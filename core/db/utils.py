from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import Settings

async def test_database_connection() -> bool:
    """Test the database connection using MCP Supabase integration."""
    try:
        # Using raw SQL query to test connection
        from mcp.supabase import execute_sql_query
        result = await execute_sql_query("SELECT 1")
        return bool(result)
    except Exception as e:
        print(f"Database connection test failed: {str(e)}")
        return False

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session using MCP Supabase integration."""
    try:
        from mcp.supabase import get_session
        async with get_session() as session:
            yield session
    except Exception as e:
        print(f"Failed to get database session: {str(e)}")
        raise 