"""
WrenchAI Streamlit Application

This module implements the main Streamlit interface for the WrenchAI framework.
It provides a user interface for interacting with the AI agents and managing workflows.
"""

import os
from typing import Any, Dict, Optional

import streamlit as st
import yaml
from dotenv import load_dotenv
from httpx import AsyncClient
from pydantic import BaseModel

# Load environment variables
load_dotenv()

class ApiConfig(BaseModel):
    """API Configuration."""
    base_url: str
    websocket_url: str
    version: str
    timeout: int

class UiConfig(BaseModel):
    """UI Configuration."""
    page_title: str
    page_icon: str
    layout: str
    initial_sidebar_state: str
    theme: Dict[str, Any]

class LoggingConfig(BaseModel):
    """Logging Configuration."""
    level: str
    format: str
    file: str

class CacheConfig(BaseModel):
    """Cache Configuration."""
    ttl: int
    max_entries: int

class SessionConfig(BaseModel):
    """Session Configuration."""
    expire_after: int
    max_size: int

class Config(BaseModel):
    """Configuration model for the Streamlit app."""
    api: ApiConfig
    ui: UiConfig
    logging: LoggingConfig
    cache: CacheConfig
    session: SessionConfig
    features: Dict[str, bool]

def load_config(config_path: str = "config.yaml") -> Config:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Config: Loaded configuration object
        
    Raises:
        FileNotFoundError: If config file is not found
        yaml.YAMLError: If config file is invalid
    """
    try:
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        return Config(**config_dict)
    except FileNotFoundError:
        st.error(f"Configuration file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        st.error(f"Invalid YAML configuration: {e}")
        raise
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
        raise

def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if 'client' not in st.session_state:
        st.session_state.client = AsyncClient(
            base_url=config.api.base_url,
            timeout=config.api.timeout
        )
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'current_agent' not in st.session_state:
        st.session_state.current_agent = None

def setup_page_config():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title=config.ui.page_title,
        page_icon=config.ui.page_icon,
        layout=config.ui.layout,
        initial_sidebar_state=config.ui.initial_sidebar_state
    )

def apply_custom_css():
    """Apply custom CSS styling."""
    st.markdown("""
        <style>
        .stApp {
            background-color: var(--background-color);
            color: var(--text-color);
        }
        .sidebar .sidebar-content {
            background-color: var(--secondary-background-color);
        }
        </style>
    """, unsafe_allow_html=True)

def sidebar_navigation():
    """Render sidebar navigation menu."""
    with st.sidebar:
        st.title("🔧 WrenchAI")
        st.markdown("---")
        
        # Agent Selection
        st.subheader("Select Agent")
        agent_type = st.selectbox(
            "Choose an agent type",
            ["SuperAgent", "InspectorAgent", "JourneyAgent"]
        )
        
        # Feature Toggles
        st.subheader("Features")
        for feature, enabled in config.features.items():
            if enabled:
                st.checkbox(
                    feature.replace('_', ' ').title(),
                    value=True,
                    key=f"feature_{feature}"
                )
        
        # Session Info
        st.markdown("---")
        st.caption("Session Information")
        st.text(f"API Version: {config.api.version}")

def main_content():
    """Render main content area."""
    st.title("WrenchAI Interface")
    
    # Chat Interface
    st.subheader("Chat with Agent")
    user_input = st.text_area("Enter your message:", key="user_input")
    
    if st.button("Send"):
        if user_input:
            # Add user message to chat history
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            # TODO: Implement agent communication
            # response = await communicate_with_agent(user_input)
            # st.session_state.chat_history.append({"role": "assistant", "content": response})
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

def main():
    """Main application entry point."""
    try:
        # Initialize configuration and session
        initialize_session_state()
        setup_page_config()
        apply_custom_css()
        
        # Render layout
        sidebar_navigation()
        main_content()
        
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.stop()

if __name__ == "__main__":
    # Load configuration
    config = load_config()
    
    # Run the application
    main()