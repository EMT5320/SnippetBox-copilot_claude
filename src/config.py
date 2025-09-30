"""Configuration management using environment variables."""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./snippetbox.db"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # CORS
    CORS_ENABLED: bool = True
    CORS_ORIGINS: str = "*"
    
    # Application
    APP_NAME: str = "SnippetBox"
    APP_VERSION: str = "1.0.0"
    
    # Validation
    MAX_TITLE_LENGTH: int = 200
    MAX_CONTENT_LENGTH: int = 100000
    MAX_TAG_LENGTH: int = 50
    MAX_TAGS_COUNT: int = 20
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from string."""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
