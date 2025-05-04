"""
User Preferences Module for WrenchAI Streamlit Application.

This module provides utilities for managing and persisting user preferences
and application settings that are specific to each user session.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union
from enum import Enum
import streamlit as st
import logging
from pydantic import BaseModel, Field, validator
from functools import lru_cache

from streamlit_app.utils.session_state import StateKey, get_state, set_state

logger = logging.getLogger(__name__)


class ThemeOption(str, Enum):
    """Enumeration of theme options."""
    DARK = "dark"
    LIGHT = "light"
    SYSTEM = "system"
    MIDNIGHT = "midnight"  # Custom midnight theme


class LayoutType(str, Enum):
    """Enumeration of layout types."""
    COMPACT = "compact"
    COMFORTABLE = "comfortable"
    SPACIOUS = "spacious"


class PlaybookViewType(str, Enum):
    """Enumeration of playbook view types."""
    GRID = "grid"
    LIST = "list"
    COMPACT = "compact"


class UserPreferences(BaseModel):
    """Model for user preferences."""
    # UI Preferences
    theme: ThemeOption = Field(ThemeOption.DARK, description="UI theme preference")
    layout: LayoutType = Field(LayoutType.COMFORTABLE, description="Layout density preference")
    code_font_size: int = Field(14, description="Font size for code displays")
    enable_animations: bool = Field(True, description="Whether to enable UI animations")
    sidebar_collapsed: bool = Field(False, description="Whether sidebar should be collapsed")
    table_pagination: int = Field(20, description="Number of rows per page in tables")
    date_format: str = Field("YYYY-MM-DD", description="Preferred date format")
    time_format: str = Field("HH:mm:ss", description="Preferred time format")
    
    # File Browser Preferences
    show_hidden_files: bool = Field(False, description="Whether to show hidden files in browser")
    default_code_language: str = Field("python", description="Default language for code display")
    
    # Playbook Preferences
    playbook_view: PlaybookViewType = Field(PlaybookViewType.GRID, description="How to display playbooks")
    default_playbook_category: str = Field("all", description="Default playbook category to display")
    show_playbook_descriptions: bool = Field(True, description="Whether to show playbook descriptions")
    playbooks_per_page: int = Field(12, description="Number of playbooks to show per page")
    show_recent_playbooks: bool = Field(True, description="Whether to show recently used playbooks")
    playbook_execution_auto_scroll: bool = Field(True, description="Whether to auto-scroll during playbook execution")
    
    # Portfolio Preferences
    portfolio_default_theme: str = Field("classic", description="Default theme for Docusaurus portfolios")
    portfolio_default_sections: List[str] = Field(
        ["introduction", "skills", "projects", "experience"], 
        description="Default sections to include in portfolios"
    )
    portfolio_deployment_preference: str = Field("github_pages", description="Preferred deployment method")
    
    # Advanced Options
    advanced_mode: bool = Field(False, description="Whether to show advanced options")
    auto_save: bool = Field(True, description="Whether to auto-save configurations")
    notification_level: str = Field("info", description="Minimum notification level to show")
    experimental_features: bool = Field(False, description="Whether to enable experimental features")
    debug_mode: bool = Field(False, description="Whether to enable debug mode")
    
    # Timestamps
    last_modified: datetime = Field(default_factory=datetime.now, description="When preferences were last modified")
    
    @validator('code_font_size')
    def validate_font_size(cls, v):
        """Validate font size is within reasonable range."""
        if not (10 <= v <= 24):
            raise ValueError(f"Font size must be between 10 and 24, got {v}")
        return v
    
    @validator('notification_level')
    def validate_notification_level(cls, v):
        """Validate notification level."""
        valid_levels = ["debug", "info", "success", "warning", "error"]
        if v.lower() not in valid_levels:
            raise ValueError(f"Notification level must be one of {valid_levels}, got {v}")
        return v.lower()
    
    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


class ApiConnectionState(BaseModel):
    """Model for API connection state."""
    # Basic connection state
    connected: bool = Field(False, description="Whether connected to the API")
    last_connected: Optional[datetime] = Field(None, description="When last successfully connected")
    retry_count: int = Field(0, description="Number of connection retries")
    error: Optional[str] = Field(None, description="Last connection error message")
    status_code: Optional[int] = Field(None, description="Last HTTP status code")
    api_version: Optional[str] = Field(None, description="Connected API version")
    ping_latency: Optional[float] = Field(None, description="API ping latency in ms")
    
    # WebSocket state
    ws_connected: bool = Field(False, description="Whether WebSocket is connected")
    ws_reconnecting: bool = Field(False, description="Whether WebSocket is reconnecting")
    ws_last_message_time: Optional[datetime] = Field(None, description="Time of last WebSocket message")
    ws_error: Optional[str] = Field(None, description="Last WebSocket error message")
    
    # Available features and capabilities
    api_features: Dict[str, bool] = Field(
        default_factory=lambda: {
            "playbooks": False,
            "execution": False,
            "file_upload": False,
            "code_generation": False,
            "portfolio": False,
            "websocket": False,
        },
        description="Available API features"
    )
    
    # Performance metrics
    request_count: int = Field(0, description="Total number of API requests made")
    avg_response_time: Optional[float] = Field(None, description="Average API response time in ms")
    error_count: int = Field(0, description="Total number of API errors")
    
    # Rate limiting information
    rate_limit_remaining: Optional[int] = Field(None, description="Remaining API rate limit")
    rate_limit_reset: Optional[datetime] = Field(None, description="When rate limit resets")
    
    class Config:
        """Pydantic model configuration."""
        validate_assignment = True
        
    def update_connection_status(self, connected: bool, status_code: Optional[int] = None, error: Optional[str] = None) -> None:
        """Update connection status."""
        self.connected = connected
        
        if connected:
            self.last_connected = datetime.now()
            self.error = None
            self.retry_count = 0
        else:
            self.error = error
            self.retry_count += 1
            
        if status_code is not None:
            self.status_code = status_code
            
    def update_websocket_status(self, connected: bool, error: Optional[str] = None) -> None:
        """Update WebSocket connection status."""
        was_connected = self.ws_connected
        self.ws_connected = connected
        
        if connected:
            self.ws_reconnecting = False
            self.ws_error = None
            self.ws_last_message_time = datetime.now()
        else:
            self.ws_error = error
            # Only set reconnecting if we were previously connected
            if was_connected:
                self.ws_reconnecting = True
                
    def update_api_features(self, features: Dict[str, bool]) -> None:
        """Update available API features."""
        self.api_features.update(features)
        
    def record_request(self, response_time: float, is_error: bool = False) -> None:
        """Record an API request for metrics tracking."""
        self.request_count += 1
        
        if is_error:
            self.error_count += 1
            
        # Update average response time
        if self.avg_response_time is None:
            self.avg_response_time = response_time
        else:
            # Calculate new average
            self.avg_response_time = ((self.avg_response_time * (self.request_count - 1)) + response_time) / self.request_count
            
    def update_rate_limits(self, remaining: int, reset_time: datetime) -> None:
        """Update API rate limit information."""
        self.rate_limit_remaining = remaining
        self.rate_limit_reset = reset_time


class AuthType(str, Enum):
    """Enumeration of authentication types."""
    NONE = "none"
    API_KEY = "api_key"
    BASIC = "basic"
    OAUTH = "oauth"
    JWT = "jwt"


class ApiCredentials(BaseModel):
    """Model for API credentials."""
    # Basic authentication fields
    auth_type: AuthType = Field(AuthType.NONE, description="Type of authentication to use")
    api_key: Optional[str] = Field(None, description="API key if required")
    username: Optional[str] = Field(None, description="Username if using basic auth")
    password: Optional[str] = Field(None, description="Password if using basic auth")
    
    # Token management
    token: Optional[str] = Field(None, description="Authentication token")
    token_type: Optional[str] = Field(None, description="Token type (Bearer, etc.)")
    token_expiry: Optional[datetime] = Field(None, description="When the token expires")
    refresh_token: Optional[str] = Field(None, description="Refresh token if applicable")
    
    # User and session info
    user_id: Optional[str] = Field(None, description="User ID if authenticated")
    user_email: Optional[str] = Field(None, description="User email if authenticated")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    session_id: Optional[str] = Field(None, description="Session ID if applicable")
    
    # Preferences
    save_credentials: bool = Field(False, description="Whether to save credentials")
    save_token: bool = Field(False, description="Whether to save token")
    
    # Status
    is_authenticated: bool = Field(False, description="Whether user is authenticated")
    last_authenticated: Optional[datetime] = Field(None, description="When user was last authenticated")
    auth_error: Optional[str] = Field(None, description="Last authentication error message")
    
    class Config:
        """Pydantic model configuration."""
        validate_assignment = True
        
    def is_valid(self) -> bool:
        """Check if credentials are valid and not expired."""
        if not self.is_authenticated:
            return False
            
        if self.token_expiry and datetime.now() > self.token_expiry:
            return False
            
        return True
        
    def needs_refresh(self) -> bool:
        """Check if token needs to be refreshed."""
        if not self.token or not self.token_expiry:
            return False
            
        # Check if token expires in the next 5 minutes
        time_until_expiry = self.token_expiry - datetime.now()
        return time_until_expiry.total_seconds() < 300  # Less than 5 minutes
        
    def clear(self) -> None:
        """Clear sensitive credential information."""
        self.api_key = None
        self.password = None
        self.token = None
        self.refresh_token = None
        self.is_authenticated = False
        
    def authenticate(self, 
                   token: Optional[str] = None, 
                   token_expiry: Optional[datetime] = None,
                   user_id: Optional[str] = None,
                   permissions: Optional[List[str]] = None) -> None:
        """Update authentication state with new token."""
        if token:
            self.token = token
            self.token_expiry = token_expiry
            self.is_authenticated = True
            self.last_authenticated = datetime.now()
            self.auth_error = None
            
            if user_id:
                self.user_id = user_id
                
            if permissions:
                self.permissions = permissions


def initialize_user_preferences() -> UserPreferences:
    """
    Initialize user preferences in session state if not already present.
    
    Returns:
        UserPreferences: The initialized or existing user preferences
    """
    if StateKey.USER_PREFERENCES.value not in st.session_state:
        # Try to load from saved preferences file
        prefs = _load_saved_preferences()
        if prefs is None:
            # Create default preferences
            prefs = UserPreferences()
        
        # Store in session state
        st.session_state[StateKey.USER_PREFERENCES.value] = prefs
    
    return st.session_state[StateKey.USER_PREFERENCES.value]


def initialize_api_state() -> ApiConnectionState:
    """
    Initialize API connection state in session state if not already present.
    
    Returns:
        ApiConnectionState: The initialized or existing API connection state
    """
    if StateKey.API_STATUS.value not in st.session_state:
        # Create default API state
        api_state = ApiConnectionState()
        
        # Store in session state
        st.session_state[StateKey.API_STATUS.value] = api_state
    
    return st.session_state[StateKey.API_STATUS.value]


def initialize_api_credentials() -> ApiCredentials:
    """
    Initialize API credentials in session state if not already present.
    
    Returns:
        ApiCredentials: The initialized or existing API credentials
    """
    if "api_credentials" not in st.session_state:
        # Try to load from saved credentials file if credentials should be saved
        creds = _load_saved_credentials()
        if creds is None:
            # Create default credentials
            creds = ApiCredentials()
        
        # Store in session state
        st.session_state["api_credentials"] = creds
    
    return st.session_state["api_credentials"]


def get_user_preferences() -> UserPreferences:
    """
    Get the current user preferences.
    
    Returns:
        UserPreferences: The current user preferences
    """
    initialize_user_preferences()  # Ensure initialized
    return st.session_state[StateKey.USER_PREFERENCES.value]


def update_user_preferences(preferences: UserPreferences) -> None:
    """
    Update user preferences in session state.
    
    Args:
        preferences: The new preferences to set
    """
    set_state(StateKey.USER_PREFERENCES, preferences)
    preferences.last_modified = datetime.now()
    
    # Save preferences if auto-save is enabled
    if preferences.auto_save:
        _save_preferences(preferences)


def update_preference(key: str, value: Any) -> UserPreferences:
    """
    Update a single user preference.
    
    Args:
        key: The preference key to update
        value: The new value to set
        
    Returns:
        UserPreferences: The updated preferences object
    """
    preferences = get_user_preferences()
    
    if not hasattr(preferences, key):
        raise ValueError(f"Invalid preference key: {key}")
    
    setattr(preferences, key, value)
    preferences.last_modified = datetime.now()
    
    # Update session state
    update_user_preferences(preferences)
    
    return preferences


def update_api_state(state: ApiConnectionState) -> None:
    """
    Update API connection state in session state.
    
    Args:
        state: The new state to set
    """
    set_state(StateKey.API_STATUS, state)


def get_api_state() -> ApiConnectionState:
    """
    Get the current API connection state.
    
    Returns:
        ApiConnectionState: The current API connection state
    """
    initialize_api_state()  # Ensure initialized
    return st.session_state[StateKey.API_STATUS.value]


def update_api_credentials(credentials: ApiCredentials) -> None:
    """
    Update API credentials in session state.
    
    Args:
        credentials: The new credentials to set
    """
    st.session_state["api_credentials"] = credentials
    
    # Save credentials if requested
    if credentials.save_credentials or credentials.save_token:
        _save_credentials(credentials)


def get_api_credentials() -> ApiCredentials:
    """
    Get the current API credentials.
    
    Returns:
        ApiCredentials: The current API credentials
    """
    initialize_api_credentials()  # Ensure initialized
    return st.session_state["api_credentials"]


def clear_api_credentials() -> None:
    """
    Clear API credentials from session state and saved file.
    """
    if "api_credentials" in st.session_state:
        # Clear sensitive data but keep the object
        creds = st.session_state["api_credentials"]
        creds.clear()
    
    # Remove saved credentials file if it exists
    creds_file = _get_credentials_file_path()
    if os.path.exists(creds_file):
        try:
            os.remove(creds_file)
            logger.info("Removed saved API credentials")
        except Exception as e:
            logger.error(f"Error removing saved API credentials: {e}")


default_preferences_folder = os.path.join(os.path.expanduser("~"), ".wrenchai")


def _get_preferences_file_path() -> str:
    """
    Get path to preferences file.
    
    Returns:
        str: Path to preferences file
    """
    folder = os.environ.get("WRENCHAI_PREFERENCES_FOLDER", default_preferences_folder)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "preferences.json")


def _get_credentials_file_path() -> str:
    """
    Get path to credentials file.
    
    Returns:
        str: Path to credentials file
    """
    folder = os.environ.get("WRENCHAI_PREFERENCES_FOLDER", default_preferences_folder)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "credentials.json")


def _save_preferences(preferences: UserPreferences) -> None:
    """
    Save user preferences to file.
    
    Args:
        preferences: The preferences to save
    """
    try:
        file_path = _get_preferences_file_path()
        with open(file_path, 'w') as f:
            # Convert to dictionary and save as JSON
            prefs_dict = preferences.dict()
            # Convert datetime to string for JSON serialization
            prefs_dict["last_modified"] = prefs_dict["last_modified"].isoformat()
            json.dump(prefs_dict, f, indent=2)
        logger.info(f"Saved user preferences to {file_path}")
    except Exception as e:
        logger.error(f"Error saving user preferences: {e}")


def _load_saved_preferences() -> Optional[UserPreferences]:
    """
    Load user preferences from file.
    
    Returns:
        Optional[UserPreferences]: The loaded preferences or None if not found
    """
    try:
        file_path = _get_preferences_file_path()
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                prefs_dict = json.load(f)
                # Convert ISO string back to datetime
                if "last_modified" in prefs_dict and isinstance(prefs_dict["last_modified"], str):
                    prefs_dict["last_modified"] = datetime.fromisoformat(prefs_dict["last_modified"])
                return UserPreferences(**prefs_dict)
    except Exception as e:
        logger.warning(f"Error loading user preferences: {e}")
    
    return None


def _save_credentials(credentials: ApiCredentials) -> None:
    """
    Save API credentials to file.
    
    Args:
        credentials: The credentials to save
    """
    try:
        file_path = _get_credentials_file_path()
        # Create a copy with only the necessary data
        save_data = {}
        
        # Only save what the user has allowed
        if credentials.save_credentials:
            if credentials.auth_type == AuthType.API_KEY:
                save_data["auth_type"] = credentials.auth_type
                save_data["api_key"] = credentials.api_key
            
            elif credentials.auth_type == AuthType.BASIC:
                save_data["auth_type"] = credentials.auth_type
                save_data["username"] = credentials.username
                # Do not save password as plain text
        
        if credentials.save_token:
            save_data["token"] = credentials.token
            save_data["token_type"] = credentials.token_type
            if credentials.token_expiry:
                save_data["token_expiry"] = credentials.token_expiry.isoformat()
            save_data["user_id"] = credentials.user_id
            save_data["user_email"] = credentials.user_email
            save_data["permissions"] = credentials.permissions
        
        # Save preferences
        save_data["save_credentials"] = credentials.save_credentials
        save_data["save_token"] = credentials.save_token
        
        # Only save if there's something to save
        if save_data:
            with open(file_path, 'w') as f:
                json.dump(save_data, f, indent=2)
            logger.info(f"Saved API credentials to {file_path}")
    except Exception as e:
        logger.error(f"Error saving API credentials: {e}")


def _load_saved_credentials() -> Optional[ApiCredentials]:
    """
    Load API credentials from file.
    
    Returns:
        Optional[ApiCredentials]: The loaded credentials or None if not found
    """
    try:
        file_path = _get_credentials_file_path()
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                saved_data = json.load(f)
                
                # Create a new credentials object
                creds = ApiCredentials(
                    save_credentials=saved_data.get("save_credentials", False),
                    save_token=saved_data.get("save_token", False)
                )
                
                # Set authentication type
                if "auth_type" in saved_data:
                    creds.auth_type = saved_data["auth_type"]
                
                # Load API key if present
                if "api_key" in saved_data:
                    creds.api_key = saved_data["api_key"]
                
                # Load username if present
                if "username" in saved_data:
                    creds.username = saved_data["username"]
                
                # Load token data if present
                if "token" in saved_data:
                    creds.token = saved_data["token"]
                    creds.token_type = saved_data.get("token_type")
                    creds.is_authenticated = True
                    creds.user_id = saved_data.get("user_id")
                    creds.user_email = saved_data.get("user_email")
                    creds.permissions = saved_data.get("permissions", [])
                    
                    # Convert token expiry from string to datetime if present
                    if "token_expiry" in saved_data and isinstance(saved_data["token_expiry"], str):
                        try:
                            creds.token_expiry = datetime.fromisoformat(saved_data["token_expiry"])
                            # Check if token is expired
                            if creds.token_expiry < datetime.now():
                                creds.is_authenticated = False
                        except Exception:
                            logger.warning("Could not parse token expiry date")
                
                return creds
    except Exception as e:
        logger.warning(f"Error loading API credentials: {e}")
    
    return None


def apply_user_preferences() -> None:
    """
    Apply user preferences to the Streamlit UI.
    This updates various UI elements based on user preferences.
    """
    preferences = get_user_preferences()
    
    # Apply theme
    if preferences.theme == ThemeOption.MIDNIGHT:
        # Apply custom midnight theme
        from streamlit_app.components.midnight_theme import apply_midnight_theme
        apply_midnight_theme()
    
    # Apply layout
    # Will be used by various components
    
    # Apply sidebar state
    st.session_state["sidebar_collapsed"] = preferences.sidebar_collapsed
    
    # Apply experimental features flag
    st.session_state["experimental_features"] = preferences.experimental_features