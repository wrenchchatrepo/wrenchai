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
        """
        Initializes the StreamlitState instance with empty component, session, cache, and layout storage.
        """
        self.components: Dict[str, ComponentState] = {}
        self.session_state: Dict[str, Any] = {}
        self.cache: Dict[str, Any] = {}
        self._layout_stack: List[LayoutConfig] = []

    def register_component(self, config: ComponentConfig) -> ComponentState:
        """
        Registers a new component and initializes its state.
        
        Args:
            config: The configuration for the component to register.
        
        Returns:
            The initialized state of the newly registered component.
        """
        state = ComponentState(key=config.key, value=config.value)
        self.components[config.key] = state
        return state

    def update_component(self, key: str, value: Any) -> ComponentState:
        """
        Updates the state of an existing component with a new value.
        
        Raises:
            KeyError: If the specified component key does not exist.
        
        Returns:
            The updated ComponentState instance.
        """
        if key not in self.components:
            raise KeyError(f"Component {key} not found")
        
        state = self.components[key]
        state.previous_value = state.value
        state.value = value
        state.last_updated = datetime.utcnow()
        state.version += 1
        return state

    def get_component(self, key: str) -> Optional[ComponentState]:
        """
        Retrieves the current state of a component by its key.
        
        Args:
            key: The unique identifier of the component.
        
        Returns:
            The ComponentState if the component exists; otherwise, None.
        """
        return self.components.get(key)

    def push_layout(self, layout: LayoutConfig):
        """
        Pushes a new layout configuration onto the layout stack.
        
        Args:
            layout: The layout configuration to add to the stack.
        """
        self._layout_stack.append(layout)

    def pop_layout(self) -> Optional[LayoutConfig]:
        """
        Removes and returns the top layout configuration from the layout stack.
        
        Returns:
            The most recently added LayoutConfig if the stack is not empty; otherwise, None.
        """
        if self._layout_stack:
            return self._layout_stack.pop()
        return None

    def get_current_layout(self) -> Optional[LayoutConfig]:
        """
        Returns the current layout configuration from the top of the layout stack.
        
        Returns:
            The current LayoutConfig if the layout stack is not empty; otherwise, None.
        """
        if self._layout_stack:
            return self._layout_stack[-1]
        return None

    def set_session_state(self, key: str, value: Any):
        """
        Sets a value for the specified key in the session state.
        
        Args:
            key: The session state key to set.
            value: The value to associate with the key.
        """
        self.session_state[key] = value

    def get_session_state(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a value from the session state by key.
        
        Args:
            key: The session state key to retrieve.
            default: The value to return if the key is not found.
        
        Returns:
            The value associated with the key, or the default if the key does not exist.
        """
        return self.session_state.get(key, default)

    def cache_data(self, key: str, value: Any):
        """
        Stores data in the cache with the current UTC timestamp for later retrieval.
        
        Args:
            key: The cache key under which the value is stored.
            value: The data to cache.
        """
        self.cache[key] = {
            'value': value,
            'timestamp': datetime.utcnow()
        }

    def get_cached_data(self, key: str) -> Optional[Any]:
        """
        Retrieves the cached value for a given key if it exists.
        
        Args:
            key: The cache key to look up.
        
        Returns:
            The cached value associated with the key, or None if not found.
        """
        if key in self.cache:
            return self.cache[key]['value']
        return None

    def clear_cache(self):
        """
        Removes all entries from the cache.
        """
        self.cache.clear()

    def clear_session_state(self):
        """
        Clears all session state data.
        
        Removes all key-value pairs from the session state dictionary.
        """
        self.session_state.clear()

    def clear_all(self):
        """
        Clears all components, session state, cache, and layout configurations.
        """
        self.components.clear()
        self.session_state.clear()
        self.cache.clear()
        self._layout_stack.clear()

# Global Streamlit state instance
streamlit_state = StreamlitState()

async def create_component(config: ComponentConfig) -> Dict[str, Any]:
    """
    Registers a new Streamlit component and returns its state information.
    
    Args:
        config: The configuration for the component to be created.
    
    Returns:
        A dictionary indicating success and containing the component's key, type, and state information, or an error message if creation fails.
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
    """
    Asynchronously updates the state of a Streamlit component by key.
    
    Attempts to update the specified component's value and returns the updated state in a dictionary. If the component is not found or an error occurs, returns an error message.
    
    Args:
        key: The unique key identifying the component.
        value: The new value to set for the component.
    
    Returns:
        A dictionary with 'success' indicating the operation result, and either the updated state or an error message.
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
    """
    Retrieves the current state of a specified component.
    
    Returns a dictionary indicating success and the component's state if found, or an error message if the component does not exist or an exception occurs.
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
    """
    Sets the current layout configuration for the Streamlit application.
    
    Args:
        layout: The layout configuration to be applied.
    
    Returns:
        A dictionary indicating success and the applied layout configuration, or an error message if the operation fails.
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
    """
    Retrieves the current layout configuration from the layout stack.
    
    Returns:
        A dictionary with 'success' indicating the operation result. If successful, includes the current layout configuration under 'layout'; otherwise, provides an error message.
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
    """
    Sets a key-value pair in the session state.
    
    Updates the session state with the specified key and value, returning a dictionary
    indicating success or failure.
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
    """
    Retrieves a session state value by key.
    
    Returns a dictionary indicating success and the value if found, or an error message if the key does not exist or an exception occurs.
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
    """
    Clears all components, session state, cache, and layout configurations.
    
    Returns:
        A dictionary indicating whether the operation was successful, with a message or error details.
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