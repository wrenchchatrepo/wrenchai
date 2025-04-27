from datetime import datetime
from typing import Dict
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base_class import Base

class Agent(Base):
    """Agent model."""
    __tablename__ = "agents"

    id = Column(String, primary_key=True, index=True)
    role = Column(String, nullable=False)
    config = Column(JSON, nullable=False, default={})
    is_active = Column(Boolean, default=True)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="agents")
    tasks = relationship("Task", back_populates="agent")

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