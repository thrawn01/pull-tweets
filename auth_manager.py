import os
import logging
from typing import Dict, Optional
from twikit import Client


class AuthManager:
    def __init__(self, config: Dict[str, str]):
        self.username = config['username']
        self.email = config['email'] 
        self.password = config['password']
        self.cookies_file = '.twikit_cookies'
        
    async def authenticate(self) -> Client:
        """Initialize twikit Client and login."""
        client = Client('en-US')
        
        # Try to load existing session first
        existing_client = await self.load_existing_session(client)
        if existing_client and await self.is_authenticated(existing_client):
            logging.info("Using existing authenticated session")
            return existing_client
            
        # Perform fresh login
        try:
            await client.login(
                auth_info_1=self.username,
                auth_info_2=self.email,
                password=self.password
            )
            await self.save_session(client)
            logging.info("Successfully authenticated with X.com")
            return client
            
        except Exception as e:
            logging.error(f"Authentication failed: {e}")
            raise ValueError(f"Failed to authenticate with X.com: {e}")
    
    async def save_session(self, client: Client) -> None:
        """Save session cookies to file."""
        try:
            client.save_cookies(self.cookies_file)
            logging.debug("Session cookies saved")
        except Exception as e:
            logging.warning(f"Failed to save session cookies: {e}")
    
    async def load_existing_session(self, client: Client) -> Optional[Client]:
        """Load existing session from cookies if available."""
        if not os.path.exists(self.cookies_file):
            return None
            
        try:
            client.load_cookies(self.cookies_file)
            return client
        except Exception as e:
            logging.debug(f"Failed to load existing session: {e}")
            return None
    
    async def is_authenticated(self, client: Client) -> bool:
        """Check if client session is still valid."""
        try:
            # Try to get user info as authentication test
            await client.get_user_by_screen_name(self.username)
            return True
        except Exception as e:
            logging.debug(f"Session validation failed: {e}")
            return False