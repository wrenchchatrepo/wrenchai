"""
UI tests for Streamlit interface.

These tests verify the functionality of the Streamlit UI components.
"""
import pytest
from streamlit.testing.v1 import AppTest
from typing import Dict, List

from streamlit_app.main import app
from core.db.models import Task, Agent
from core.agents.super_agent import SuperAgent
from core.agents.journey_agent import JourneyAgent

@pytest.fixture
def st_test():
    """Create Streamlit test client."""
    return AppTest.from_file("streamlit_app/main.py")

@pytest.fixture
async def agents():
    """Initialize test agents."""
    super_agent = SuperAgent()
    journey_agent = JourneyAgent()
    
    await super_agent.initialize()
    await journey_agent.initialize()
    
    return {
        "super": super_agent,
        "journey": journey_agent
    }

def test_initial_page_load(st_test: AppTest):
    """Test initial page load and basic UI elements."""
    # Run the app
    st_test.run()
    
    # Check main components
    assert st_test.title.value == "WrenchAI"
    assert st_test.sidebar.selectbox("Navigation").value == "Home"
    assert st_test.button("Create Task").exists()

def test_task_creation_form(st_test: AppTest):
    """Test task creation form functionality."""
    st_test.run()
    
    # Navigate to task creation
    st_test.sidebar.selectbox("Navigation").set_value("Create Task")
    
    # Fill form
    st_test.text_input("Title").input("Test Task")
    st_test.text_area("Description").input("Test Description")
    st_test.multiselect("Requirements").set_value(["code_review", "documentation"])
    
    # Submit form
    st_test.button("Create").click()
    
    # Verify success message
    assert "Task created successfully" in st_test.toast[0].value

def test_task_list_view(st_test: AppTest):
    """Test task list view and filtering."""
    st_test.run()
    
    # Navigate to task list
    st_test.sidebar.selectbox("Navigation").set_value("Tasks")
    
    # Test filtering
    st_test.selectbox("Status Filter").set_value("In Progress")
    st_test.button("Apply Filter").click()
    
    # Verify filtered results
    tasks = st_test.dataframe("Tasks").value
    assert all(task["status"] == "in_progress" for task in tasks)

def test_agent_status_dashboard(st_test: AppTest):
    """Test agent status dashboard."""
    st_test.run()
    
    # Navigate to dashboard
    st_test.sidebar.selectbox("Navigation").set_value("Dashboard")
    
    # Verify agent status cards
    assert st_test.metric("Active Agents").exists()
    assert st_test.metric("Tasks in Progress").exists()
    assert st_test.metric("Completed Tasks").exists()

def test_real_time_updates(st_test: AppTest):
    """Test real-time task updates in UI."""
    st_test.run()
    
    # Navigate to task view
    st_test.sidebar.selectbox("Navigation").set_value("Tasks")
    
    # Create test task
    task_data = {
        "title": "Real-time Test",
        "description": "Testing updates",
        "status": "pending"
    }
    st_test.session_state["tasks"].append(task_data)
    
    # Simulate status update
    task_data["status"] = "in_progress"
    st_test.rerun()
    
    # Verify update reflected
    tasks = st_test.dataframe("Tasks").value
    assert any(task["title"] == "Real-time Test" and 
              task["status"] == "in_progress" for task in tasks)

def test_error_handling_display(st_test: AppTest):
    """Test error handling and display in UI."""
    st_test.run()
    
    # Trigger error condition
    st_test.sidebar.selectbox("Navigation").set_value("Create Task")
    st_test.button("Create").click()  # Without required fields
    
    # Verify error message
    assert "Required fields missing" in st_test.error[0].value

def test_task_detail_view(st_test: AppTest):
    """Test task detail view functionality."""
    st_test.run()
    
    # Create test task
    task_data = {
        "id": "test-123",
        "title": "Detail Test",
        "description": "Testing details",
        "status": "pending"
    }
    st_test.session_state["tasks"].append(task_data)
    
    # Navigate to task detail
    st_test.sidebar.selectbox("Navigation").set_value("Tasks")
    st_test.button(f"View {task_data['id']}").click()
    
    # Verify detail components
    assert task_data["title"] in st_test.header[0].value
    assert st_test.text_area("Description").value == task_data["description"]
    assert st_test.selectbox("Status").value == task_data["status"]

def test_agent_interaction(st_test: AppTest, agents: Dict[str, Agent]):
    """Test UI interaction with agents."""
    st_test.run()
    
    # Navigate to agent view
    st_test.sidebar.selectbox("Navigation").set_value("Agents")
    
    # Verify agent list
    agent_list = st_test.dataframe("Agent List").value
    assert any(agent["id"] == agents["super"].id for agent in agent_list)
    assert any(agent["id"] == agents["journey"].id for agent in agent_list)
    
    # Test agent task assignment
    st_test.selectbox("Select Agent").set_value(agents["super"].id)
    st_test.selectbox("Select Task").set_value("test-task")
    st_test.button("Assign Task").click()
    
    # Verify assignment
    assert "Task assigned successfully" in st_test.success[0].value

def test_progress_tracking(st_test: AppTest):
    """Test task progress tracking visualization."""
    st_test.run()
    
    # Navigate to progress view
    st_test.sidebar.selectbox("Navigation").set_value("Progress")
    
    # Add test data
    progress_data = {
        "completed": 5,
        "in_progress": 3,
        "pending": 2
    }
    st_test.session_state["progress"] = progress_data
    
    # Verify progress chart
    assert st_test.plotly_chart("Progress Chart").exists()
    chart_data = st_test.plotly_chart("Progress Chart").value
    assert len(chart_data["data"]) == 3  # Three status categories

def test_settings_configuration(st_test: AppTest):
    """Test settings configuration interface."""
    st_test.run()
    
    # Navigate to settings
    st_test.sidebar.selectbox("Navigation").set_value("Settings")
    
    # Test theme toggle
    st_test.radio("Theme").set_value("Dark")
    assert st_test.session_state["theme"] == "dark"
    
    # Test notification settings
    st_test.checkbox("Enable Notifications").set_value(True)
    assert st_test.session_state["notifications_enabled"] == True

def test_responsive_layout(st_test: AppTest):
    """Test responsive layout behavior."""
    st_test.run()
    
    # Test desktop layout
    st_test.session_state["viewport"] = "desktop"
    assert st_test.sidebar.exists()
    assert st_test.columns[0].exists()
    
    # Test mobile layout
    st_test.session_state["viewport"] = "mobile"
    st_test.rerun()
    assert st_test.button("Menu").exists()  # Mobile menu button 