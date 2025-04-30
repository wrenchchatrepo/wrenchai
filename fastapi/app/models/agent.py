"""SQLAlchemy model for agents."""

from typing import Dict, Any
from sqlalchemy import Column, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base_class import Base

class Agent(Base):
    """Agent model for database storage."""
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String, nullable=False)
    config = Column(JSON, nullable=False, default=dict)
    status = Column(String, nullable=False, default="inactive")
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="agents")
    tasks = relationship("Task", back_populates="agent")

    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"<Agent(id={self.id}, type={self.type}, status={self.status})>"

class Task(Base):
    """Task model."""
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    task_type = Column(String, nullable=False)
    input_data = Column(JSON, nullable=False)
    config = Column(JSON, nullable=False, default={})
    status = Column(String, nullable=False, default="pending")
    progress = Column(Float, nullable=False, default=0.0)
    message = Column(String)
    result = Column(JSON)
    error = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="tasks") 