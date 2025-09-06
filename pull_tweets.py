#!/usr/bin/env python3

import asyncio
import argparse
import logging
import sys
import os
from datetime import timedelta

from config_manager import ConfigManager
from auth_manager import AuthManager
from rate_limiter import RateLimiter
from tweet_extractor import TweetExtractor
from data_processor import StreamingDataProcessor, CheckpointManager
from date_parser import DateParser


class TweetPuller:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config_manager = None
        self.client = None
        
    async def run(self, username: str, duration: str, output_file: str, resume: bool = False) -> None:
        """Main execution workflow."""
        try:
            # Initialize components
            self.setup_logging()
            await self.initialize_client()
            
            # Validate inputs
            self.validate_inputs(username, duration, output_file)
            
            # Parse duration and set up checkpoint management (always enabled)
            parsed_duration = DateParser.parse_duration(duration)
            
            checkpoint = CheckpointManager(output_file)
            existing_checkpoint = await checkpoint.load_checkpoint()
            if existing_checkpoint and resume:
                logging.info(f"Resuming from previous extraction: {existing_checkpoint.get('count', 0)} tweets")
            elif existing_checkpoint and not resume:
                logging.info(f"Found previous checkpoint ({existing_checkpoint.get('count', 0)} tweets). Use --resume to continue or delete {output_file}.checkpoint to start fresh.")
            
            # Initialize components
            rate_limiter = RateLimiter(**self.config_manager.get_rate_limit_settings())
            
            output_settings = self.config_manager.get_output_settings()
            processing_settings = self.config_manager.get_processing_settings()
            
            batch_size = output_settings.get('batch_size', 50)
            checkpoint_interval = processing_settings.get('checkpoint_interval', 100)
            max_memory_mb = processing_settings.get('max_memory_mb', 500)
            
            # Create extractor and processor
            extractor = TweetExtractor(self.client, rate_limiter)
            processor = StreamingDataProcessor(output_file, batch_size, checkpoint_interval, max_memory_mb)
            
            logging.info(f"Starting tweet extraction for @{username.lstrip('@')}")
            logging.info(f"Duration: {duration} | Output: {output_file}")
            
            # Extract and process tweets
            tweet_stream = extractor.extract_user_tweets(username, parsed_duration)
            await processor.process_tweet_stream(tweet_stream)
            
            # Cleanup checkpoint on success
            await checkpoint.cleanup_checkpoint()
            
            logging.info(f"Extraction completed successfully: {processor.total_count} tweets saved to {output_file}")
            
        except Exception as e:
            logging.error(f"Tweet extraction failed: {e}")
            sys.exit(1)
    
    async def initialize_client(self) -> None:
        """Initialize configuration and authentication."""
        # Load configuration
        self.config_manager = ConfigManager(self.config_path)
        config = self.config_manager.load_config()
        self.config_manager.validate_auth_config()
        
        # Initialize authentication
        auth_manager = AuthManager(config['auth'])
        self.client = await auth_manager.authenticate()
        
        logging.info("Initialization completed successfully")
    
    def setup_logging(self, verbose: bool = False) -> None:
        """Setup logging configuration."""
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def validate_inputs(self, username: str, duration: str, output_file: str) -> bool:
        """Validate command line inputs."""
        if not username:
            raise ValueError("Username is required")
        
        if not output_file:
            raise ValueError("Output file is required")
            
        if not output_file.endswith('.parquet'):
            raise ValueError("Output file must have .parquet extension")
        
        # Test duration parsing
        try:
            DateParser.parse_duration(duration)
        except ValueError as e:
            raise ValueError(f"Invalid duration format: {e}")
        
        return True


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Extract tweets from X.com using twikit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pull_tweets.py @elonmusk -o elon_tweets.parquet
  python pull_tweets.py elonmusk --duration "7 days" --output-file tweets_7d.parquet
  python pull_tweets.py @username -d "1 month" -o tweets.parquet --resume --verbose
        """
    )
    
    # Required arguments
    parser.add_argument(
        'username',
        help='Twitter username (with or without @)'
    )
    
    parser.add_argument(
        '--output-file', '-o',
        required=True,
        help='Output parquet filename (e.g., tweets.parquet)'
    )
    
    # Optional arguments
    parser.add_argument(
        '--duration', '-d',
        default='30 days',
        help='Time period to go back (e.g., "7 days", "1 month", default: "30 days")'
    )
    
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to config.yaml file (default: ./config.yaml)'
    )
    
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from existing output file if present'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Number of tweets to process per batch (default: 50)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()


async def main() -> None:
    """Main entry point."""
    args = parse_arguments()
    
    # Check if config file exists
    if not os.path.exists(args.config):
        print(f"Error: Configuration file not found: {args.config}")
        print("Please create a config.yaml file based on config.yaml.template")
        sys.exit(1)
    
    # Initialize and run tweet puller
    puller = TweetPuller(args.config)
    
    # Setup logging based on verbose flag
    puller.setup_logging(args.verbose)
    
    await puller.run(
        username=args.username,
        duration=args.duration,
        output_file=args.output_file,
        resume=args.resume
    )


if __name__ == "__main__":
    asyncio.run(main())