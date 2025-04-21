# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import sys
import logging
import asyncio
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel

# Try to import SQL generator dependencies
try:
    import psycopg
    HAS_PSYCOPG = True
except ImportError:
    HAS_PSYCOPG = False
    logging.warning("psycopg is not installed. SQL generation will be limited.")

# Check for Pydantic AI
try:
    from pydantic_ai import Agent
    from pydantic_ai.dependencies import PydanticAIDeps
    HAS_PYDANTIC_AI = True
except ImportError:
    HAS_PYDANTIC_AI = False
    logging.warning("pydantic-ai is not installed. SQL generation will not work.")

# Check for rich (optional - for better output formatting)
try:
    from rich.console import Console
    from rich.syntax import Syntax
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    logging.warning("rich is not installed. Output will use standard formatting.")

# Output models
class SQLResponse(BaseModel):
    """SQL query generation response"""
    sql: str
    explanation: Optional[str] = None

class SQLError(BaseModel):
    """SQL generation error"""
    error: str
    details: Optional[str] = None

# Dependency type
class SQLDeps(PydanticAIDeps):
    """Dependencies for SQL generator"""
    conn: Optional[Any] = None  # PostgreSQL connection

class SQLGenerator:
    """SQL generator using Pydantic AI"""
    
    def __init__(self, 
                db_host: str = "localhost", 
                db_port: int = 54320,
                db_name: str = "logs",
                db_user: str = "postgres",
                db_password: str = "postgres",
                model: str = "openai:gpt-4-1106-preview"):
        """Initialize the SQL generator
        
        Args:
            db_host: PostgreSQL host
            db_port: PostgreSQL port
            db_name: Database name
            db_user: Database user
            db_password: Database password
            model: AI model to use
        """
        self.db_config = {
            "host": db_host,
            "port": db_port,
            "dbname": db_name,
            "user": db_user,
            "password": db_password
        }
        
        self.model = model
        self.conn = None
        self._check_requirements()
    
    def _check_requirements(self):
        """Check if all required dependencies are installed"""
        if not HAS_PYDANTIC_AI:
            logging.error("pydantic-ai is required for SQL generation")
            raise ImportError("pydantic-ai is required for SQL generation")
            
        if not HAS_PSYCOPG:
            logging.warning("psycopg is not installed. SQL validation will be disabled.")
    
    async def connect(self) -> bool:
        """Connect to the PostgreSQL database
        
        Returns:
            True if connection successful, False otherwise
        """
        if not HAS_PSYCOPG:
            logging.warning("psycopg is not installed. SQL validation will be disabled.")
            return False
            
        try:
            self.conn = await psycopg.AsyncConnection.connect(
                **self.db_config, 
                autocommit=True
            )
            logging.info("Connected to PostgreSQL database")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to PostgreSQL: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the PostgreSQL database"""
        if self.conn:
            await self.conn.close()
            self.conn = None
            logging.info("Disconnected from PostgreSQL database")
    
    async def get_schema_info(self) -> str:
        """Get schema information from the database
        
        Returns:
            Schema information as a string
        """
        if not self.conn:
            logging.warning("Not connected to database. Returning empty schema.")
            return ""
            
        try:
            schema_query = """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position;
            """
            
            async with self.conn.cursor() as cur:
                await cur.execute(schema_query)
                rows = await cur.fetchall()
                
            tables = {}
            for table_name, column_name, data_type in rows:
                if table_name not in tables:
                    tables[table_name] = []
                tables[table_name].append(f"{column_name} {data_type}")
            
            schema_text = "Database Schema:\n"
            for table, columns in tables.items():
                schema_text += f"\nTABLE {table} (\n  "
                schema_text += ",\n  ".join(columns)
                schema_text += "\n);"
                
            return schema_text
        except Exception as e:
            logging.error(f"Error fetching schema: {e}")
            return "Failed to fetch schema information."
    
    async def validate_sql(self, sql: str) -> Dict[str, Any]:
        """Validate SQL by running EXPLAIN
        
        Args:
            sql: SQL query to validate
            
        Returns:
            Dictionary with validation result
        """
        if not self.conn:
            return {
                "valid": False,
                "error": "Not connected to database"
            }
            
        try:
            explain_sql = f"EXPLAIN {sql}"
            async with self.conn.cursor() as cur:
                await cur.execute(explain_sql)
                plan = await cur.fetchall()
                
            return {
                "valid": True,
                "plan": [row[0] for row in plan]
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def generate_sql(self, query: str) -> Union[SQLResponse, SQLError]:
        """Generate SQL from natural language query
        
        Args:
            query: Natural language query
            
        Returns:
            SQL response or error
        """
        if not HAS_PYDANTIC_AI:
            return SQLError(
                error="pydantic-ai is not installed",
                details="Please install pydantic-ai to use this feature"
            )
            
        # Connect to database if not already connected
        if not self.conn and HAS_PSYCOPG:
            await self.connect()
            
        # Get schema information
        schema_info = await self.get_schema_info()
        
        # Create agent
        agent = Agent[SQLDeps, Union[SQLResponse, SQLError]](
            self.model,
            deps_type=SQLDeps,
            output_type=Union[SQLResponse, SQLError],
            instructions=f"""
            You are an expert SQL query generator for PostgreSQL. 
            Your task is to translate natural language queries into valid PostgreSQL SQL.
            
            {schema_info}
            
            Guidelines:
            - Generate only standard PostgreSQL SQL queries
            - Include appropriate JOINs if data spans multiple tables
            - Use proper SQL syntax and formatting
            - For queries asking for "recent" data, use appropriate date filtering
            - For queries about "errors" or "problems", focus on error-related fields
            - If you cannot generate a valid query, explain why
            """
        )
        
        # Create dependencies
        deps = SQLDeps(conn=self.conn)
        
        try:
            # Run the agent
            result = await agent.run(deps, query)
            
            # Validate SQL if we have a connection
            if isinstance(result, SQLResponse) and self.conn:
                validation = await self.validate_sql(result.sql)
                if not validation["valid"]:
                    return SQLError(
                        error="Generated SQL is invalid",
                        details=validation["error"]
                    )
                    
            return result
        except Exception as e:
            logging.error(f"Error generating SQL: {e}")
            return SQLError(
                error="Failed to generate SQL",
                details=str(e)
            )

async def run_example(query: str, db_config: Optional[Dict[str, Any]] = None):
    """Run the SQL generator example
    
    Args:
        query: Natural language query
        db_config: Optional database configuration
    """
    # Use default config if not provided
    config = db_config or {
        "db_host": "localhost",
        "db_port": 54320,
        "db_name": "logs",
        "db_user": "postgres",
        "db_password": "postgres"
    }
    
    # Create generator
    generator = SQLGenerator(**config)
    
    try:
        # Generate SQL
        print(f"Generating SQL for query: {query}")
        result = await generator.generate_sql(query)
        
        # Display result
        if HAS_RICH and isinstance(result, SQLResponse):
            console.print("\n[bold green]Generated SQL:[/bold green]")
            console.print(Syntax(result.sql, "sql", theme="monokai"))
            if result.explanation:
                console.print("\n[bold blue]Explanation:[/bold blue]")
                console.print(result.explanation)
        elif HAS_RICH and isinstance(result, SQLError):
            console.print("\n[bold red]Error:[/bold red]")
            console.print(result.error)
            if result.details:
                console.print("\n[bold yellow]Details:[/bold yellow]")
                console.print(result.details)
        else:
            # Standard output
            if isinstance(result, SQLResponse):
                print("\nGenerated SQL:")
                print(result.sql)
                if result.explanation:
                    print("\nExplanation:")
                    print(result.explanation)
            else:
                print("\nError:")
                print(result.error)
                if result.details:
                    print("\nDetails:")
                    print(result.details)
    finally:
        # Clean up
        await generator.disconnect()

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "Find all error logs from the last 7 days"
        
    asyncio.run(run_example(query))

if __name__ == "__main__":
    main()