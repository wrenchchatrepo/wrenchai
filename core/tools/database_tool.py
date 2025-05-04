from typing import List, Dict, Any, Optional, Union, Tuple
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import create_engine, text, event, inspect, Index, Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
import pandas as pd
from contextlib import contextmanager
import logging
import json
import os
from datetime import datetime, timedelta
import hashlib
import secrets
from cryptography.fernet import Fernet
import threading
from functools import wraps
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import SQLAlchemyError
from typing import Set
from sqlalchemy_utils import database_exists, create_database
import time
import re
from sqlalchemy.sql import func

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class DatabaseConfig(BaseModel):
    """Configuration for database connection"""
    dialect: str = Field(..., description="Database dialect (postgresql, mysql, sqlite, etc.)")
    username: Optional[str] = Field(default=None, description="Database username")
    password: Optional[SecretStr] = Field(default=None, description="Database password")
    host: Optional[str] = Field(default=None, description="Database host")
    port: Optional[int] = Field(default=None, description="Database port")
    database: str = Field(..., description="Database name")
    ssl_mode: Optional[str] = Field(default=None, description="SSL mode for connection")
    pool_size: int = Field(default=5, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Maximum number of connections to overflow")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    pool_recycle: int = Field(default=3600, description="Connection recycle time in seconds")
    echo: bool = Field(default=False, description="Echo SQL statements")
    encrypt_sensitive: bool = Field(default=True, description="Encrypt sensitive data")

class QueryResult(BaseModel):
    """Model for query execution results"""
    success: bool = Field(..., description="Whether the query was successful")
    rowcount: Optional[int] = Field(default=None, description="Number of rows affected")
    results: Optional[List[Dict[str, Any]]] = Field(default=None, description="Query results")
    error_message: Optional[str] = Field(default=None, description="Error message if query failed")
    execution_time: Optional[float] = Field(default=None, description="Query execution time in seconds")
    query_plan: Optional[Dict[str, Any]] = Field(default=None, description="Query execution plan")

class QueryMetrics(BaseModel):
    """Model for tracking query performance metrics"""
    query_hash: str = Field(..., description="Hash of the normalized query")
    normalized_query: str = Field(..., description="Normalized query pattern")
    execution_count: int = Field(default=0, description="Number of times query was executed")
    total_execution_time: float = Field(default=0.0, description="Total execution time in seconds")
    avg_execution_time: float = Field(default=0.0, description="Average execution time in seconds")
    min_execution_time: float = Field(default=float('inf'), description="Minimum execution time in seconds")
    max_execution_time: float = Field(default=0.0, description="Maximum execution time in seconds")
    last_executed: datetime = Field(default_factory=datetime.now, description="Last execution timestamp")
    row_count: int = Field(default=0, description="Number of rows affected by the query")

class SchemaVersion(BaseModel):
    """Model for schema versioning"""
    version_id: str = Field(..., description="Schema version identifier")
    applied_at: datetime = Field(default_factory=datetime.now, description="When this version was applied")
    description: str = Field(..., description="Version description")
    checksum: str = Field(..., description="Schema checksum for validation")

class AuditLog(BaseModel):
    """Model for audit logging"""
    timestamp: datetime = Field(default_factory=datetime.now, description="When the action occurred")
    user: str = Field(..., description="User who performed the action")
    action: str = Field(..., description="Type of action performed")
    table_name: str = Field(..., description="Name of the table affected")
    query: str = Field(..., description="SQL query executed")
    affected_rows: int = Field(..., description="Number of rows affected by the query")
    execution_time: float = Field(..., description="Execution time of the query in seconds")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    task_id = Column(String, unique=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    status = Column(String, index=True)
    priority = Column(String, index=True)
    task_metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), index=True)
    
    # Composite indexes for common query patterns
    __table_args__ = (
        # Index for status-based queries with priority sorting
        Index('idx_task_status_priority', status, priority),
        
        # Index for time-range queries with status filtering
        Index('idx_task_created_status', created_at, status),
        
        # Index for title search with status filtering
        Index('idx_task_title_status', title, status),
        
        # Index for recent updates with status
        Index('idx_task_updated_status', updated_at, status),
        
        # Index for priority-based queries with creation time
        Index('idx_task_priority_created', priority, created_at)
    )

