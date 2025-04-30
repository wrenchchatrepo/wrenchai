"""Tests for the Streamlit Tools."""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

from core.tools.streamlit_tools import (
    ComponentType,
    LayoutConfig,
    ComponentConfig,
    ComponentState,
    StreamlitState,
    streamlit_state,
    create_component,
    update_component_state,
    get_component_state,
    set_layout,
    get_layout,
    set_session_data,
    get_session_data,
    clear_all_state
)

@pytest.fixture
def clean_streamlit_state():
    """Provide a clean Streamlit state for each test."""
    streamlit_state.clear_all()
    yield streamlit_state
    streamlit_state.clear_all()

@pytest.fixture
def sample_component_config():
    """Create a sample component configuration."""
    return ComponentConfig(
        type=ComponentType.BUTTON,
        key="test_button",
        label="Test Button",
        value=False,
        help="A test button"
    )

@pytest.fixture
def sample_layout_config():
    """Create a sample layout configuration."""
    return LayoutConfig(
        columns=2,
        gap="large",
        padding="2rem",
        align_items="center",
        container_width="800px"
    )

@pytest.mark.asyncio
async def test_create_component(clean_streamlit_state, sample_component_config):
    """Test component creation."""
    result = await create_component(sample_component_config)
    
    assert result["success"]
    assert result["component"]["key"] == "test_button"
    assert result["component"]["type"] == ComponentType.BUTTON
    assert result["component"]["state"]["value"] is False
    
    # Verify component was registered in state
    assert "test_button" in clean_streamlit_state.components

@pytest.mark.asyncio
async def test_update_component_state(clean_streamlit_state, sample_component_config):
    """Test component state updates."""
    # First create the component
    await create_component(sample_component_config)
    
    # Then update its state
    result = await update_component_state("test_button", True)
    
    assert result["success"]
    assert result["state"]["value"] is True
    assert result["state"]["previous_value"] is False
    assert result["state"]["version"] == 2
    
    # Verify state was updated
    component = clean_streamlit_state.components["test_button"]
    assert component.value is True
    assert component.previous_value is False

@pytest.mark.asyncio
async def test_update_nonexistent_component(clean_streamlit_state):
    """Test updating a component that doesn't exist."""
    result = await update_component_state("nonexistent", True)
    
    assert not result["success"]
    assert "not found" in result["error"]

@pytest.mark.asyncio
async def test_get_component_state(clean_streamlit_state, sample_component_config):
    """Test getting component state."""
    # Create and update component
    await create_component(sample_component_config)
    await update_component_state("test_button", True)
    
    # Get state
    result = await get_component_state("test_button")
    
    assert result["success"]
    assert result["state"]["key"] == "test_button"
    assert result["state"]["value"] is True
    assert result["state"]["version"] == 2

@pytest.mark.asyncio
async def test_get_nonexistent_component_state(clean_streamlit_state):
    """Test getting state of nonexistent component."""
    result = await get_component_state("nonexistent")
    
    assert not result["success"]
    assert "not found" in result["error"]

@pytest.mark.asyncio
async def test_set_layout(clean_streamlit_state, sample_layout_config):
    """Test setting layout configuration."""
    result = await set_layout(sample_layout_config)
    
    assert result["success"]
    assert result["layout"]["columns"] == 2
    assert result["layout"]["gap"] == "large"
    
    # Verify layout was pushed to stack
    current_layout = clean_streamlit_state.get_current_layout()
    assert current_layout is not None
    assert current_layout.columns == 2
    assert current_layout.gap == "large"

@pytest.mark.asyncio
async def test_get_layout_empty(clean_streamlit_state):
    """Test getting layout when none is set."""
    result = await get_layout()
    
    assert not result["success"]
    assert "No layout configuration found" in result["error"]

@pytest.mark.asyncio
async def test_get_layout(clean_streamlit_state, sample_layout_config):
    """Test getting current layout configuration."""
    # First set a layout
    await set_layout(sample_layout_config)
    
    # Then get it
    result = await get_layout()
    
    assert result["success"]
    assert result["layout"]["columns"] == 2
    assert result["layout"]["gap"] == "large"
    assert result["layout"]["padding"] == "2rem"

