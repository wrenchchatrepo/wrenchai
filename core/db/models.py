"""SQLAlchemy models for the WrenchAI application."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, 
    Boolean, ForeignKey, Index, JSON, Float
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
    """Model for storing task information."""
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    parameters = Column(JSON)
    result = Column(JSON)
    error = Column(Text)
    
    # Relationships
    executions = relationship("TaskExecution", back_populates="task")
    monitoring_data = relationship("MonitoringData", back_populates="task")

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "parameters": self.parameters,
            "result": self.result,
            "error": self.error
        }

class TaskExecution(Base):
    """Model for storing task execution details."""
    __tablename__ = "task_executions"

    id = Column(String(36), primary_key=True)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    agent_id = Column(String(36), nullable=False)
    status = Column(String(50), nullable=False, default="running")
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime)
    result = Column(JSON)
    error = Column(Text)
    
    # Relationships
    task = relationship("Task", back_populates="executions")

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error
        }

class Journey(Base):
    """Model for storing journey information."""
    __tablename__ = "journeys"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    context = Column(JSON)
    result = Column(JSON)
    error = Column(Text)
    
    # Relationships
    steps = relationship("JourneyStep", back_populates="journey")

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "context": self.context,
            "result": self.result,
            "error": self.error,
            "steps": [step.to_dict() for step in self.steps]
        }

class JourneyStep(Base):
    """Model for storing journey step information."""
    __tablename__ = "journey_steps"

    id = Column(String(36), primary_key=True)
    journey_id = Column(String(36), ForeignKey("journeys.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    order = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    parameters = Column(JSON)
    result = Column(JSON)
    error = Column(Text)
    
    # Relationships
    journey = relationship("Journey", back_populates="steps")

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "journey_id": self.journey_id,
            "name": self.name,
            "description": self.description,
            "order": self.order,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "parameters": self.parameters,
            "result": self.result,
            "error": self.error
        }

class MonitoringData(Base):
    """Model for storing monitoring information."""
    __tablename__ = "monitoring_data"

    id = Column(String(36), primary_key=True)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    success_rate = Column(Float)
    latency = Column(Float)
    error_rate = Column(Float)
    quality_score = Column(Float)
    recommendations = Column(JSON)
    
    # Relationships
    task = relationship("Task", back_populates="monitoring_data")

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "success_rate": self.success_rate,
            "latency": self.latency,
            "error_rate": self.error_rate,
            "quality_score": self.quality_score,
            "recommendations": self.recommendations
        }

class User(Base):
    """Model for storing user information."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        } 