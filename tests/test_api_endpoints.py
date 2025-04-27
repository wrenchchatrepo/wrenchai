"""
Integration tests for API endpoints.

These tests verify the functionality of the FastAPI endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator, Dict

from core.db.session import async_session, engine
from core.db.models import Task, Agent, Message, Tool
from app.main import app
from app.core.security import create_access_token
from app.api.deps import get_db

# Override the database dependency
async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        # Create test tables
        await conn.run_sync(Task.metadata.create_all)
        await conn.run_sync(Agent.metadata.create_all)
        await conn.run_sync(Message.metadata.create_all)
        await conn.run_sync(Tool.metadata.create_all)
    
    async with async_session() as session:
        try:
            yield session
        finally:
            # Clean up test tables
            async with engine.begin() as conn:
                await conn.run_sync(Task.metadata.drop_all)
                await conn.run_sync(Agent.metadata.drop_all)
                await conn.run_sync(Message.metadata.drop_all)
                await conn.run_sync(Tool.metadata.drop_all)

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)

@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Create authentication headers."""
    access_token = create_access_token({"sub": "test_user"})
    return {"Authorization": f"Bearer {access_token}"}

def test_health_check(client: TestClient):
    """Test the health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_task(client: TestClient, auth_headers: Dict[str, str]):
    """Test task creation endpoint."""
    task_data = {
        "title": "Test Task",
        "description": "Test Description",
        "priority": "high",
        "status": "pending"
    }
    response = client.post(
        "/api/v1/tasks/",
        json=task_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == task_data["title"]
    assert "id" in data

def test_get_task(client: TestClient, auth_headers: Dict[str, str]):
    """Test task retrieval endpoint."""
    # First create a task
    task_data = {
        "title": "Test Task",
        "description": "Test Description"
    }
    create_response = client.post(
        "/api/v1/tasks/",
        json=task_data,
        headers=auth_headers
    )
    task_id = create_response.json()["id"]
    
    # Then retrieve it
    response = client.get(
        f"/api/v1/tasks/{task_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["title"] == task_data["title"]

def test_update_task(client: TestClient, auth_headers: Dict[str, str]):
    """Test task update endpoint."""
    # Create task
    task_data = {
        "title": "Test Task",
        "description": "Test Description"
    }
    create_response = client.post(
        "/api/v1/tasks/",
        json=task_data,
        headers=auth_headers
    )
    task_id = create_response.json()["id"]
    
    # Update task
    update_data = {"status": "in_progress"}
    response = client.patch(
        f"/api/v1/tasks/{task_id}",
        json=update_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"

def test_delete_task(client: TestClient, auth_headers: Dict[str, str]):
    """Test task deletion endpoint."""
    # Create task
    task_data = {
        "title": "Test Task",
        "description": "Test Description"
    }
    create_response = client.post(
        "/api/v1/tasks/",
        json=task_data,
        headers=auth_headers
    )
    task_id = create_response.json()["id"]
    
    # Delete task
    response = client.delete(
        f"/api/v1/tasks/{task_id}",
        headers=auth_headers
    )
    assert response.status_code == 204
    
    # Verify deletion
    get_response = client.get(
        f"/api/v1/tasks/{task_id}",
        headers=auth_headers
    )
    assert get_response.status_code == 404

def test_list_tasks(client: TestClient, auth_headers: Dict[str, str]):
    """Test task listing endpoint."""
    # Create multiple tasks
    tasks = [
        {"title": "Task 1", "description": "Description 1"},
        {"title": "Task 2", "description": "Description 2"}
    ]
    for task_data in tasks:
        client.post(
            "/api/v1/tasks/",
            json=task_data,
            headers=auth_headers
        )
    
    # List tasks
    response = client.get(
        "/api/v1/tasks/",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(task["title"] == "Task 1" for task in data)
    assert any(task["title"] == "Task 2" for task in data)

def test_filter_tasks(client: TestClient, auth_headers: Dict[str, str]):
    """Test task filtering endpoint."""
    # Create tasks with different statuses
    tasks = [
        {"title": "Task 1", "status": "pending"},
        {"title": "Task 2", "status": "in_progress"}
    ]
    for task_data in tasks:
        client.post(
            "/api/v1/tasks/",
            json=task_data,
            headers=auth_headers
        )
    
    # Filter tasks by status
    response = client.get(
        "/api/v1/tasks/?status=pending",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert all(task["status"] == "pending" for task in data)

def test_pagination(client: TestClient, auth_headers: Dict[str, str]):
    """Test pagination of task listing."""
    # Create multiple tasks
    tasks = [
        {"title": f"Task {i}", "description": f"Description {i}"}
        for i in range(15)
    ]
    for task_data in tasks:
        client.post(
            "/api/v1/tasks/",
            json=task_data,
            headers=auth_headers
        )
    
    # Get first page
    response = client.get(
        "/api/v1/tasks/?skip=0&limit=10",
        headers=auth_headers
    )
    assert response.status_code == 200
    first_page = response.json()
    assert len(first_page) == 10
    
    # Get second page
    response = client.get(
        "/api/v1/tasks/?skip=10&limit=10",
        headers=auth_headers
    )
    assert response.status_code == 200
    second_page = response.json()
    assert len(second_page) == 5

def test_error_handling(client: TestClient, auth_headers: Dict[str, str]):
    """Test API error handling."""
    # Test invalid task ID
    response = client.get(
        "/api/v1/tasks/999999",
        headers=auth_headers
    )
    assert response.status_code == 404
    
    # Test invalid input data
    invalid_data = {"title": ""}  # Empty title
    response = client.post(
        "/api/v1/tasks/",
        json=invalid_data,
        headers=auth_headers
    )
    assert response.status_code == 422
    
    # Test unauthorized access
    response = client.get("/api/v1/tasks/")
    assert response.status_code == 401

def test_rate_limiting(client: TestClient, auth_headers: Dict[str, str]):
    """Test rate limiting middleware."""
    # Make multiple requests in quick succession
    for _ in range(10):
        response = client.get(
            "/api/v1/tasks/",
            headers=auth_headers
        )
    
    # The last request should be rate limited
    response = client.get(
        "/api/v1/tasks/",
        headers=auth_headers
    )
    assert response.status_code == 429 