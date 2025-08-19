"""
Application configuration settings
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = Field(default="sqlite:///./data/db/talkai.db")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    
    # API Keys
    moonshot_api_key: Optional[str] = Field(default=None)
    openai_api_key: Optional[str] = Field(default=None)
    
    # WeChat Mini Program
    wechat_app_id: Optional[str] = Field(default=None)
    wechat_app_secret: Optional[str] = Field(default=None)
    
    # JWT Settings
    secret_key: str = Field(default="your-secret-key-change-in-production-min-32-chars")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=1440)  # 24 hours
    
    # Model Settings
    model_provider: str = Field(default="moonshot")
    moonshot_model: str = Field(default="moonshot-v1-8k")
    openai_model: str = Field(default="gpt-3.5-turbo")
    
    # App Settings
    api_version: str = Field(default="v1")
    debug: bool = Field(default=False)
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    
    # CORS
    allowed_origins: List[str] = Field(default=[
        "http://localhost:3000",
        "https://servicewechat.com"
    ])
    
    # File Upload
    max_file_size: int = Field(default=10 * 1024 * 1024)  # 10MB
    upload_dir: str = Field(default="./data/uploads")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100)
    rate_limit_window: int = Field(default=60)
    
    # Logging
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="./logs/app.log")
    
    # Dictionary Settings
    dictionary_db_path: str = Field(default="./data/db/dictionary400k.db")
    
    # Learning Settings
    vocab_auto_sync_hours: int = Field(default=24)
    max_chat_records_per_analysis: int = Field(default=100)
    max_memory_turns: int = Field(default=3)
    top_n_vocab: int = Field(default=5)
    
    # TTS Settings
    tts_enabled: bool = Field(default=False)
    
    # API Error Handling
    api_retry_attempts: int = Field(default=3)
    api_min_retry_delay: int = Field(default=2)
    api_max_retry_delay: int = Field(default=10)
    api_retry_multiplier: float = Field(default=1.5)
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


# Paths
def get_db_path() -> str:
    """Get database file path"""
    os.makedirs(os.path.dirname(settings.database_url.replace("sqlite:///", "")), exist_ok=True)
    return settings.database_url


def get_upload_path() -> str:
    """Get upload directory path"""
    os.makedirs(settings.upload_dir, exist_ok=True)
    return settings.upload_dir


def get_log_path() -> str:
    """Get log file path"""
    os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)
    return settings.log_file