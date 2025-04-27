from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import QueuePool
from core.tools.secrets_manager import secrets
import logging
from typing import AsyncGenerator, Generator
import os

logger = logging.getLogger(__name__)

# Get database URL from environment or secrets
async def get_database_url() -> str:
    """Get database URL from environment or secrets manager."""
    try:
        # Try to get from environment first
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            return db_url
            
        # If not in environment, get from secrets manager
        db_password = await secrets.get_secret("db_password")
        db_user = await secrets.get_secret("db_user")
        db_host = await secrets.get_secret("db_host")
        db_name = await secrets.get_secret("db_name")
        
        return f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}/{db_name}"
    except Exception as e:
        logger.error(f"Failed to get database URL: {str(e)}")
        raise

# Create async engine with connection pooling
async def create_async_db_engine():
    """Create async database engine with connection pooling."""
    try:
        db_url = await get_database_url()
        return create_async_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=20,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            echo=False
        )
    except Exception as e:
        logger.error(f"Failed to create database engine: {str(e)}")
        raise

# Create sync engine for migrations
def create_sync_db_engine():
    """Create synchronous database engine for migrations."""
    try:
        # Use sync URL for migrations
        db_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/wrenchai")
        return create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            echo=False
        )
    except Exception as e:
        logger.error(f"Failed to create sync database engine: {str(e)}")
        raise

# Create async session factory
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    engine = await create_async_db_engine()
    async_session_factory = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()

# Create sync session factory for migrations
def get_sync_session() -> Generator[Session, None, None]:
    """Get synchronous database session for migrations."""
    engine = create_sync_db_engine()
    sync_session_factory = sessionmaker(
        engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    with sync_session_factory() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()

# Database dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting database session."""
    async for session in get_async_session():
        yield session 