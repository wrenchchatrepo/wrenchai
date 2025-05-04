"""Agent and Task models."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import String, Boolean, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base

class Agent(Base):
    """Agent model for managing AI agents.
    
    Attributes:
        role: Agent's role/type (e.g., "inspector", "journey", "dba")
        config: Agent-specific configuration
        is_active: Whether agent is currently active
        owner_id: ID of user who owns this agent
        tasks: List of tasks assigned to this agent
    """
    role: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        index=True
    )
    config: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    owner_id: Mapped[UUID] = mapped_column(
        UUIDString,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False
    )

    # Relationships
    owner = relationship("User", back_populates="agents")
    tasks: Mapped[List["Task"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan"
    )

class Task(Base):
    """Task model for tracking agent operations.
    
    Attributes:
        agent_id: ID of agent assigned to this task
        task_type: Type of task (e.g., "code_analysis", "optimization")
        input_data: Input parameters and data for the task
        config: Task-specific configuration
        status: Current status (e.g., "pending", "running", "completed")
        progress: Progress percentage (0-100)
        message: Current status message or description
        result: Task execution results
        error: Error message if task failed
    """
    agent_id: Mapped[UUID] = mapped_column(
        UUIDString,
        ForeignKey("agent.id", ondelete="CASCADE"),
        nullable=False
    )
    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    input_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False
    )
    config: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True
    )
    progress: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    message: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True
    )
    error: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    # Relationships
    agent = relationship("Agent", back_populates="tasks")
    executions: Mapped[List["TaskExecution"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan"
    )

class TaskExecution(Base):
    """Task execution history and metrics.
    
    Attributes:
        task_id: ID of the associated task
        start_time: When execution started
        end_time: When execution completed
        status: Execution status
        metrics: Performance metrics and statistics
        logs: Execution logs and output
    """
    task_id: Mapped[UUID] = mapped_column(
        UUIDString,
        ForeignKey("task.id", ondelete="CASCADE"),
        nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="running"
    )
    metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True
    )
    logs: Mapped[Optional[str]] = mapped_column(
        String(5000),
        nullable=True
    )

    # Relationships
    task = relationship("Task", back_populates="executions") 