"""
Streamlit tools for managing components and interactions.

This module provides tools for:
- Component creation and management
- State handling
- Layout configuration
- Session state management
- Cache management
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class ComponentType(str, Enum):
    """Types of Streamlit components."""
    TEXT = "text"
    MARKDOWN = "markdown"
    HEADER = "header"
    BUTTON = "button"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    SELECT = "select"
    SLIDER = "slider"
    INPUT = "input"
    FILE_UPLOADER = "file_uploader"
    IMAGE = "image"
    CHART = "chart"
    MAP = "map"
    PROGRESS = "progress"
    SPINNER = "spinner"
    BALLOONS = "balloons"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"

class LayoutConfig(BaseModel):
    """Layout configuration for Streamlit components."""
    columns: int = Field(1, description="Number of columns in layout")
    gap: str = Field("medium", description="Gap between components")
    padding: str = Field("1rem", description="Padding around components")
    align_items: str = Field("start", description="Alignment of items")
    container_width: Optional[str] = Field(None, description="Container width")

class ComponentConfig(BaseModel):
    """Configuration for a Streamlit component."""
    type: ComponentType
    key: str
    label: Optional[str] = None
    value: Any = None
    options: Optional[List[Any]] = None
    help: Optional[str] = None
    disabled: bool = False
    layout: Optional[LayoutConfig] = None

class ComponentState(BaseModel):
    """State of a Streamlit component."""
    key: str = Field(..., description="Unique identifier for the component")
    value: Any = Field(None, description="Current value of the component")
    previous_value: Any = Field(None, description="Previous value of the component")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(1, description="Version of the component state")

class StreamlitState:
    """Manages Streamlit application state."""
    
    def __init__(self):
        self.components: Dict[str, ComponentState] = {}
        self.session_state: Dict[str, Any] = {}
        self.cache: Dict[str, Any] = {}
        self._layout_stack: List[LayoutConfig] = []

    def register_component(self, config: ComponentConfig) -> ComponentState:
        """Register a new component and initialize its state."""
        state = ComponentState(key=config.key, value=config.value)
        self.components[config.key] = state
        return state

    def update_component(self, key: str, value: Any) -> ComponentState:
        """Update a component's state with a new value."""
        if key not in self.components:
            raise KeyError(f"Component {key} not found")
        
        state = self.components[key]
        state.previous_value = state.value
        state.value = value
        state.last_updated = datetime.utcnow()
        state.version += 1
        return state

    def get_component(self, key: str) -> Optional[ComponentState]:
        """Get a component's current state."""
        return self.components.get(key)

    def push_layout(self, layout: LayoutConfig):
        """Push a new layout configuration onto the stack."""
        self._layout_stack.append(layout)

    def pop_layout(self) -> Optional[LayoutConfig]:
        """Pop the current layout configuration from the stack."""
        if self._layout_stack:
            return self._layout_stack.pop()
        return None

    def get_current_layout(self) -> Optional[LayoutConfig]:
        """Get the current layout configuration."""
        if self._layout_stack:
            return self._layout_stack[-1]
        return None

    def set_session_state(self, key: str, value: Any):
        """Set a value in the session state."""
        self.session_state[key] = value

    def get_session_state(self, key: str, default: Any = None) -> Any:
        """Get a value from the session state."""
        return self.session_state.get(key, default)

    def cache_data(self, key: str, value: Any):
        """Cache data for reuse."""
        self.cache[key] = {
            'value': value,
            'timestamp': datetime.utcnow()
        }

    def get_cached_data(self, key: str) -> Optional[Any]:
        """Get cached data if available."""
        if key in self.cache:
            return self.cache[key]['value']
        return None

    def clear_cache(self):
        """Clear all cached data."""
        self.cache.clear()

    def clear_session_state(self):
        """Clear all session state data."""
        self.session_state.clear()

    def clear_all(self):
        """Clear all state, cache, and components."""
        self.components.clear()
        self.session_state.clear()
        self.cache.clear()
        self._layout_stack.clear()

# Global Streamlit state instance
streamlit_state = StreamlitState()

async def create_component(config: ComponentConfig) -> Dict[str, Any]:
    """Create a new Streamlit component.
    
    Args:
        config: Component configuration
        
    Returns:
        Dictionary containing component information
    """
    try:
        state = streamlit_state.register_component(config)
        return {
            "success": True,
            "component": {
                "key": state.key,
                "type": config.type,
                "state": state.dict()
            }
        }
    except Exception as e:
        logger.error(f"Error creating component: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def update_component_state(key: str, value: Any) -> Dict[str, Any]:
    """Update a component's state.
    
    Args:
        key: Component key
        value: New value
        
    Returns:
        Dictionary containing updated state
    """
    try:
        state = streamlit_state.update_component(key, value)
        return {
            "success": True,
            "state": state.dict()
        }
    except KeyError as e:
        return {
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Error updating component state: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def get_component_state(key: str) -> Dict[str, Any]:
    """Get a component's current state.
    
    Args:
        key: Component key
        
    Returns:
        Dictionary containing component state
    """
    try:
        state = streamlit_state.get_component(key)
        if state is None:
            return {
                "success": False,
                "error": f"Component {key} not found"
            }
        return {
            "success": True,
            "state": state.dict()
        }
    except Exception as e:
        logger.error(f"Error getting component state: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def set_layout(layout: LayoutConfig) -> Dict[str, Any]:
    """Set the current layout configuration.
    
    Args:
        layout: Layout configuration
        
    Returns:
        Dictionary containing layout information
    """
    try:
        streamlit_state.push_layout(layout)
        return {
            "success": True,
            "layout": layout.dict()
        }
    except Exception as e:
        logger.error(f"Error setting layout: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def get_layout() -> Dict[str, Any]:
    """Get the current layout configuration.
    
    Returns:
        Dictionary containing layout information
    """
    try:
        layout = streamlit_state.get_current_layout()
        if layout is None:
            return {
                "success": False,
                "error": "No layout configuration found"
            }
        return {
            "success": True,
            "layout": layout.dict()
        }
    except Exception as e:
        logger.error(f"Error getting layout: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def set_session_data(key: str, value: Any) -> Dict[str, Any]:
    """Set session state data.
    
    Args:
        key: Session state key
        value: Value to store
        
    Returns:
        Dictionary containing operation status
    """
    try:
        streamlit_state.set_session_state(key, value)
        return {
            "success": True,
            "message": f"Session state updated for key: {key}"
        }
    except Exception as e:
        logger.error(f"Error setting session state: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def get_session_data(key: str) -> Dict[str, Any]:
    """Get session state data.
    
    Args:
        key: Session state key
        
    Returns:
        Dictionary containing session state data
    """
    try:
        value = streamlit_state.get_session_state(key)
        if value is None:
            return {
                "success": False,
                "error": f"Session state key {key} not found"
            }
        return {
            "success": True,
            "value": value
        }
    except Exception as e:
        logger.error(f"Error getting session state: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def clear_all_state() -> Dict[str, Any]:
    """Clear all state data.
    
    Returns:
        Dictionary containing operation status
    """
    try:
        streamlit_state.clear_all()
        return {
            "success": True,
            "message": "All state cleared successfully"
        }
    except Exception as e:
        logger.error(f"Error clearing state: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        } 