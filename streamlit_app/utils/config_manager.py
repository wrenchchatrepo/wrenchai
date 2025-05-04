"""
Configuration Management Module for WrenchAI Streamlit Application.

This module provides utilities for loading, managing, and validating application
configuration from various sources including files, environment variables, and defaults.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union, TypeVar
from functools import lru_cache
import logging
from pydantic import BaseModel, Field, validator, root_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Define configuration model
class ApiConfig(BaseModel):
    """API Configuration model."""
    base_url: str = Field("http://localhost:8000", description="Base URL for the API")
    websocket_url: str = Field("ws://localhost:8000/ws", description="WebSocket URL for real-time communication")
    version: str = Field("v1", description="API version")
    timeout: int = Field(30, description="Request timeout in seconds")
    auth_enabled: bool = Field(False, description="Whether authentication is required")
    auth_url: Optional[str] = Field(None, description="Authentication endpoint URL")
    verify_ssl: bool = Field(True, description="Whether to verify SSL certificates")
    
    @validator('base_url', 'websocket_url')
    def validate_urls(cls, v):
        """Validate URL format."""
        if not v.startswith(("http://", "https://", "ws://", "wss://")):
            raise ValueError(f"Invalid URL format: {v}")
        return v


class UiConfig(BaseModel):
    """UI Configuration model."""
    page_title: str = Field("WrenchAI", description="Browser page title")
    page_icon: str = Field("🔧", description="Favicon/icon for the app")
    layout: str = Field("wide", description="Page layout (wide or centered)")
    initial_sidebar_state: str = Field("expanded", description="Initial sidebar state")
    theme: Dict[str, Any] = Field(
        {
            "primaryColor": "#FF10F0",  # Neon Pink
            "backgroundColor": "#0A0A0A",  # Pure Black
            "secondaryBackgroundColor": "#1B1B1B",  # Dark Grey
            "textColor": "#E3E3E3",  # Soft White
            "font": "sans serif"
        },
        description="UI theme configuration"
    )
    
    @validator('layout')
    def validate_layout(cls, v):
        """Validate layout value."""
        if v not in ["wide", "centered"]:
            raise ValueError(f"Invalid layout: {v}. Must be 'wide' or 'centered'")
        return v
    
    @validator('initial_sidebar_state')
    def validate_sidebar_state(cls, v):
        """Validate sidebar state value."""
        if v not in ["expanded", "collapsed"]:
            raise ValueError(f"Invalid sidebar state: {v}. Must be 'expanded' or 'collapsed'")
        return v


class LoggingConfig(BaseModel):
    """Logging Configuration model."""
    level: str = Field("INFO", description="Logging level")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
        description="Log message format"
    )
    file: str = Field("wrenchai-ui.log", description="Log file path")
    console: bool = Field(True, description="Whether to log to console")
    rotation: bool = Field(True, description="Whether to use rotating log files")
    max_size: int = Field(10, description="Maximum log file size in MB")
    backup_count: int = Field(5, description="Number of backup log files to keep")
    
    @validator('level')
    def validate_level(cls, v):
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid logging level: {v}. Must be one of {valid_levels}")
        return v.upper()


class PlaybookConfig(BaseModel):
    """Playbook configuration model."""
    display_name: str = Field("Playbooks", description="Display name for the playbooks section")
    icon: str = Field("📚", description="Icon for the playbooks section")
    categories: Dict[str, str] = Field(
        {
            "all": "All Playbooks",
            "code": "Code Generation",
            "docs": "Documentation",
            "analysis": "Code Analysis",
            "deployment": "Deployment",
            "portfolio": "Portfolio"
        },
        description="Playbook categories with display names"
    )
    default_category: str = Field("all", description="Default category to display")
    show_descriptions: bool = Field(True, description="Whether to show playbook descriptions")
    grid_view: bool = Field(True, description="Whether to use grid view instead of list view")
    enable_search: bool = Field(True, description="Whether to enable search functionality")
    enable_filtering: bool = Field(True, description="Whether to enable category filtering")
    items_per_page: int = Field(12, description="Number of playbooks to show per page")
    show_pagination: bool = Field(True, description="Whether to show pagination")
    
    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


class CacheConfig(BaseModel):
    """Cache Configuration model."""
    enabled: bool = Field(True, description="Whether caching is enabled")
    ttl: int = Field(3600, description="Time to live in seconds")
    max_entries: int = Field(1000, description="Maximum cache entries")
    persist: bool = Field(False, description="Whether to persist cache to disk")
    cache_dir: str = Field(".cache", description="Cache directory if persisting to disk")


class DocusaurusConfig(BaseModel):
    """Docusaurus Portfolio configuration model."""
    display_name: str = Field("Portfolio Generator", description="Display name for the portfolio generator")
    icon: str = Field("ud83dudcdC", description="Icon for the portfolio generator")
    themes: Dict[str, str] = Field(
        {
            "classic": "Classic",
            "dark": "Dark",
            "modern": "Modern",
            "tech": "Tech",
            "minimal": "Minimal"
        },
        description="Available portfolio themes"
    )
    default_theme: str = Field("classic", description="Default theme to use")
    default_sections: List[str] = Field(
        ["introduction", "skills", "projects", "experience", "education", "contact"],
        description="Default sections to include in the portfolio"
    )
    github_integration: bool = Field(True, description="Whether to enable GitHub integration")
    preview_enabled: bool = Field(True, description="Whether to enable preview functionality")
    deployment_options: Dict[str, bool] = Field(
        {
            "github_pages": True,
            "vercel": True,
            "netlify": True
        },
        description="Available deployment options"
    )
    max_projects: int = Field(10, description="Maximum number of projects to include")
    
    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


class SessionConfig(BaseModel):
    """Session Configuration model."""
    expire_after: int = Field(3600, description="Session expiry in seconds")
    max_size: int = Field(100, description="Maximum session storage size in MB")
    secure: bool = Field(False, description="Whether to use secure cookies")
    use_cookies: bool = Field(False, description="Whether to use cookies for session ID")
    cookie_name: str = Field("wrenchai_session", description="Cookie name if using cookies")


class ApplicationConfig(BaseModel):
    """Complete Application Configuration model."""
    api: ApiConfig = Field(default_factory=ApiConfig)
    ui: UiConfig = Field(default_factory=UiConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    session: SessionConfig = Field(default_factory=SessionConfig)
    playbooks: PlaybookConfig = Field(default_factory=PlaybookConfig)
    docusaurus: DocusaurusConfig = Field(default_factory=DocusaurusConfig)
    features: Dict[str, bool] = Field(
        {
            "enable_websocket": True,
            "enable_file_upload": True,
            "enable_code_preview": True,
            "enable_agent_monitoring": True,
            "enable_portfolio_generator": True,
            "enable_playbook_browser": True,
            "enable_realtime_logs": True,
            "enable_advanced_config": True
        },
        description="Feature flags for enabling/disabling features"
    )
    # Environment-specific overrides
    environment: str = Field("development", description="Application environment")
    dev_mode: bool = Field(False, description="Whether development mode is enabled")
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "forbid"


class ConfigManager:
    """Configuration Manager for loading and handling application config."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Optional path to the configuration file
        """
        self.config_path = config_path or "config.yaml"
        self.config = self._load_config()
    
    def _load_config(self) -> ApplicationConfig:
        """
        Load configuration from file and environment variables.
        
        Returns:
            ApplicationConfig: The loaded configuration
        """
        # Start with default configuration
        config_dict = {}
        
        # Try to load from YAML file
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        config_dict.update(file_config)
                        logger.info(f"Loaded configuration from {self.config_path}")
        except Exception as e:
            logger.warning(f"Could not load configuration from {self.config_path}: {e}")
        
        # Apply environment variable overrides
        self._apply_env_overrides(config_dict)
        
        # Create Pydantic model with the config
        try:
            return ApplicationConfig(**config_dict)
        except Exception as e:
            logger.error(f"Error creating configuration model: {e}")
            # Fall back to default configuration
            return ApplicationConfig()
    
    def _apply_env_overrides(self, config_dict: Dict[str, Any]) -> None:
        """
        Apply environment variable overrides to configuration.
        
        Environment variables are expected in the format WRENCHAI_SECTION_KEY=value.
        For example, WRENCHAI_API_BASE_URL would override api.base_url.
        
        Args:
            config_dict: Configuration dictionary to update with env vars
        """
        prefix = "WRENCHAI_"
        for env_var, value in os.environ.items():
            if env_var.startswith(prefix):
                # Remove prefix and split into parts
                parts = env_var[len(prefix):].lower().split('_', 1)
                if len(parts) == 2:
                    section, key = parts
                    
                    # Create sections if they don't exist
                    if section not in config_dict:
                        config_dict[section] = {}
                    
                    # Handle boolean values
                    if value.lower() in ('true', 'yes', 'on', '1'):
                        value = True
                    elif value.lower() in ('false', 'no', 'off', '0'):
                        value = False
                    
                    # Handle integer values
                    try:
                        if value.isdigit():
                            value = int(value)
                    except (AttributeError, ValueError):
                        pass
                    
                    # Update config
                    if isinstance(config_dict[section], dict):
                        config_dict[section][key] = value
                        logger.debug(f"Applied environment override: {env_var}")
    
    def get_config(self) -> ApplicationConfig:
        """Get the current configuration."""
        return self.config
    
    def reload(self) -> ApplicationConfig:
        """Reload configuration from sources."""
        self.config = self._load_config()
        return self.config
    
    def save_config(self, config: ApplicationConfig, path: Optional[str] = None) -> None:
        """
        Save configuration to a file.
        
        Args:
            config: The configuration to save
            path: Optional path to save to, defaults to the loaded path
        """
        save_path = path or self.config_path
        try:
            # Convert to dictionary and save as YAML
            config_dict = config.dict()
            with open(save_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False)
            logger.info(f"Saved configuration to {save_path}")
        except Exception as e:
            logger.error(f"Error saving configuration to {save_path}: {e}")
            raise
    
    def update_config(self, section: str, key: str, value: Any) -> ApplicationConfig:
        """
        Update a specific configuration value.
        
        Args:
            section: Configuration section (api, ui, etc.)
            key: Configuration key within the section
            value: New value to set
            
        Returns:
            ApplicationConfig: Updated configuration
        """
        # Validate the section
        if not hasattr(self.config, section):
            raise ValueError(f"Invalid configuration section: {section}")
        
        # Get the section object
        section_obj = getattr(self.config, section)
        
        # Validate the key
        if not hasattr(section_obj, key):
            raise ValueError(f"Invalid configuration key: {key} in section {section}")
        
        # Update the value
        try:
            setattr(section_obj, key, value)
            logger.info(f"Updated configuration {section}.{key} = {value}")
            return self.config
        except Exception as e:
            logger.error(f"Error updating configuration {section}.{key}: {e}")
            raise


@lru_cache(maxsize=1)
def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """
    Get or create a ConfigManager instance (singleton).
    
    Args:
        config_path: Optional path to the configuration file
        
    Returns:
        ConfigManager: The configuration manager instance
    """
    return ConfigManager(config_path)


def get_config(config_path: Optional[str] = None) -> ApplicationConfig:
    """
    Get the application configuration.
    
    Args:
        config_path: Optional path to the configuration file
        
    Returns:
        ApplicationConfig: The application configuration
    """
    return get_config_manager(config_path).get_config()