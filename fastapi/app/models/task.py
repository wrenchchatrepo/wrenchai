"""SQLAlchemy model for tasks."""

from datetime import datetime
from typing import Dict, Any
from sqlalchemy import Column, String, JSON, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base_class import Base

class Task(Base):
    """Task model for database storage."""
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String, nullable=False)
    input_data = Column(JSON, nullable=False)
    config = Column(JSON, nullable=False, default=dict)
    status = Column(String, nullable=False, default="pending")
    progress = Column(Float, nullable=False, default=0.0)
    result = Column(JSON, nullable=True)
    error = Column(JSON, nullable=True)
    message = Column(String, nullable=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    playbook_id = Column(UUID(as_uuid=True), ForeignKey("playbooks.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    agent = relationship("Agent", back_populates="tasks")
    playbook = relationship("Playbook", back_populates="tasks")

    def __repr__(self) -> str:
        """
        Returns a concise string representation of the Task instance, including its id, type, and status.
        """
        return f"<Task(id={self.id}, type={self.type}, status={self.status})>" 