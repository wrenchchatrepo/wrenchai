from typing import List, Optional

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings.
    
    Attributes:
        APP_NAME: Name of the application
        DEBUG: Debug mode flag
        VERSION: API version
        API_V1_STR: API v1 prefix
        PROJECT_NAME: Project name
        BACKEND_CORS_ORIGINS: List of allowed CORS origins
        DATABASE_URL: Database connection string
        SECRET_KEY: Secret key for JWT
        ALGORITHM: JWT algorithm
        ACCESS_TOKEN_EXPIRE_MINUTES: JWT token expiration time
        REDIS_URL: Redis connection string for caching
        FIRST_SUPERUSER: First superuser email
        FIRST_SUPERUSER_PASSWORD: First superuser password
    """
    APP_NAME: str = "WrenchAI"
    DEBUG: bool = False
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "WrenchAI"
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # Database
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Redis
    REDIS_URL: Optional[str] = None
    
    # First superuser
    FIRST_SUPERUSER: str
    FIRST_SUPERUSER_PASSWORD: str
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 