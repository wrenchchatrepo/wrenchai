"""
Initializer Module for WrenchAI Streamlit Application.

This module provides a centralized way to initialize all application components,
including configuration, session state, logging, and other services.
"""

import os
import streamlit as st
import logging
from pathlib import Path
from typing import Dict, Optional, Union

# Import utility modules
from streamlit_app.utils.config_manager import get_config, ApplicationConfig
from streamlit_app.utils.session_state import initialize_session_state, show_messages
from streamlit_app.utils.user_preferences import (
    initialize_user_preferences, 
    initialize_api_state,
    initialize_api_credentials,
    apply_user_preferences
)
from streamlit_app.utils.logger import configure_logging, get_logger, streamlit_log_handler

# Set up module logger
logger = get_logger(__name__)


class AppInitializer:
    """Class to handle application initialization."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the application initializer.
        
        Args:
            config_path: Optional path to the configuration file
        """
        self.config_path = config_path
        self.config = None
    
    def initialize_app(self) -> ApplicationConfig:
        """
        Initialize all application components.
        
        Returns:
            ApplicationConfig: The loaded application configuration
        """
        try:
            # Load configuration first
            self.config = self._load_configuration()
            
            # Configure logging
            self._configure_logging()
            
            # Initialize session state
            self._initialize_session_state()
            
            # Initialize preferences
            self._initialize_preferences()
            
            # Set up page configuration
            self._configure_page()
            
            # Apply user preferences
            self._apply_preferences()
            
            logger.info("Application initialized successfully")
            return self.config
        
        except Exception as e:
            # Handle initialization errors
            st.error(f"Error initializing application: {str(e)}")
            logger.exception("Error during application initialization")
            raise
    
    def _load_configuration(self) -> ApplicationConfig:
        """Load application configuration."""
        config = get_config(self.config_path)
        logger.debug("Configuration loaded")
        return config
    
    def _configure_logging(self) -> None:
        """Configure application logging."""
        configure_logging(self.config.logging)
        
        # Add the Streamlit log handler to the root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(streamlit_log_handler)
        
        logger.debug("Logging configured")
    
    def _initialize_session_state(self) -> None:
        """Initialize session state."""
        initialize_session_state()
        
        # Store configuration in session state for easy access
        st.session_state["config"] = self.config
        
        logger.debug("Session state initialized")
    
    def _initialize_preferences(self) -> None:
        """Initialize user preferences and API state."""
        initialize_user_preferences()
        initialize_api_state()
        initialize_api_credentials()
        
        logger.debug("User preferences and API state initialized")
    
    def _configure_page(self) -> None:
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title=self.config.ui.page_title,
            page_icon=self.config.ui.page_icon,
            layout=self.config.ui.layout,
            initial_sidebar_state=self.config.ui.initial_sidebar_state,
            menu_items={
                'Get Help': 'https://github.com/yourusername/wrenchai',
                'Report a bug': 'https://github.com/yourusername/wrenchai/issues',
                'About': f"## WrenchAI {self.config.api.version}\nAn intelligent toolbox for streamlining your development workflow."
            }
        )
        
        logger.debug("Page configured")
    
    def _apply_preferences(self) -> None:
        """Apply user preferences to the UI."""
        apply_user_preferences()
        logger.debug("User preferences applied")


def initialize_app(config_path: Optional[str] = None) -> ApplicationConfig:
    """
    Initialize the application with the provided configuration.
    
    Args:
        config_path: Optional path to the configuration file
        
    Returns:
        ApplicationConfig: The loaded application configuration
    """
    initializer = AppInitializer(config_path)
    return initializer.initialize_app()


def display_messages() -> None:
    """
    Display any pending messages in the UI.
    
    This function should be called near the top of each page to ensure
    that any messages set by previous operations are displayed.
    """
    show_messages()