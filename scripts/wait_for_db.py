"""Script to check database availability.

This script attempts to connect to the database and waits until it's available.
It uses exponential backoff for retries and has a maximum timeout.
"""

import asyncio
import logging
import os
import sys
import time
from typing import Optional
from core.db.utils import test_database_connection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is not set")
    sys.exit(1)

async def wait_for_database(max_retries: int = 60, retry_interval: int = 1) -> bool:
    """
    Wait for database to be ready with retries.
    
    Args:
        max_retries: Maximum number of retries
        retry_interval: Seconds between retries
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    retries = 0
    
    while retries < max_retries:
        is_connected = await test_database_connection()
        if is_connected:
            print("Successfully connected to database")
            return True
            
        retries += 1
        if retries < max_retries:
            print(f"Database connection attempt {retries} failed. Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)
    
    print("Failed to connect to database after maximum retries")
    return False

def main() -> None:
    """
    Main function that attempts to connect to the database.
    
    The function will retry with exponential backoff if the connection fails.
    """
    try:
        success = asyncio.run(wait_for_database())
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Failed to connect to database after multiple attempts: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 