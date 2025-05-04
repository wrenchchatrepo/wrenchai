"""
Session State Management Module for WrenchAI Streamlit Application.

This module provides utilities for managing and persisting application state
across Streamlit reruns and between different pages of the application.
"""

from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, TypeVar, Generic, Union
import streamlit as st
import time
import logging
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

# Type variable for generic state container
T = TypeVar('T')

class StateKey(str, Enum):
    """Enumeration of standardized session state keys."""
    # User and authentication
    USER_INFO = "user_info"
    AUTH_TOKEN = "auth_token"
    
    # API connection
    API_STATUS = "api_status"
    CONNECTION_ERROR = "connection_error"
    API_FEATURES = "api_features"
    WS_CONNECTION = "ws_connection"
    
    # Configuration and preferences
    CONFIG = "config"
    USER_PREFERENCES = "user_preferences"
    THEME = "theme"
    
    # Navigation and UI state
    CURRENT_PAGE = "current_page"
    SIDEBAR_EXPANDED = "sidebar_expanded"
    ACTIVE_TAB = "active_tab"
    BREADCRUMBS = "breadcrumbs"
    NAV_HISTORY = "navigation_history"
    
    # Playbook related
    SELECTED_PLAYBOOK = "selected_playbook"
    PLAYBOOK_PARAMS = "playbook_params"
    PLAYBOOK_LIST = "playbook_list"
    PLAYBOOK_FILTER = "playbook_filter"
    PLAYBOOK_CATEGORIES = "playbook_categories"
    EXECUTION_ID = "execution_id"
    EXECUTION_STATE = "execution_state"
    EXECUTION_RESULTS = "execution_results"
    EXECUTION_LOGS = "execution_logs"
    EXECUTION_HISTORY = "execution_history"
    
    # Docusaurus portfolio specific
    PORTFOLIO_CONFIG = "portfolio_config"
    PORTFOLIO_PREVIEW = "portfolio_preview"
    PORTFOLIO_THEME = "portfolio_theme"
    PORTFOLIO_SECTIONS = "portfolio_sections"
    PORTFOLIO_BUILD_STATUS = "portfolio_build_status"
    PORTFOLIO_DEPLOYMENT = "portfolio_deployment"
    
    # Workspace and project
    CURRENT_PROJECT = "current_project"
    PROJECT_FILES = "project_files"
    FILE_CONTENT = "file_content"
    PROJECT_STRUCTURE = "project_structure"
    
    # Caching and optimization
    CACHE_TIMESTAMP = "cache_timestamp"
    LAST_REFRESH = "last_refresh"
    
    # Misc
    ERROR_MESSAGE = "error_message"
    SUCCESS_MESSAGE = "success_message"
    INFO_MESSAGE = "info_message"
    WARNING_MESSAGE = "warning_message"
    LAST_UPDATED = "last_updated"
    DEBUG_MODE = "debug_mode"


