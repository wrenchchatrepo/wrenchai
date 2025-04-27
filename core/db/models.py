"""SQLAlchemy models for the WrenchAI application."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, 
    Boolean, ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class AuditLog(Base):
    """Audit log model for tracking database operations.
    
    Attributes:
        id: Primary key
        timestamp: When the operation occurred
        user: User who performed the operation
        action: Type of operation (INSERT, UPDATE, DELETE)
        table_name: Name of the affected table
        query: The SQL query that was executed
        affected_rows: Number of rows affected
        execution_time: Time taken to execute the query in milliseconds
    """
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user = Column(String(255), nullable=False)
    action = Column(String(50), nullable=False)
    table_name = Column(String(255), nullable=False)
    query = Column(Text, nullable=False)
    affected_rows = Column(Integer, nullable=False)
    execution_time = Column(Integer, nullable=False)  # in milliseconds
    
    # Indexes
    __table_args__ = (
        Index("ix_audit_logs_timestamp", "timestamp"),
        Index("ix_audit_logs_user", "user"),
    )

class QueryMetrics(Base):
    """Query metrics model for monitoring query performance.
    
    Attributes:
        id: Primary key
        query_hash: Hash of the normalized query
        normalized_query: Query with parameters replaced
        execution_count: Number of times the query was executed
        total_execution_time: Total time spent executing the query
        avg_execution_time: Average execution time
        min_execution_time: Minimum execution time
        max_execution_time: Maximum execution time
        last_executed: When the query was last executed
        row_count: Number of rows returned/affected
    """
    
    __tablename__ = "query_metrics"
    
    id = Column(Integer, primary_key=True)
    query_hash = Column(String(64), nullable=False, unique=True)
    normalized_query = Column(Text, nullable=False)
    execution_count = Column(Integer, default=0, nullable=False)
    total_execution_time = Column(Integer, default=0, nullable=False)  # in milliseconds
    avg_execution_time = Column(Integer, default=0, nullable=False)  # in milliseconds
    min_execution_time = Column(Integer, nullable=True)  # in milliseconds
    max_execution_time = Column(Integer, nullable=True)  # in milliseconds
    last_executed = Column(DateTime(timezone=True), nullable=True)
    row_count = Column(Integer, default=0, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("ix_query_metrics_query_hash", "query_hash"),
        Index("ix_query_metrics_last_executed", "last_executed"),
    )

class Agent(Base):
    """Agent model for storing agent configurations and state.
    
    Attributes:
        id: Primary key
        name: Agent name
        type: Type of agent (e.g., SuperAgent, InspectorAgent)
        config: Agent configuration as JSON
        is_active: Whether the agent is currently active
        created_at: When the agent was created
        updated_at: When the agent was last updated
        last_active: When the agent was last active
    """
    
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    config = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    last_active = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tasks = relationship("Task", back_populates="agent")
    
    # Indexes
    __table_args__ = (
        Index("ix_agents_type", "type"),
        Index("ix_agents_is_active", "is_active"),
    )

class Task(Base):
    """Task model for tracking agent tasks and their status.
    
    Attributes:
        id: Primary key
        agent_id: ID of the agent assigned to the task
        status: Current status of the task
        priority: Task priority (1-5, 1 being highest)
        input_data: Input data for the task as JSON
        output_data: Output data from the task as JSON
        error: Error message if task failed
        started_at: When the task was started
        completed_at: When the task was completed
        created_at: When the task was created
    """
    
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    priority = Column(Integer, nullable=False, default=3)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    agent = relationship("Agent", back_populates="tasks")
    
    # Indexes
    __table_args__ = (
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_priority", "priority"),
        Index("ix_tasks_created_at", "created_at"),
    ) 