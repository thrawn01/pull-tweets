import asyncio
import time
import logging
from typing import Dict, Any


class RateLimiter:
    def __init__(self, base_delay: float, max_retries: int, backoff_multiplier: float):
        self.base_delay = base_delay
        self.max_retries = max_retries
        self.backoff_multiplier = backoff_multiplier
        self.last_request_time = 0
        
    async def wait_before_request(self) -> None:
        """Implement configurable delays between API requests."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.base_delay:
            wait_time = self.base_delay - elapsed
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    async def handle_rate_limit_error(self, attempt: int) -> bool:
        """Handle rate limit exceptions with exponential backoff."""
        if attempt >= self.max_retries:
            return False
            
        backoff_delay = self.calculate_backoff_delay(attempt)
        logging.warning(f"Rate limit hit, waiting {backoff_delay}s (attempt {attempt}/{self.max_retries})")
        await asyncio.sleep(backoff_delay)
        return True
    
    def calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        return self.base_delay * (self.backoff_multiplier ** attempt)
    
    async def handle_twikit_rate_limits(self, error: Exception) -> bool:
        """Handle twikit-specific rate limit exceptions."""
        from twikit.errors import TooManyRequests, Unauthorized, Forbidden
        
        # Constants for rate limiting
        RATE_LIMIT_BUFFER_SECONDS = 60
        MIN_WAIT_SECONDS = 300
        DEFAULT_RATE_LIMIT_WAIT_SECONDS = 900
        MAX_WAIT_SECONDS = 3600  # Cap at 1 hour
        
        if isinstance(error, TooManyRequests):
            # Handle specific rate limit reset times if available
            if hasattr(error, 'rate_limit_reset') and error.rate_limit_reset:
                try:
                    reset_time = int(error.rate_limit_reset)
                    current_time = int(time.time())
                    
                    # Validate reset time is reasonable
                    if reset_time > current_time and reset_time - current_time < MAX_WAIT_SECONDS:
                        sleep_time = reset_time - current_time + RATE_LIMIT_BUFFER_SECONDS
                        wait_time = max(sleep_time, MIN_WAIT_SECONDS)
                        wait_time = min(wait_time, MAX_WAIT_SECONDS)  # Cap maximum wait
                    else:
                        wait_time = DEFAULT_RATE_LIMIT_WAIT_SECONDS
                except (ValueError, OverflowError, TypeError):
                    # Handle invalid reset time values
                    wait_time = DEFAULT_RATE_LIMIT_WAIT_SECONDS
            else:
                wait_time = DEFAULT_RATE_LIMIT_WAIT_SECONDS
                
            logging.warning(f"Rate limit exceeded, waiting {wait_time}s")
            await asyncio.sleep(wait_time)
            return True
            
        elif isinstance(error, (Unauthorized, Forbidden)):
            logging.warning(f"Account access denied: {error}")
            return False
        else:
            raise error