class PlaybookExecutionState(str, Enum):
    """Enumeration of playbook execution states."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    VALIDATING = "validating"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class PlaybookSession:
    """Class for managing playbook execution session state."""
    
    def __init__(self):
        """Initialize playbook session state."""
        self.initialize_state()
    
    def initialize_state(self):
        """Initialize or reset playbook state."""
        # Set default execution state
        set_state(StateKey.EXECUTION_STATE, PlaybookExecutionState.IDLE)
        set_state(StateKey.EXECUTION_ID, None)
        set_state(StateKey.EXECUTION_RESULTS, None)
        set_state(StateKey.EXECUTION_LOGS, [])
    
    def start_execution(self, playbook_id: str, params: Dict[str, Any]) -> str:
        """Start playbook execution and return execution ID."""
        # Store playbook parameters
        set_state(StateKey.PLAYBOOK_PARAMS, params)
        set_state(StateKey.SELECTED_PLAYBOOK, playbook_id)
        
        # Set execution state to initializing
        set_state(StateKey.EXECUTION_STATE, PlaybookExecutionState.INITIALIZING)
        
        # Execution ID should come from the API when actually implemented
        # For now, generate a fake one based on time
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d%H%M%S')}_{playbook_id}"
        set_state(StateKey.EXECUTION_ID, execution_id)
        
        # Initialize empty results
        set_state(StateKey.EXECUTION_RESULTS, {})
        set_state(StateKey.EXECUTION_LOGS, [])
        
        # Add to execution history
        self._update_execution_history(execution_id, playbook_id, params)
        
        return execution_id
    
    def update_execution_state(self, state: PlaybookExecutionState, results: Optional[Dict] = None, logs: Optional[List] = None) -> None:
        """Update execution state, results, and logs."""
        set_state(StateKey.EXECUTION_STATE, state)
        
        if results is not None:
            set_state(StateKey.EXECUTION_RESULTS, results)
        
        if logs is not None:
            current_logs = get_state(StateKey.EXECUTION_LOGS, [])
            updated_logs = current_logs + logs
            set_state(StateKey.EXECUTION_LOGS, updated_logs)
    
    def cancel_execution(self) -> None:
        """Cancel current execution."""
        set_state(StateKey.EXECUTION_STATE, PlaybookExecutionState.CANCELED)
    
    def get_execution_state(self) -> Dict[str, Any]:
        """Get the current execution state as a dictionary."""
        return {
            "execution_id": get_state(StateKey.EXECUTION_ID),
            "playbook_id": get_state(StateKey.SELECTED_PLAYBOOK),
            "state": get_state(StateKey.EXECUTION_STATE),
            "params": get_state(StateKey.PLAYBOOK_PARAMS, {}),
            "results": get_state(StateKey.EXECUTION_RESULTS, {}),
            "logs": get_state(StateKey.EXECUTION_LOGS, []),
        }
    
    def _update_execution_history(self, execution_id: str, playbook_id: str, params: Dict[str, Any]) -> None:
        """Update execution history with new execution."""
        history = get_state(StateKey.EXECUTION_HISTORY, [])
        
        # Add new execution to history
        history.append({
            "execution_id": execution_id,
            "playbook_id": playbook_id,
            "timestamp": datetime.now().isoformat(),
            "params": params,
            "state": PlaybookExecutionState.INITIALIZING
        })
        
        # Limit history size to last 20 executions
        if len(history) > 20:
            history = history[-20:]
        
        set_state(StateKey.EXECUTION_HISTORY, history)
    
class StateContainer(Generic[T]):
    """Generic container for session state values with default handling."""
    
    def __init__(self, key: Union[str, StateKey], default_factory=None):
        """
        Initialize the state container.
        
        Args:
            key: The key in the session state
            default_factory: Optional callable that returns the default value
        """
        self.key = key.value if isinstance(key, StateKey) else key
        self.default_factory = default_factory
    
    def get(self) -> T:
        """Get the value from session state, initializing with default if needed."""
        if self.key not in st.session_state:
            if self.default_factory is not None:
                st.session_state[self.key] = self.default_factory()
            else:
                st.session_state[self.key] = None
        return st.session_state[self.key]
    
    def set(self, value: T) -> None:
        """Set the value in session state and update last modified timestamp."""
        st.session_state[self.key] = value
        # Update the last updated timestamp for this key
        if f"{self.key}_last_updated" not in st.session_state:
            st.session_state[f"{self.key}_last_updated"] = {}
        st.session_state[f"{self.key}_last_updated"] = datetime.now()
    
    def delete(self) -> None:
        """Delete the value from session state if it exists."""
        if self.key in st.session_state:
            del st.session_state[self.key]
        if f"{self.key}_last_updated" in st.session_state:
            del st.session_state[f"{self.key}_last_updated"]


def initialize_session_state():
    """Initialize essential session state variables with defaults."""
    # Basic variables
    if StateKey.LAST_UPDATED.value not in st.session_state:
        st.session_state[StateKey.LAST_UPDATED.value] = datetime.now()
    
    # Debug mode
    if StateKey.DEBUG_MODE.value not in st.session_state:
        st.session_state[StateKey.DEBUG_MODE.value] = False
    
    # Authentication state
    if StateKey.USER_INFO.value not in st.session_state:
        st.session_state[StateKey.USER_INFO.value] = None
    if StateKey.AUTH_TOKEN.value not in st.session_state:
        st.session_state[StateKey.AUTH_TOKEN.value] = None
    
    # API status
    if StateKey.API_STATUS.value not in st.session_state:
        st.session_state[StateKey.API_STATUS.value] = {"connected": False, "ping_latency": None}
    if StateKey.CONNECTION_ERROR.value not in st.session_state:
        st.session_state[StateKey.CONNECTION_ERROR.value] = None
    if StateKey.API_FEATURES.value not in st.session_state:
        st.session_state[StateKey.API_FEATURES.value] = {}
    if StateKey.WS_CONNECTION.value not in st.session_state:
        st.session_state[StateKey.WS_CONNECTION.value] = {"connected": False, "last_message": None}
    
    # UI state
    if StateKey.CURRENT_PAGE.value not in st.session_state:
        st.session_state[StateKey.CURRENT_PAGE.value] = "home"
    if StateKey.SIDEBAR_EXPANDED.value not in st.session_state:
        st.session_state[StateKey.SIDEBAR_EXPANDED.value] = True
    if StateKey.ACTIVE_TAB.value not in st.session_state:
        st.session_state[StateKey.ACTIVE_TAB.value] = "browse"
    if StateKey.BREADCRUMBS.value not in st.session_state:
        st.session_state[StateKey.BREADCRUMBS.value] = [{"name": "Home", "path": "/"}]
    if StateKey.NAV_HISTORY.value not in st.session_state:
        st.session_state[StateKey.NAV_HISTORY.value] = []
    
    # Message containers
    if StateKey.ERROR_MESSAGE.value not in st.session_state:
        st.session_state[StateKey.ERROR_MESSAGE.value] = None
    if StateKey.SUCCESS_MESSAGE.value not in st.session_state:
        st.session_state[StateKey.SUCCESS_MESSAGE.value] = None
    if StateKey.INFO_MESSAGE.value not in st.session_state:
        st.session_state[StateKey.INFO_MESSAGE.value] = None
    if StateKey.WARNING_MESSAGE.value not in st.session_state:
        st.session_state[StateKey.WARNING_MESSAGE.value] = None
    
    # Playbook state
    if StateKey.SELECTED_PLAYBOOK.value not in st.session_state:
        st.session_state[StateKey.SELECTED_PLAYBOOK.value] = None
    if StateKey.PLAYBOOK_PARAMS.value not in st.session_state:
        st.session_state[StateKey.PLAYBOOK_PARAMS.value] = {}
    if StateKey.PLAYBOOK_LIST.value not in st.session_state:
        st.session_state[StateKey.PLAYBOOK_LIST.value] = []
    if StateKey.PLAYBOOK_FILTER.value not in st.session_state:
        st.session_state[StateKey.PLAYBOOK_FILTER.value] = {"category": None, "search": ""}
    if StateKey.PLAYBOOK_CATEGORIES.value not in st.session_state:
        st.session_state[StateKey.PLAYBOOK_CATEGORIES.value] = []
    if StateKey.EXECUTION_STATE.value not in st.session_state:
        st.session_state[StateKey.EXECUTION_STATE.value] = PlaybookExecutionState.IDLE
    if StateKey.EXECUTION_ID.value not in st.session_state:
        st.session_state[StateKey.EXECUTION_ID.value] = None
    if StateKey.EXECUTION_RESULTS.value not in st.session_state:
        st.session_state[StateKey.EXECUTION_RESULTS.value] = {}
    if StateKey.EXECUTION_LOGS.value not in st.session_state:
        st.session_state[StateKey.EXECUTION_LOGS.value] = []
    if StateKey.EXECUTION_HISTORY.value not in st.session_state:
        st.session_state[StateKey.EXECUTION_HISTORY.value] = []
    
    # Portfolio specific state
    if StateKey.PORTFOLIO_CONFIG.value not in st.session_state:
        st.session_state[StateKey.PORTFOLIO_CONFIG.value] = {}
    if StateKey.PORTFOLIO_PREVIEW.value not in st.session_state:
        st.session_state[StateKey.PORTFOLIO_PREVIEW.value] = None
    if StateKey.PORTFOLIO_THEME.value not in st.session_state:
        st.session_state[StateKey.PORTFOLIO_THEME.value] = "classic"
    if StateKey.PORTFOLIO_SECTIONS.value not in st.session_state:
        st.session_state[StateKey.PORTFOLIO_SECTIONS.value] = []
    if StateKey.PORTFOLIO_BUILD_STATUS.value not in st.session_state:
        st.session_state[StateKey.PORTFOLIO_BUILD_STATUS.value] = None
    if StateKey.PORTFOLIO_DEPLOYMENT.value not in st.session_state:
        st.session_state[StateKey.PORTFOLIO_DEPLOYMENT.value] = {"type": None, "url": None, "status": None}
    
    # Project and workspace state
    if StateKey.CURRENT_PROJECT.value not in st.session_state:
        st.session_state[StateKey.CURRENT_PROJECT.value] = None
    if StateKey.PROJECT_FILES.value not in st.session_state:
        st.session_state[StateKey.PROJECT_FILES.value] = []
    if StateKey.FILE_CONTENT.value not in st.session_state:
        st.session_state[StateKey.FILE_CONTENT.value] = {}
    if StateKey.PROJECT_STRUCTURE.value not in st.session_state:
        st.session_state[StateKey.PROJECT_STRUCTURE.value] = {}
    
    # Caching and optimization
    if StateKey.CACHE_TIMESTAMP.value not in st.session_state:
        st.session_state[StateKey.CACHE_TIMESTAMP.value] = {}
    if StateKey.LAST_REFRESH.value not in st.session_state:
        st.session_state[StateKey.LAST_REFRESH.value] = datetime.now()


def get_state(key: Union[str, StateKey], default=None) -> Any:
    """
    Get a value from the session state with a default fallback.
    
    Args:
        key: The session state key
        default: Default value if key doesn't exist
        
    Returns:
        The value from session state or the default
    """
    key_str = key.value if isinstance(key, StateKey) else key
    return st.session_state.get(key_str, default)


def set_state(key: Union[str, StateKey], value: Any) -> None:
    """
    Set a value in the session state.
    
    Args:
        key: The session state key
        value: The value to set
    """
    key_str = key.value if isinstance(key, StateKey) else key
    st.session_state[key_str] = value
    # Update last modified timestamp
    st.session_state[StateKey.LAST_UPDATED.value] = datetime.now()


def delete_state(key: Union[str, StateKey]) -> None:
    """
    Delete a value from session state if it exists.
    
    Args:
        key: The session state key to delete
    """
    key_str = key.value if isinstance(key, StateKey) else key
    if key_str in st.session_state:
        del st.session_state[key_str]


def clear_all_state() -> None:
    """Clear all session state values except essential configuration."""
    # Create a copy of the keys to avoid modification during iteration
    keys = list(st.session_state.keys())
    
    # Keys to preserve (like configuration)
    preserve_keys = {
        StateKey.CONFIG.value, 
        StateKey.USER_PREFERENCES.value,
        StateKey.THEME.value
    }
    
    # Clear all keys except those to preserve
    for key in keys:
        if key not in preserve_keys:
            del st.session_state[key]
    
    # Re-initialize essential state
    initialize_session_state()


def with_state_change_tracking(func):
    """
    Decorator to track changes to session state.
    
    Args:
        func: The function to decorate
        
    Returns:
        Wrapped function that tracks state changes
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Capture state before function execution
        before_state = {k: v for k, v in st.session_state.items()}
        
        # Execute the function
        result = func(*args, **kwargs)
        
        # Compare with state after execution
        after_state = {k: v for k, v in st.session_state.items()}
        
        # Log the changes
        new_keys = set(after_state.keys()) - set(before_state.keys())
        deleted_keys = set(before_state.keys()) - set(after_state.keys())
        modified_keys = {
            k for k in before_state.keys() & after_state.keys()
            if before_state[k] != after_state[k]
        }
        
        if new_keys or deleted_keys or modified_keys:
            logger.debug(f"Session state changes in {func.__name__}:")
            if new_keys:
                logger.debug(f"  New keys: {new_keys}")
            if deleted_keys:
                logger.debug(f"  Deleted keys: {deleted_keys}")
            if modified_keys:
                logger.debug(f"  Modified keys: {modified_keys}")
            
            # Update last modified timestamp
            st.session_state[StateKey.LAST_UPDATED.value] = datetime.now()
        
        return result
    return wrapper


