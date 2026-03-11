"""
Configuration management module.
Loads and validates all environment variables.
"""

import os
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Central configuration class"""
    
    # Telegram
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: List[int] = [int(id_) for id_ in os.getenv("ADMIN_IDS", "").split(",") if id_]
    CHANNEL_ID: str = os.getenv("CHANNEL_ID", "")
    CHANNEL_LINK: str = os.getenv("CHANNEL_LINK", "")
    
    # MongoDB
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "movie_bot")
    
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD") or None
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
    
    # Subscription
    FREE_DAILY_LIMIT: int = int(os.getenv("FREE_DAILY_LIMIT", 5))
    PREMIUM_DAILY_LIMIT: int = int(os.getenv("PREMIUM_DAILY_LIMIT", 999999))
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", 1))
    RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", 5))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/bot.log")
    
    # Payment (Optional)
    PAYMENT_PROVIDER_TOKEN: Optional[str] = os.getenv("PAYMENT_PROVIDER_TOKEN") or None
    
    # Application
    APP_NAME: str = "MovieBot"
    VERSION: str = "1.0.0"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        required_vars = [
            ("BOT_TOKEN", cls.BOT_TOKEN),
            ("CHANNEL_ID", cls.CHANNEL_ID),
            ("MONGODB_URI", cls.MONGODB_URI),
        ]
        
        missing = [var_name for var_name, value in required_vars if not value]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        if not cls.ADMIN_IDS:
            print("Warning: No ADMIN_IDS configured")
        
        return True


# Create config instance
config = Config()
config.validate()
