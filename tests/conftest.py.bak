"""
Global pytest fixtures for WrenchAI testing.
"""
import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.agents.base import BaseAgent
from core.models.message import Message
from core.models.task import Task
from core.tools.message_queue import MessageQueue
from core.tools.tool_registry import ToolRegistry

# Configuration Loading
def load_config(config_path: str = "tests/test_configs/test_config.yaml") -> dict:
    """Load test configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

@pytest.fixture(scope="session")
def test_config() -> dict:
    """Fixture to provide test configuration."""
    return load_config()

@pytest.fixture(scope="session")
def agent_config(test_config: dict) -> dict:
    """Fixture to provide agent-specific configuration."""
    return test_config["agent"]

@pytest.fixture(scope="session")
def db_config(test_config: dict) -> dict:
    """Fixture to provide database-specific configuration."""
    return test_config["database"]

# Database Fixtures
@pytest.fixture(scope="session")
async def db_engine(db_config: dict) -> AsyncGenerator[AsyncEngine, None]:
    """Create database engine for testing."""
    engine = create_async_engine(
        db_config["url"],
        echo=db_config["echo"],
        pool_size=db_config["pool_size"],
        max_overflow=db_config["max_overflow"],
        pool_timeout=db_config["pool_timeout"],
        pool_recycle=db_config["pool_recycle"],
    )
    
    try:
        yield engine
    finally:
        await engine.dispose()

@pytest.fixture(scope="session")
def db_session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create database session factory."""
    return async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

@pytest.fixture
async def db_session(
    db_session_factory: async_sessionmaker[AsyncSession]
) -> AsyncGenerator[AsyncSession, None]:
    """Provide database session for testing."""
    async with db_session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()

@pytest.fixture
async def cleanup_test_data(db_session: AsyncSession) -> None:
    """Clean up test data after tests."""
    yield
    # Add cleanup logic here for different tables
    tables = ["messages", "tasks", "agents", "tools"]
    for table in tables:
        await db_session.execute(f"DELETE FROM {table}")
    await db_session.commit()

# Application Fixtures
@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Create FastAPI application for testing."""
    from fastapi.app.main import app
    return app

@pytest.fixture(scope="session")
def test_client(app: FastAPI) -> Generator[TestClient, None, None]:
    """Create test client for FastAPI application."""
    with TestClient(app) as client:
        yield client

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for testing."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Agent Testing Fixtures
@pytest.fixture
async def mock_message_queue() -> AsyncGenerator[MessageQueue, None]:
    """Create mock message queue for testing."""
    queue = MessageQueue()
    try:
        yield queue
    finally:
        await queue.clear()

@pytest.fixture
async def mock_tool_registry() -> AsyncGenerator[ToolRegistry, None]:
    """Create mock tool registry for testing."""
    registry = ToolRegistry()
    try:
        yield registry
    finally:
        await registry.clear()

@pytest.fixture
async def base_agent(
    agent_config: dict,
    mock_message_queue: MessageQueue,
    mock_tool_registry: ToolRegistry,
    db_session: AsyncSession,
) -> AsyncGenerator[BaseAgent, None]:
    """Create base agent instance for testing."""
    agent = BaseAgent(
        agent_id=agent_config["id"],
        name=agent_config["name"],
        description=agent_config["description"],
        capabilities=agent_config["capabilities"],
        message_queue=mock_message_queue,
        tool_registry=mock_tool_registry,
        session=db_session,
    )
    try:
        yield agent
    finally:
        await agent.cleanup()

# Message and Task Fixtures
@pytest.fixture
def sample_message() -> Message:
    """Create sample message for testing."""
    return Message(
        content="Test message",
        sender="test-sender",
        recipient="test-recipient",
        message_type="test",
    )

@pytest.fixture
def sample_task() -> Task:
    """Create sample task for testing."""
    return Task(
        name="test-task",
        description="Test task description",
        priority=1,
        status="pending",
    )

# Utility Fixtures
@pytest.fixture
def temp_file(tmp_path) -> Generator[str, None, None]:
    """Create temporary file for testing."""
    file_path = tmp_path / "test_file.txt"
    with open(file_path, "w") as f:
        f.write("Test content")
    yield str(file_path)
    os.remove(file_path)

@pytest.fixture
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set mock environment variables for testing."""
    env_vars = {
        "TEST_DATABASE_URL": "sqlite+aiosqlite:///test.db",
        "TEST_SECRET_KEY": "test-secret-key",
        "TEST_API_KEY": "test-api-key",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)