"""User model and related schemas."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base

class User(Base):
    """User model.
    
    Attributes:
        email: User's email address
        hashed_password: Hashed password using Argon2
        full_name: User's full name
        is_active: Whether user account is active
        is_superuser: Whether user has superuser privileges
        agents: List of agents owned by this user
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        index=True, 
        nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        default=True, 
        nullable=False
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, 
        default=False, 
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    agents: Mapped[List["Agent"]] = relationship(
        "Agent",
        back_populates="owner",
        cascade="all, delete-orphan"
    ) 