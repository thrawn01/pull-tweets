import logging
from typing import AsyncGenerator, Dict, Any, Optional
from datetime import datetime, timedelta
from twikit import Client, User, Tweet
from rate_limiter import RateLimiter
from date_parser import DateParser


class TweetExtractor:
    def __init__(self, client: Client, rate_limiter: RateLimiter):
        self.client = client
        self.rate_limiter = rate_limiter
        
    async def extract_user_tweets(self, username: str, duration: timedelta) -> AsyncGenerator[Dict[str, Any], None]:
        """Extract tweets for a user within the specified duration."""
        # Remove @ if present
        username = username.lstrip('@')
        
        # Get user object
        user = await self.get_user_by_username(username)
        cutoff_date = DateParser.calculate_cutoff_date(duration)
        
        logging.info(f"Extracting tweets for @{username} from {cutoff_date.isoformat()}")
        
        # Extract tweets with pagination
        async for tweet in self.extract_with_pagination(user, cutoff_date):
            tweet_dict = self.convert_tweet_to_dict(tweet)
            yield tweet_dict
    
    async def get_user_by_username(self, username: str, max_attempts: int = 3) -> User:
        """Convert username to User object via twikit API."""
        for attempt in range(max_attempts):
            try:
                await self.rate_limiter.wait_before_request()
                user = await self.client.get_user_by_screen_name(username)
                logging.info(f"Found user: @{username} (ID: {user.id})")
                return user
            except Exception as e:
                if attempt == max_attempts - 1:  # Last attempt
                    raise ValueError(f"User @{username} not found or inaccessible after {max_attempts} attempts: {e}")
                
                if not await self.rate_limiter.handle_twikit_rate_limits(e):
                    raise ValueError(f"User @{username} not found or inaccessible: {e}")
        
        raise ValueError(f"User @{username} lookup failed after {max_attempts} attempts")
    
    async def extract_with_pagination(self, user: User, cutoff_date: datetime, max_retries: int = 3) -> AsyncGenerator[Tweet, None]:
        """Extract tweets with proper pagination and date filtering."""
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                await self.rate_limiter.wait_before_request()
                tweets = await self.client.get_user_tweets(user.id, 'Tweets', count=40)
                
                for tweet in tweets:
                    tweet_date = self.get_tweet_date(tweet)
                    if tweet_date and tweet_date < cutoff_date:
                        logging.info(f"Reached cutoff date: {tweet_date.isoformat()}")
                        return
                    yield tweet
                
                # Continue pagination
                while hasattr(tweets, 'next_cursor') and tweets.next_cursor:
                    page_retry_count = 0
                    
                    while page_retry_count < max_retries:
                        try:
                            await self.rate_limiter.wait_before_request()
                            tweets = await tweets.next()
                            
                            for tweet in tweets:
                                tweet_date = self.get_tweet_date(tweet)
                                if tweet_date and tweet_date < cutoff_date:
                                    logging.info(f"Reached cutoff date: {tweet_date.isoformat()}")
                                    return
                                yield tweet
                            break  # Success, exit page retry loop
                            
                        except Exception as e:
                            if not await self.rate_limiter.handle_twikit_rate_limits(e):
                                logging.error(f"Error in pagination: {e}")
                                return
                            page_retry_count += 1
                            if page_retry_count >= max_retries:
                                logging.error(f"Pagination failed after {max_retries} retries")
                                return
                
                return  # Success, exit main retry loop
                
            except Exception as e:
                if not await self.rate_limiter.handle_twikit_rate_limits(e):
                    raise RuntimeError(f"Failed to extract tweets: {e}")
                retry_count += 1
                if retry_count >= max_retries:
                    raise RuntimeError(f"Tweet extraction failed after {max_retries} retries: {e}")
                logging.warning(f"Retrying tweet extraction (attempt {retry_count + 1}/{max_retries})")
    
    def get_tweet_date(self, tweet: Tweet) -> Optional[datetime]:
        """Extract creation date from tweet, handling various attribute names."""
        # Try different possible attribute names
        date_attrs = ['created_at_datetime', 'created_at', 'date']
        
        for attr in date_attrs:
            if hasattr(tweet, attr):
                date_value = getattr(tweet, attr)
                if date_value:
                    try:
                        return DateParser.parse_tweet_date(date_value)
                    except ValueError:
                        continue
        
        logging.warning(f"Could not extract date from tweet {getattr(tweet, 'id', 'unknown')}")
        return None
    
    def convert_tweet_to_dict(self, tweet: Tweet) -> Dict[str, Any]:
        """Convert Tweet object to dictionary format for parquet storage."""
        # Helper to safely get attribute
        def safe_get(attr, default=None):
            return getattr(tweet, attr, default)
        
        # Helper to safely get user attribute
        def safe_get_user(attr, default=None):
            user = safe_get('user')
            if user:
                return getattr(user, attr, default)
            return default
        
        # Convert hashtags and URLs to lists
        hashtags = []
        urls = []
        
        # Extract hashtags
        entities = safe_get('entities', {})
        if isinstance(entities, dict) and 'hashtags' in entities:
            hashtags = [tag.get('text', '') for tag in entities['hashtags']]
        
        # Extract URLs
        if isinstance(entities, dict) and 'urls' in entities:
            urls = [url.get('expanded_url', url.get('url', '')) for url in entities['urls']]
        
        # Get media info as JSON string
        media_info = None
        if isinstance(entities, dict) and 'media' in entities:
            media_info = str(entities['media'])
        
        return {
            # Core tweet data
            'id': safe_get('id'),
            'text': safe_get('text'),
            'full_text': safe_get('full_text', safe_get('text')),
            'created_at': self.get_tweet_date(tweet),
            'lang': safe_get('lang'),
            
            # User information
            'user_id': safe_get_user('id'),
            'user_screen_name': safe_get_user('screen_name'),
            'user_name': safe_get_user('name'),
            
            # Engagement metrics
            'favorite_count': safe_get('favorite_count', 0),
            'favorited': safe_get('favorited', False),
            'retweet_count': safe_get('retweet_count', 0),
            'reply_count': safe_get('reply_count', 0),
            'quote_count': safe_get('quote_count', 0),
            'view_count': safe_get('view_count', 0),
            'bookmark_count': safe_get('bookmark_count', 0),
            'bookmarked': safe_get('bookmarked', False),
            
            # Content metadata
            'hashtags': hashtags,
            'urls': urls,
            'media': media_info,
            'has_card': safe_get('has_card', False),
            'is_quote_status': safe_get('is_quote_status', False),
            'possibly_sensitive': safe_get('possibly_sensitive', False),
            'is_translatable': safe_get('is_translatable', False),
            
            # Thread/reply information
            'in_reply_to': safe_get('in_reply_to_status_id'),
            'conversation_id': safe_get('conversation_id'),
            
            # Location data
            'place': str(safe_get('place')) if safe_get('place') else None,
            
            # Content source
            'source': safe_get('source'),
        }