def set_error(message: str) -> None:
    """Set an error message in the session state."""
    set_state(StateKey.ERROR_MESSAGE, message)


def set_success(message: str) -> None:
    """Set a success message in the session state."""
    set_state(StateKey.SUCCESS_MESSAGE, message)


def set_info(message: str) -> None:
    """Set an info message in the session state."""
    set_state(StateKey.INFO_MESSAGE, message)


def set_warning(message: str) -> None:
    """Set a warning message in the session state."""
    set_state(StateKey.WARNING_MESSAGE, message)


def clear_messages() -> None:
    """Clear all message states."""
    delete_state(StateKey.ERROR_MESSAGE)
    delete_state(StateKey.SUCCESS_MESSAGE)
    delete_state(StateKey.INFO_MESSAGE)
    delete_state(StateKey.WARNING_MESSAGE)


def show_messages() -> None:
    """Display all pending messages using Streamlit notifications."""
    # Show error message if present
    error_msg = get_state(StateKey.ERROR_MESSAGE)
    if error_msg:
        st.error(error_msg)
        delete_state(StateKey.ERROR_MESSAGE)
    
    # Show success message if present
    success_msg = get_state(StateKey.SUCCESS_MESSAGE)
    if success_msg:
        st.success(success_msg)
        delete_state(StateKey.SUCCESS_MESSAGE)
    
    # Show info message if present
    info_msg = get_state(StateKey.INFO_MESSAGE)
    if info_msg:
        st.info(info_msg)
        delete_state(StateKey.INFO_MESSAGE)
    
    # Show warning message if present
    warning_msg = get_state(StateKey.WARNING_MESSAGE)
    if warning_msg:
        st.warning(warning_msg)
        delete_state(StateKey.WARNING_MESSAGE)


