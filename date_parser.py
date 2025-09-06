from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import re


class DateParser:
    @staticmethod
    def parse_duration(duration_str: str) -> timedelta:
        """Parse natural language duration strings using dateutil."""
        duration_str = duration_str.strip().lower()
        
        # Handle common patterns
        patterns = {
            r'(\d+)\s*days?': lambda m: timedelta(days=int(m.group(1))),
            r'(\d+)\s*weeks?': lambda m: timedelta(weeks=int(m.group(1))),
            r'(\d+)\s*months?': lambda m: timedelta(days=int(m.group(1)) * 30),  # Approximate
            r'(\d+)\s*years?': lambda m: timedelta(days=int(m.group(1)) * 365),  # Approximate
            r'(\d+)\s*hours?': lambda m: timedelta(hours=int(m.group(1))),
            r'(\d+)\s*minutes?': lambda m: timedelta(minutes=int(m.group(1))),
        }
        
        for pattern, converter in patterns.items():
            match = re.search(pattern, duration_str)
            if match:
                return converter(match)
        
        # Default to 30 days if parsing fails
        raise ValueError(f"Unable to parse duration: '{duration_str}'. Use format like '7 days', '1 month', etc.")
    
    @staticmethod
    def calculate_cutoff_date(duration: timedelta) -> datetime:
        """Calculate cutoff date for tweet filtering."""
        from datetime import timezone
        return datetime.now(timezone.utc) - duration
    
    @staticmethod
    def parse_tweet_date(tweet_created_at) -> datetime:
        """Parse tweet date from twikit Tweet object."""
        # Handle both datetime objects and string formats
        if isinstance(tweet_created_at, datetime):
            return tweet_created_at
        elif isinstance(tweet_created_at, str):
            # Try parsing ISO format first
            try:
                return datetime.fromisoformat(tweet_created_at.replace('Z', '+00:00'))
            except ValueError:
                # Fallback to other common formats
                formats = [
                    '%a %b %d %H:%M:%S %z %Y',  # Twitter API format
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S.%fZ',
                ]
                for fmt in formats:
                    try:
                        return datetime.strptime(tweet_created_at, fmt)
                    except ValueError:
                        continue
        
        raise ValueError(f"Unable to parse tweet date: {tweet_created_at}")