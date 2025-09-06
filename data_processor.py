import json
import logging
import aiofiles
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import psutil
import os
from typing import List, Dict, Any, AsyncGenerator, Optional
from datetime import datetime


class StreamingDataProcessor:
    def __init__(self, output_file: str, batch_size: int = 50, checkpoint_interval: int = 100, max_memory_mb: int = 500):
        self.output_file = output_file
        self.batch_size = batch_size
        self.checkpoint_interval = checkpoint_interval
        self.max_memory_mb = max_memory_mb
        self.parquet_writer = None
        self.first_write = True
        self.schema = self.define_parquet_schema()
        self.total_count = 0
        self.checkpoint_manager = CheckpointManager(output_file)
        self.last_tweet_id = None
        self.process = psutil.Process(os.getpid())
        
    def define_parquet_schema(self) -> pa.Schema:
        """Define consistent schema for parquet output with proper data types."""
        return pa.schema([
            # Core tweet data
            pa.field('id', pa.string()),
            pa.field('text', pa.string()),
            pa.field('full_text', pa.string()),
            pa.field('created_at', pa.timestamp('ns')),
            pa.field('lang', pa.string()),
            
            # User information  
            pa.field('user_id', pa.string()),
            pa.field('user_screen_name', pa.string()),
            pa.field('user_name', pa.string()),
            
            # Engagement metrics
            pa.field('favorite_count', pa.int64()),
            pa.field('favorited', pa.bool_()),
            pa.field('retweet_count', pa.int64()),
            pa.field('reply_count', pa.int64()),
            pa.field('quote_count', pa.int64()),
            pa.field('view_count', pa.int64()),
            pa.field('bookmark_count', pa.int64()),
            pa.field('bookmarked', pa.bool_()),
            
            # Content metadata
            pa.field('hashtags', pa.list_(pa.string())),
            pa.field('urls', pa.list_(pa.string())),
            pa.field('media', pa.string()),  # JSON string representation
            pa.field('has_card', pa.bool_()),
            pa.field('is_quote_status', pa.bool_()),
            pa.field('possibly_sensitive', pa.bool_()),
            pa.field('is_translatable', pa.bool_()),
            
            # Thread/reply information
            pa.field('in_reply_to', pa.string()),
            pa.field('conversation_id', pa.string()),
            
            # Location data
            pa.field('place', pa.string()),  # JSON string representation
            
            # Content source
            pa.field('source', pa.string()),
        ])
    
    def get_memory_usage_mb(self) -> float:
        """Get current memory usage of the process in MB."""
        try:
            memory_info = self.process.memory_info()
            return memory_info.rss / (1024 * 1024)  # Convert bytes to MB
        except Exception as e:
            logging.warning(f"Failed to get memory usage: {e}")
            return 0.0
    
    def check_memory_limit(self) -> bool:
        """Check if memory usage is within limits."""
        current_memory = self.get_memory_usage_mb()
        if current_memory > self.max_memory_mb:
            logging.warning(f"Memory usage ({current_memory:.1f}MB) exceeds limit ({self.max_memory_mb}MB)")
            return False
        return True
    
    async def handle_memory_pressure(self, batch: List[Dict[str, Any]]) -> None:
        """Handle memory pressure by forcing batch write and cleanup."""
        logging.info(f"Memory pressure detected, forcing batch write (current: {self.get_memory_usage_mb():.1f}MB)")
        
        if batch:
            try:
                await self.write_batch_to_parquet(batch)
                batch.clear()
                logging.info(f"Memory after batch write: {self.get_memory_usage_mb():.1f}MB")
            except Exception as e:
                logging.error(f"Failed to write batch during memory pressure: {e}")
                # Still clear batch to free memory
                batch.clear()
                raise
    
    async def process_tweet_stream(self, tweet_stream: AsyncGenerator[Dict[str, Any], None]) -> None:
        """Process tweet stream in configurable batches to minimize memory usage."""
        batch = []
        consecutive_failures = 0
        MAX_CONSECUTIVE_FAILURES = 3
        
        try:
            async for tweet_dict in tweet_stream:
                batch.append(tweet_dict)
                self.total_count += 1
                self.last_tweet_id = tweet_dict.get('id')
                
                # Check memory usage and force batch write if needed
                should_write_batch = (
                    len(batch) >= self.batch_size or  # Normal batch size reached
                    not self.check_memory_limit()     # Memory limit exceeded
                )
                
                if should_write_batch:
                    try:
                        if not self.check_memory_limit():
                            await self.handle_memory_pressure(batch)
                        else:
                            await self.write_batch_to_parquet(batch)
                            
                        current_memory = self.get_memory_usage_mb()
                        logging.info(f"Processed {self.total_count} tweets (Memory: {current_memory:.1f}MB)")
                        consecutive_failures = 0  # Reset failure counter
                        
                        # Save checkpoint periodically
                        if self.total_count % self.checkpoint_interval == 0:
                            await self.checkpoint_manager.save_checkpoint(self.last_tweet_id, self.total_count)
                            
                    except Exception as e:
                        consecutive_failures += 1
                        logging.error(f"Failed to write batch ({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}): {e}")
                        
                        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                            logging.error("Too many consecutive write failures, stopping to prevent memory exhaustion")
                            raise RuntimeError("Repeated parquet write failures detected")
                    finally:
                        batch.clear()  # Always clear batch to prevent memory growth
                    
            # Write final batch
            if batch:
                await self.write_batch_to_parquet(batch)
                logging.info(f"Final batch processed. Total tweets: {self.total_count}")
                
        finally:
            # Ensure writer is always closed even on exceptions
            self.finalize_parquet_writer()
    
    async def write_batch_to_parquet(self, tweets: List[Dict[str, Any]]) -> None:
        """Write batch to parquet using PyArrow for proper incremental writing."""
        if not tweets:
            return
            
        # Validate and clean data
        cleaned_tweets = []
        for tweet in tweets:
            if self.validate_tweet_data(tweet):
                cleaned_tweets.append(self.normalize_tweet_data(tweet))
        
        if not cleaned_tweets:
            logging.warning("No valid tweets in batch")
            return
            
        try:
            # Convert to pandas DataFrame then to PyArrow table with schema enforcement
            dataframe = pd.DataFrame(cleaned_tweets)
            
            # Validate dataframe columns match expected schema
            expected_columns = set(field.name for field in self.schema)
            actual_columns = set(dataframe.columns)
            
            if not actual_columns.issubset(expected_columns):
                missing_columns = actual_columns - expected_columns
                logging.warning(f"Unexpected columns found: {missing_columns}")
                # Drop unexpected columns to prevent schema mismatch
                dataframe = dataframe[list(expected_columns.intersection(actual_columns))]
            
            # Add missing columns with default values
            for field in self.schema:
                if field.name not in dataframe.columns:
                    default_value = self._get_default_value_for_type(field.type)
                    dataframe[field.name] = default_value
            
            # Reorder columns to match schema
            dataframe = dataframe.reindex(columns=[field.name for field in self.schema])
            
            table = pa.Table.from_pandas(dataframe, schema=self.schema, preserve_index=False)
            
            if self.first_write:
                self.parquet_writer = pq.ParquetWriter(self.output_file, self.schema)
                self.first_write = False
            
            self.parquet_writer.write_table(table)
            
        except Exception as e:
            logging.error(f"Error writing batch to parquet: {e}")
            # Don't re-raise to allow processing to continue with next batch
            # The caller handles consecutive failures
            raise RuntimeError(f"Parquet write failed: {e}")
    
    def _get_default_value_for_type(self, pa_type) -> Any:
        """Get default value for PyArrow type."""
        if pa.types.is_string(pa_type):
            return None
        elif pa.types.is_integer(pa_type):
            return 0
        elif pa.types.is_boolean(pa_type):
            return False
        elif pa.types.is_timestamp(pa_type):
            return None
        elif pa.types.is_list(pa_type):
            return []
        else:
            return None
    
    def validate_tweet_data(self, tweet: Dict[str, Any]) -> bool:
        """Validate data completeness and structure."""
        # Check for required fields
        if not tweet.get('id'):
            logging.warning("Tweet missing ID, skipping")
            return False
        
        if not tweet.get('text') and not tweet.get('full_text'):
            logging.warning(f"Tweet {tweet.get('id')} missing text content")
            return False
        
        return True
    
    def normalize_tweet_data(self, tweet: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize data types for parquet schema compatibility."""
        normalized = tweet.copy()
        
        # Convert and validate integer fields
        int_fields = ['favorite_count', 'retweet_count', 'reply_count', 'quote_count', 'view_count', 'bookmark_count']
        for field in int_fields:
            value = normalized.get(field)
            if value is None:
                normalized[field] = 0
            else:
                try:
                    # Convert string numbers to int
                    normalized[field] = int(str(value)) if value else 0
                except (ValueError, TypeError):
                    logging.warning(f"Could not convert {field} value '{value}' to int, using 0")
                    normalized[field] = 0
        
        bool_fields = ['favorited', 'bookmarked', 'has_card', 'is_quote_status', 'possibly_sensitive', 'is_translatable']
        for field in bool_fields:
            if normalized.get(field) is None:
                normalized[field] = False
        
        list_fields = ['hashtags', 'urls']
        for field in list_fields:
            if not normalized.get(field):
                normalized[field] = []
        
        # Ensure datetime is properly formatted
        if normalized.get('created_at') and isinstance(normalized['created_at'], datetime):
            # PyArrow will handle datetime conversion
            pass
        elif normalized.get('created_at'):
            # Convert to ISO string if not datetime
            normalized['created_at'] = str(normalized['created_at'])
        
        return normalized
    
    def finalize_parquet_writer(self) -> None:
        """Finalize parquet writer and close file."""
        if self.parquet_writer:
            try:
                self.parquet_writer.close()
                logging.info(f"Parquet file written successfully: {self.output_file}")
            except Exception as e:
                logging.error(f"Error closing parquet writer: {e}")
                # Still mark as closed to prevent double-close attempts
            finally:
                self.parquet_writer = None


class CheckpointManager:
    def __init__(self, output_file: str):
        self.output_file = output_file
        self.checkpoint_file = f"{output_file}.checkpoint"
        
    async def save_checkpoint(self, last_tweet_id: str, count: int) -> None:
        """Save extraction progress to checkpoint file."""
        checkpoint = {
            "last_tweet_id": last_tweet_id,
            "count": count,
            "timestamp": datetime.now().isoformat(),
            "output_file": self.output_file
        }
        
        try:
            async with aiofiles.open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(checkpoint, indent=2))
            logging.debug(f"Checkpoint saved: {count} tweets processed")
        except (IOError, OSError) as e:
            logging.warning(f"Failed to save checkpoint: {e}")
        except Exception as e:
            logging.error(f"Unexpected error saving checkpoint: {e}")
    
    async def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load checkpoint data if available."""
        try:
            async with aiofiles.open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                if not content.strip():  # Handle empty files
                    return None
                checkpoint = json.loads(content)
            logging.info(f"Loaded checkpoint: {checkpoint.get('count', 0)} tweets previously processed")
            return checkpoint
        except FileNotFoundError:
            logging.debug("No checkpoint file found")
            return None
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logging.warning(f"Corrupted checkpoint file, ignoring: {e}")
            return None
        except (IOError, OSError) as e:
            logging.error(f"Error reading checkpoint file: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error loading checkpoint: {e}")
            return None
    
    async def get_resume_point(self) -> Optional[str]:
        """Get the last tweet ID for resume capability."""
        checkpoint = await self.load_checkpoint()
        if checkpoint:
            return checkpoint.get('last_tweet_id')
        return None
    
    async def cleanup_checkpoint(self) -> None:
        """Clean up checkpoint file on successful completion."""
        try:
            import os
            if os.path.exists(self.checkpoint_file):
                os.remove(self.checkpoint_file)
                logging.info("Checkpoint file cleaned up")
        except Exception as e:
            logging.warning(f"Failed to cleanup checkpoint: {e}")