class SessionStateHistory:
    """Class to track and manage history of session state changes."""
    
    def __init__(self, max_history: int = 100):
        """
        Initialize the history tracker.
        
        Args:
            max_history: Maximum number of history entries to keep
        """
        self.max_history = max_history
        self._history_key = "_session_state_history"
        
        # Initialize history if needed
        if self._history_key not in st.session_state:
            st.session_state[self._history_key] = []
    
    def record_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """
        Record a change to the session state.
        
        Args:
            key: The key that changed
            old_value: The previous value
            new_value: The new value
        """
        history = st.session_state[self._history_key]
        history.append({
            "timestamp": datetime.now(),
            "key": key,
            "old_value": old_value,
            "new_value": new_value
        })
        
        # Trim history if it exceeds the maximum size
        if len(history) > self.max_history:
            st.session_state[self._history_key] = history[-self.max_history:]
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get the complete history of changes."""
        return st.session_state.get(self._history_key, [])
    
    def clear_history(self) -> None:
        """Clear the history of changes."""
        st.session_state[self._history_key] = []
    
    def get_changes_for_key(self, key: str) -> List[Dict[str, Any]]:
        """Get the history of changes for a specific key."""
        history = st.session_state.get(self._history_key, [])
        return [entry for entry in history if entry["key"] == key]