class TaskExecution(Base):
    __tablename__ = "task_executions"
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"))
    agent_id = Column(String, index=True)
    status = Column(String, index=True)
    result = Column(JSON)
    error = Column(JSON)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True))
    duration = Column(Integer)  # in milliseconds
    
    # Composite indexes for execution queries
    __table_args__ = (
        # Index for task-based queries with status
        Index('idx_execution_task_status', task_id, status),
        
        # Index for agent performance analysis
        Index('idx_execution_agent_status', agent_id, status),
        
        # Index for execution time analysis
        Index('idx_execution_started_completed', started_at, completed_at),
        
        # Index for duration-based analysis with status
        Index('idx_execution_duration_status', duration, status)
    )

class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"))
    depends_on_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"))
    
    # Indexes for dependency management
    __table_args__ = (
        # Unique index to prevent duplicate dependencies
        Index('idx_unique_dependency', task_id, depends_on_id, unique=True),
        
        # Index for finding dependent tasks
        Index('idx_dependency_depends_on', depends_on_id)
    )

class DatabaseTool:
    """Tool for database operations and management"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engines: Dict[str, Engine] = {}
        self.sessions: Dict[str, sessionmaker] = {}
        self._connection_lock = threading.Lock()
        self._encryption_key = self._load_or_create_key()
        self._fernet = Fernet(self._encryption_key)
        self.query_metrics: Dict[str, QueryMetrics] = {}
        self.audit_logs: List[AuditLog] = []
        self._setup_metrics_tracking()
        self._setup_engine()
        
    def _load_or_create_key(self) -> bytes:
        """Load or create encryption key"""
        key_file = ".db_encryption_key"
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            return key
            
    def _setup_engine(self) -> None:
        connection_url = f"{self.config.dialect}://{self.config.username}:{self.config.password.get_secret_value()}@{self.config.host}:{self.config.port}/{self.config.database}"
        
        if not database_exists(connection_url):
            create_database(connection_url)
        
        self.engine = create_engine(
            connection_url,
            poolclass=QueuePool,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_timeout=self.config.pool_timeout
        )
        self.Session = sessionmaker(bind=self.engine)
        
        # Set up query timing
        @event.listens_for(self.engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault("query_start_time", []).append(time.time())
            
        @event.listens_for(self.engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total_time = time.time() - conn.info["query_start_time"].pop()
            self._update_query_metrics(statement, total_time, cursor.rowcount)
            
        self.engines["default"] = self.engine
        self.sessions["default"] = self.Session
        
    def _setup_metrics_tracking(self) -> None:
        """Set up query metrics tracking"""
        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
            
        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            execution_time = time.time() - context._query_start_time
            
            # Normalize and hash the query
            normalized_query = self._normalize_query(statement)
            query_hash = hash(normalized_query)
            
            # Update metrics
            if query_hash not in self.query_metrics:
                self.query_metrics[query_hash] = QueryMetrics(
                    query_hash=str(query_hash),
                    normalized_query=normalized_query,
                    execution_count=0,
                    total_execution_time=0,
                    avg_execution_time=0,
                    min_execution_time=float('inf'),
                    max_execution_time=0,
                    last_executed=datetime.now(),
                    row_count=0
                )
            
            metrics = self.query_metrics[query_hash]
            metrics.execution_count += 1
            metrics.total_execution_time += execution_time
            metrics.avg_execution_time = metrics.total_execution_time / metrics.execution_count
            metrics.min_execution_time = min(metrics.min_execution_time, execution_time)
            metrics.max_execution_time = max(metrics.max_execution_time, execution_time)
            metrics.last_executed = datetime.now()
            metrics.row_count = cursor.rowcount

    def _normalize_query(self, query: str) -> str:
        """Normalize a SQL query by replacing literals with placeholders"""
        normalized = re.sub(r"'[^']*'", "'?'", query)
        normalized = re.sub(r"\d+", "?", normalized)
        return normalized

    def _update_query_metrics(self, query: str, execution_time: float, row_count: int) -> None:
        normalized_query = self._normalize_query(query)
        query_hash = hash(normalized_query)
        
        if query_hash not in self.query_metrics:
            self.query_metrics[query_hash] = QueryMetrics(
                query_hash=str(query_hash),
                normalized_query=normalized_query,
                execution_count=0,
                total_execution_time=0,
                avg_execution_time=0,
                min_execution_time=float('inf'),
                max_execution_time=0,
                last_executed=datetime.now(),
                row_count=0
            )
        
        metrics = self.query_metrics[query_hash]
        metrics.execution_count += 1
        metrics.total_execution_time += execution_time
        metrics.avg_execution_time = metrics.total_execution_time / metrics.execution_count
        metrics.min_execution_time = min(metrics.min_execution_time, execution_time)
        metrics.max_execution_time = max(metrics.max_execution_time, execution_time)
        metrics.last_executed = datetime.now()
        metrics.row_count = row_count

    def get_slow_queries(self, threshold: float = 1.0) -> List[QueryMetrics]:
        """Get queries that exceed the average execution time threshold"""
        return [
            metrics for metrics in self.query_metrics.values()
            if metrics.avg_execution_time > threshold
        ]

    def analyze_query_patterns(self) -> Dict[str, Any]:
        """Analyze query patterns and generate optimization suggestions"""
        return {
            'total_unique_queries': len(self.query_metrics),
            'total_executions': sum(m.execution_count for m in self.query_metrics.values()),
            'avg_execution_time': sum(m.avg_execution_time for m in self.query_metrics.values()) / len(self.query_metrics) if self.query_metrics else 0,
            'slow_queries': len(self.get_slow_queries()),
            'most_frequent': sorted(
                self.query_metrics.values(),
                key=lambda x: x.execution_count,
                reverse=True
            )[:5]
        }

    def init_schema_versioning(self, alembic_ini_path: str) -> None:
        """Initialize schema versioning with Alembic."""
        alembic_cfg = Config(alembic_ini_path)
        command.init(alembic_cfg, 'migrations')

    def create_migration(self, alembic_ini_path: str, message: str) -> None:
        """Create a new migration."""
        alembic_cfg = Config(alembic_ini_path)
        command.revision(alembic_cfg, message=message, autogenerate=True)

    def apply_migrations(self, alembic_ini_path: str) -> None:
        """Apply all pending migrations."""
        alembic_cfg = Config(alembic_ini_path)
        command.upgrade(alembic_cfg, 'head')

    def compare_schemas(self, target_schema: str) -> Dict[str, Any]:
        """Compare current schema with target schema."""
        with self.Session() as session:
            current_schema = str(session.execute(text('SELECT current_schema();')).scalar())
            diff_query = f"""
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = :schema
                EXCEPT
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = :target_schema;
            """
            differences = session.execute(
                text(diff_query),
                {'schema': current_schema, 'target_schema': target_schema}
            ).fetchall()
            return {'differences': [dict(d) for d in differences]}

    def add_audit_log(self, user: str, action: str, table_name: str, query: str, affected_rows: int, execution_time: float) -> None:
        """Add an entry to the audit log."""
        log = AuditLog(
            timestamp=datetime.now(),
            user=user,
            action=action,
            table_name=table_name,
            query=query,
            affected_rows=affected_rows,
            execution_time=execution_time
        )
        self.audit_logs.append(log)
        
        # Persist audit log to database
        with self.Session() as session:
            session.execute(
                text("""
                    INSERT INTO audit_logs (timestamp, user, action, table_name, query, affected_rows, execution_time)
                    VALUES (:timestamp, :user, :action, :table_name, :query, :affected_rows, :execution_time)
                """),
                log.dict()
            )
            session.commit()

    def get_audit_logs(self, 
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None,
                      user: Optional[str] = None,
                      action: Optional[str] = None) -> List[AuditLog]:
        """Retrieve filtered audit logs."""
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = {}
        
        if start_time:
            query += " AND timestamp >= :start_time"
            params['start_time'] = start_time
        if end_time:
            query += " AND timestamp <= :end_time"
            params['end_time'] = end_time
        if user:
            query += " AND user = :user"
            params['user'] = user
        if action:
            query += " AND action = :action"
            params['action'] = action
            
        with self.Session() as session:
            results = session.execute(text(query), params).fetchall()
            return [AuditLog(**dict(row)) for row in results]

    def mask_sensitive_data(self, data: str, pattern: str) -> str:
        """Mask sensitive data using a regex pattern."""
        if not self.config.encrypt_sensitive:
            return data
            
        def mask_match(match):
            sensitive_data = match.group(0)
            if self._fernet:
                return self._fernet.encrypt(sensitive_data.encode()).decode()
            return '*' * len(sensitive_data)
            
        return re.sub(pattern, mask_match, data)

    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None, analyze: bool = False) -> QueryResult:
        """Execute a query with optional query plan analysis."""
        start_time = time.time()
        try:
            with self.Session() as session:
                if analyze:
                    explain_query = f"EXPLAIN (FORMAT JSON) {query}"
                    query_plan = session.execute(text(explain_query), params).scalar()
                else:
                    query_plan = None
                    
                result = session.execute(text(query), params)
                rows = [dict(row) for row in result.fetchall()]
                
                execution_time = time.time() - start_time
                return QueryResult(
                    success=True,
                    rowcount=result.rowcount,
                    results=rows,
                    execution_time=execution_time,
                    query_plan=json.loads(query_plan) if query_plan else None,
                    error_message=None
                )
        except Exception as e:
            return QueryResult(
                success=False,
                rowcount=0,
                results=None,
                execution_time=time.time() - start_time,
                query_plan=None,
                error_message=str(e)
            )

    @contextmanager
    def session_scope(self, connection_name: str = "default", retry_count: int = 3):
        """Provide a transactional scope around a series of operations with retry logic"""
        if connection_name not in self.sessions:
            raise ValueError(f"No connection found with name: {connection_name}")
            
        for attempt in range(retry_count):
            session = self.sessions[connection_name]()
            try:
                yield session
                session.commit()
                break
            except Exception as e:
                session.rollback()
                if attempt == retry_count - 1:
                    raise e
                self.logger.warning(f"Retrying transaction (attempt {attempt + 2}/{retry_count})")
            finally:
                session.close()
                
    def execute_script(self, script: str, connection_name: str = "default") -> QueryResult:
        """Execute a SQL script containing multiple statements"""
        try:
            with self.session_scope(connection_name) as session:
                start_time = time.time()
                
                # Split script into individual statements
                statements = [stmt.strip() for stmt in script.split(";") if stmt.strip()]
                results = []
                
                for stmt in statements:
                    result = session.execute(text(stmt))
                    if result.returns_rows:
                        results.extend([
                            self._process_row(dict(row), self.engines[connection_name].dialect.name)
                            for row in result
                        ])
                        
                execution_time = time.time() - start_time
                
                return QueryResult(
                    success=True,
                    results=results if results else None,
                    execution_time=execution_time
                )
        except Exception as e:
            return QueryResult(
                success=False,
                error_message=str(e)
            )
            
    def query_to_dataframe(self, query: str, params: Optional[Dict[str, Any]] = None,
                          connection_name: str = "default") -> pd.DataFrame:
        """Execute a query and return results as a pandas DataFrame"""
        with self.engines[connection_name].connect() as conn:
            return pd.read_sql(text(query), conn, params=params)
            
    def table_exists(self, table_name: str, connection_name: str = "default") -> bool:
        """Check if a table exists in the database"""
        try:
            with self.engines[connection_name].connect() as conn:
                return self.engines[connection_name].dialect.has_table(conn, table_name)
        except Exception as e:
            self.logger.error(f"Error checking table existence: {str(e)}")
            return False
            
    def get_table_schema(self, table_name: str, connection_name: str = "default") -> Optional[Dict[str, Any]]:
        """Get the schema definition for a table"""
        try:
            with self.engines[connection_name].connect() as conn:
                inspector = self.engines[connection_name].dialect.inspector
                if not inspector.has_table(table_name):
                    return None
                    
                columns = inspector.get_columns(table_name)
                pk = inspector.get_pk_constraint(table_name)
                fks = inspector.get_foreign_keys(table_name)
                indexes = inspector.get_indexes(table_name)
                
                return {
                    "columns": columns,
                    "primary_key": pk,
                    "foreign_keys": fks,
                    "indexes": indexes
                }
        except Exception as e:
            self.logger.error(f"Error getting table schema: {str(e)}")
            return None
            
    def create_backup(self, backup_path: str, connection_name: str = "default") -> bool:
        """Create a backup of the database"""
        try:
            engine = self.engines[connection_name]
            dialect = engine.dialect.name
            
            if dialect == "sqlite":
                # For SQLite, we can just copy the file
                import shutil
                database_path = engine.url.database
                shutil.copy2(database_path, backup_path)
            elif dialect == "postgresql":
                # For PostgreSQL, use pg_dump
                import subprocess
                cmd = [
                    "pg_dump",
                    f"--dbname={engine.url.database}",
                    f"--host={engine.url.host}",
                    f"--port={engine.url.port or 5432}",
                    f"--username={engine.url.username}",
                    "--format=custom",
                    f"--file={backup_path}"
                ]
                env = os.environ.copy()
                if engine.url.password:
                    env["PGPASSWORD"] = engine.url.password
                subprocess.run(cmd, env=env, check=True)
            elif dialect == "mysql":
                # For MySQL, use mysqldump
                import subprocess
                cmd = [
                    "mysqldump",
                    f"--host={engine.url.host}",
                    f"--port={engine.url.port or 3306}",
                    f"--user={engine.url.username}",
                    engine.url.database,
                    f"--result-file={backup_path}"
                ]
                env = os.environ.copy()
                if engine.url.password:
                    env["MYSQL_PWD"] = engine.url.password
                subprocess.run(cmd, env=env, check=True)
            else:
                raise NotImplementedError(f"Backup not implemented for {dialect}")
                
            return True
        except Exception as e:
            self.logger.error(f"Error creating backup: {str(e)}")
            return False
            
    def restore_backup(self, backup_path: str, connection_name: str = "default") -> bool:
        """Restore database from a backup"""
        try:
            engine = self.engines[connection_name]
            dialect = engine.dialect.name
            
            if dialect == "sqlite":
                # For SQLite, we can just copy the file
                import shutil
                database_path = engine.url.database
                shutil.copy2(backup_path, database_path)
            elif dialect == "postgresql":
                # For PostgreSQL, use pg_restore
                import subprocess
                cmd = [
                    "pg_restore",
                    f"--dbname={engine.url.database}",
                    f"--host={engine.url.host}",
                    f"--port={engine.url.port or 5432}",
                    f"--username={engine.url.username}",
                    "--clean",
                    backup_path
                ]
                env = os.environ.copy()
                if engine.url.password:
                    env["PGPASSWORD"] = engine.url.password
                subprocess.run(cmd, env=env, check=True)
            elif dialect == "mysql":
                # For MySQL, use mysql client
                import subprocess
                cmd = [
                    "mysql",
                    f"--host={engine.url.host}",
                    f"--port={engine.url.port or 3306}",
                    f"--user={engine.url.username}",
                    engine.url.database
                ]
                env = os.environ.copy()
                if engine.url.password:
                    env["MYSQL_PWD"] = engine.url.password
                with open(backup_path, "rb") as f:
                    subprocess.run(cmd, env=env, input=f.read(), check=True)
            else:
                raise NotImplementedError(f"Restore not implemented for {dialect}")
                
            return True
        except Exception as e:
            self.logger.error(f"Error restoring backup: {str(e)}")
            return False
            
    def optimize_query(self, query: str, connection_name: str = "default") -> Dict[str, Any]:
        """Analyze and optimize a SQL query"""
        try:
            with self.session_scope(connection_name) as session:
                # Get query plan
                explain_stmt = text(query)
                result = session.execute(explain_stmt)
                query_plan = [dict(row) for row in result]
                
                # Analyze query plan
                analysis = self._analyze_query_plan(query_plan)
                
                return {
                    "original_query": query,
                    "query_plan": query_plan,
                    "analysis": analysis,
                    "recommendations": self._generate_optimization_recommendations(analysis)
                }
        except Exception as e:
            self.logger.error(f"Error optimizing query: {str(e)}")
            return {
                "error": str(e)
            }
            
    def _analyze_query_plan(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze a query execution plan"""
        analysis = {
            "table_scans": [],
            "index_usage": [],
            "join_types": [],
            "estimated_rows": 0,
            "estimated_cost": 0
        }
        
        for step in plan:
            if "Seq Scan" in str(step):
                analysis["table_scans"].append(step)
            if "Index" in str(step):
                analysis["index_usage"].append(step)
            if "Join" in str(step):
                analysis["join_types"].append(step)
            if "rows" in step:
                analysis["estimated_rows"] += int(step["rows"])
            if "total_cost" in step:
                analysis["estimated_cost"] += float(step["total_cost"])
                
        return analysis
        
    def _generate_optimization_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate query optimization recommendations"""
        recommendations = []
        
        # Check for table scans
        if analysis["table_scans"]:
            recommendations.append(
                "Consider adding indexes to avoid table scans on: " +
                ", ".join(scan.get("relation", "unknown") for scan in analysis["table_scans"])
            )
            
        # Check join types
        for join in analysis["join_types"]:
            if "Hash Join" in str(join) and analysis["estimated_rows"] > 1000:
                recommendations.append(
                    "Consider using materialized views or pre-computing joins for large datasets"
                )
                
        # Check estimated cost
        if analysis["estimated_cost"] > 1000:
            recommendations.append(
                "Query cost is high. Consider breaking it down into smaller queries or using CTEs"
            )
            
        return recommendations

    def _process_row(self, row: Dict[str, Any], dialect: str) -> Dict[str, Any]:
        """Process a row of data, handling encryption if needed"""
        processed = {}
        for key, value in row.items():
            if isinstance(value, str) and value.startswith("encrypted:"):
                try:
                    decrypted = self._fernet.decrypt(value[10:].encode()).decode()
                    processed[key] = decrypted
                except Exception:
                    processed[key] = value
            else:
                processed[key] = value
        return processed

    def get_query_plan(self, query: str, connection_name: str = "default") -> List[Dict[str, Any]]:
        """
        Get the query execution plan for a given SQL query.
        
        Args:
            query (str): The SQL query to analyze
            connection_name (str): The name of the database connection to use
            
        Returns:
            List[Dict[str, Any]]: The query execution plan
        """
        try:
            with self.session_scope(connection_name) as session:
                # Get query plan using raw SQL EXPLAIN
                explain_query = f"EXPLAIN {query}"
                result = session.execute(text(explain_query))
                query_plan = [dict(row) for row in result]
                
            return query_plan
        except Exception as e:
            self.logger.error(f"Error getting query plan: {str(e)}")
            raise

async def database_operation(operation: str, connection_string: str = None, query: str = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Performs database operations as a tool entry point.

    Args:
        operation: The database operation to perform (query, execute, list_tables, describe_table, connect, disconnect).
        connection_string: The database connection string.
        query: The SQL query to execute (for 'query' and 'execute'). Also used for table name in 'describe_table'.
        params: Query parameters.

    Returns:
        A dictionary containing the result of the operation.
    """
    # Note: This function needs a proper DatabaseTool instance or a way to manage connections.
    # The current implementation below is a placeholder based on the provided arguments
    # and assumes DatabaseTool would be instantiated and used.
    # Correct implementation depends on how DatabaseTool state/instances are managed globally or per request.
    logger.warning("database_operation needs proper DatabaseTool instantiation/management.")

    try:
        # Placeholder: Simulating DB operations. Replace with actual DatabaseTool calls.
        if operation == 'query':
            if query is None:
                 return {
                    "success": False,
                    "error": "query is required for 'query' operation"
                }
            # results = await db_tool.execute_query(query=query, params=params) # Example call
            return { "success": True, "data": f"Simulated query: {query} with params {params}"}
        elif operation == 'execute':
             if query is None:
                 return {
                    "success": False,
                    "error": "query is required for 'execute' operation"
                }
             # results = await db_tool.execute_query(query=query, params=params) # Example call
             return {"success": True, "data": f"Simulated execute: {query} with params {params}"}
        elif operation == 'list_tables':
            # schema = await db_tool.list_tables() # Example call
            return {"success": True, "data": ["table1", "table2"]} # Placeholder
        elif operation == 'describe_table':
            if query is None: # Assuming query holds table name
                 return {
                    "success": False,
                    "error": "query (table name) is required for 'describe_table' operation"
                }
            # schema = await db_tool.get_table_schema(table_name=query) # Example call
            return {"success": True, "data": {"columns": [{"name": "id", "type": "INTEGER"}]}} # Placeholder
        elif operation == 'connect':
            return { "success": True, "message": "Connect operation simulated."}
        elif operation == 'disconnect':
             return { "success": True, "message": "Disconnect operation simulated."}
        else:
            return {
                "success": False,
                "error": f"Invalid operation: {operation}. Supported operations are: query, execute, list_tables, describe_table, connect, disconnect"
            }

    except Exception as e:
        logging.error(f"Database operation failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
