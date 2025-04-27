import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from alembic.config import Config
from alembic import command
from core.db.session import SessionLocal
from core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_db(db: AsyncSession) -> None:
    try:
        # Run migrations
        logger.info("Running database migrations...")
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")

        # Create initial data if needed
        logger.info("Creating initial data...")
        # Add any initial data creation here
        # Example: await create_first_superuser(db)
        
        logger.info("Initial data creation completed")

    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        raise

async def create_first_superuser(db: AsyncSession) -> None:
    """Create the first superuser if it doesn't exist."""
    from core.models.user import User
    from core.security import get_password_hash
    
    try:
        # Check if superuser exists
        result = await db.execute(
            User.__table__.select().where(User.email == settings.FIRST_SUPERUSER)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                email=settings.FIRST_SUPERUSER,
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                is_superuser=True,
                is_active=True,
            )
            db.add(user)
            await db.commit()
            logger.info(f"Created first superuser: {settings.FIRST_SUPERUSER}")
        else:
            logger.info("First superuser already exists")

    except Exception as e:
        logger.error(f"Error creating first superuser: {e}")
        await db.rollback()
        raise

async def main() -> None:
    """Main function to initialize the database."""
    try:
        logger.info("Starting database initialization...")
        async with SessionLocal() as db:
            await init_db(db)
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 