@pytest.mark.asyncio
async def test_set_session_data(clean_streamlit_state):
    """Test setting session state data."""
    result = await set_session_data("test_key", {"value": 42})
    
    assert result["success"]
    assert "test_key" in result["message"]
    
    # Verify data was stored
    assert clean_streamlit_state.get_session_state("test_key") == {"value": 42}

@pytest.mark.asyncio
async def test_get_session_data(clean_streamlit_state):
    """Test getting session state data."""
    # First set some data
    await set_session_data("test_key", {"value": 42})
    
    # Then get it
    result = await get_session_data("test_key")
    
    assert result["success"]
    assert result["value"] == {"value": 42}

@pytest.mark.asyncio
async def test_get_nonexistent_session_data(clean_streamlit_state):
    """Test getting nonexistent session data."""
    result = await get_session_data("nonexistent")
    
    assert not result["success"]
    assert "not found" in result["error"]

@pytest.mark.asyncio
async def test_clear_all_state(clean_streamlit_state, sample_component_config, sample_layout_config):
    """Test clearing all state data."""
    # Set up some state
    await create_component(sample_component_config)
    await set_layout(sample_layout_config)
    await set_session_data("test_key", {"value": 42})
    
    # Clear everything
    result = await clear_all_state()
    
    assert result["success"]
    assert "cleared successfully" in result["message"]
    
    # Verify everything was cleared
    assert len(clean_streamlit_state.components) == 0
    assert len(clean_streamlit_state.session_state) == 0
    assert len(clean_streamlit_state.cache) == 0
    assert len(clean_streamlit_state._layout_stack) == 0

def test_streamlit_state_cache_operations(clean_streamlit_state):
    """Test cache operations in StreamlitState."""
    # Cache some data
    clean_streamlit_state.cache_data("test_cache", {"value": 42})
    
    # Get cached data
    cached = clean_streamlit_state.get_cached_data("test_cache")
    assert cached == {"value": 42}
    
    # Get nonexistent cache
    assert clean_streamlit_state.get_cached_data("nonexistent") is None
    
    # Clear cache
    clean_streamlit_state.clear_cache()
    assert clean_streamlit_state.get_cached_data("test_cache") is None

def test_streamlit_state_layout_stack(clean_streamlit_state, sample_layout_config):
    """Test layout stack operations in StreamlitState."""
    # Push layout
    clean_streamlit_state.push_layout(sample_layout_config)
    
    # Get current layout
    current = clean_streamlit_state.get_current_layout()
    assert current == sample_layout_config
    
    # Pop layout
    popped = clean_streamlit_state.pop_layout()
    assert popped == sample_layout_config
    
    # Verify stack is empty
    assert clean_streamlit_state.get_current_layout() is None
    assert clean_streamlit_state.pop_layout() is None

def test_component_state_versioning(clean_streamlit_state, sample_component_config):
    """Test component state versioning."""
    # Create initial state
    state = clean_streamlit_state.register_component(sample_component_config)
    assert state.version == 1
    
    # Update multiple times
    for i in range(3):
        state = clean_streamlit_state.update_component(state.key, f"value_{i}")
        assert state.version == i + 2
        assert state.previous_value == f"value_{i-1}" if i > 0 else False

def test_layout_config_defaults():
    """Test LayoutConfig default values."""
    layout = LayoutConfig()
    
    assert layout.columns == 1
    assert layout.gap == "medium"
    assert layout.padding == "1rem"
    assert layout.align_items == "start"
    assert layout.container_width is None

def test_component_config_validation():
    """Test ComponentConfig validation."""
    # Test required fields
    with pytest.raises(ValueError):
        ComponentConfig()  # Missing required fields
    
    # Test valid config
    config = ComponentConfig(
        type=ComponentType.TEXT,
        key="test"
    )
    assert config.type == ComponentType.TEXT
    assert config.key == "test"
    assert config.value is None
    assert config.disabled is False

def test_component_state_timestamps():
    """Test ComponentState timestamp handling."""
    state = ComponentState(key="test")
    initial_time = state.last_updated
    
    # Wait a moment and update
    state.value = "new_value"
    state.last_updated = datetime.utcnow()
    
    assert state.last_updated > initial_time 