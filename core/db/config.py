"""Database configuration settings using pydantic-settings."""

from typing import Dict, Any
from pydantic_settings import BaseSettings
from sqlalchemy.pool import AsyncAdaptedQueuePool

class DatabaseSettings(BaseSettings):
    """Database configuration settings.
    
    Attributes:
        DB_DRIVER: Database driver (default: postgresql+asyncpg)
        DB_HOST: Database host
        DB_PORT: Database port
        DB_USER: Database user
        DB_PASSWORD: Database password
        DB_NAME: Database name
        POOL_SIZE: Connection pool size
        MAX_OVERFLOW: Maximum number of connections to overflow
        POOL_TIMEOUT: Timeout for getting a connection from the pool
        POOL_RECYCLE: Connection recycle time
        POOL_PRE_PING: Whether to ping connections before using them
    """
    
    # Database connection settings
    DB_DRIVER: str = "postgresql+asyncpg"
    DB_HOST: str
    DB_PORT: int = 5432
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    
    # Connection pool settings
    POOL_SIZE: int = 5
    MAX_OVERFLOW: int = 10
    POOL_TIMEOUT: int = 30
    POOL_RECYCLE: int = 1800
    POOL_PRE_PING: bool = True
    
    @property
    def DATABASE_URL(self) -> str:
        """Generate the database URL from settings.
        
        Returns:
            str: The complete database URL
        """
        return (
            f"{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
    
    @property
    def POOL_SETTINGS(self) -> Dict[str, Any]:
        """Get SQLAlchemy connection pool settings.
        
        Returns:
            Dict[str, Any]: Pool configuration dictionary
        """
        return {
            "poolclass": AsyncAdaptedQueuePool,
            "pool_size": self.POOL_SIZE,
            "max_overflow": self.MAX_OVERFLOW,
            "pool_timeout": self.POOL_TIMEOUT,
            "pool_recycle": self.POOL_RECYCLE,
            "pool_pre_ping": self.POOL_PRE_PING
        }
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
db_settings = DatabaseSettings() 