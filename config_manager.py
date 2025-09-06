import yaml
import os
from typing import Dict, Any


class ConfigManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = {}

    def load_config(self) -> Dict[str, Any]:
        """Load and parse YAML configuration file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r') as file:
                self.config = yaml.safe_load(file)
            return self.config
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")

    def validate_auth_config(self) -> bool:
        """Validate required authentication fields are present."""
        if 'auth' not in self.config:
            raise ValueError("Missing 'auth' section in configuration")
        
        REQUIRED_FIELDS = ['username', 'email', 'password']
        
        for field in REQUIRED_FIELDS:
            if field not in self.config['auth'] or not self.config['auth'][field]:
                raise ValueError(f"Missing or empty '{field}' in auth configuration")
        
        return True

    def get_rate_limit_settings(self) -> Dict[str, Any]:
        """Get rate limiting configuration with defaults."""
        defaults = {
            'base_delay_seconds': 2.0,
            'max_retries': 5,
            'backoff_multiplier': 2.0
        }
        
        if 'rate_limiting' in self.config:
            return {**defaults, **self.config['rate_limiting']}
        return defaults

    def get_output_settings(self) -> Dict[str, Any]:
        """Get output configuration with defaults."""
        defaults = {
            'include_engagement_metrics': True,
            'include_media_info': True,
            'date_format': 'ISO',
            'batch_size': 50
        }
        
        if 'output' in self.config:
            return {**defaults, **self.config['output']}
        return defaults

    def get_processing_settings(self) -> Dict[str, Any]:
        """Get processing configuration with defaults."""
        defaults = {
            'checkpoint_interval': 100,
            'max_memory_mb': 500
        }
        
        if 'processing' in self.config:
            return {**defaults, **self.config['processing']}
        return defaults