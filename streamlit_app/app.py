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

# Import the Midnight theme and components
from streamlit_app.components.midnight_theme import apply_midnight_theme, highlight_card, neon_metric, status_indicator
from streamlit_app.components.streaming_output import create_streaming_output
from streamlit_app.components.chat_file_upload import chat_file_uploader, display_file_message
from streamlit_app.components.log_viewer import log_viewer
from streamlit_app.components.progress_indicators import progress_bar

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
    if 'task_progress' not in st.session_state:
        st.session_state.task_progress = 0.0

def setup_page_config():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title=config.ui.page_title,
        page_icon=config.ui.page_icon,
        layout=config.ui.layout,
        initial_sidebar_state=config.ui.initial_sidebar_state
    )

def apply_custom_css():
    """Apply custom CSS styling and Midnight UI theme."""
    # Apply the Midnight UI theme
    apply_midnight_theme()

def sidebar_navigation():
    """Render sidebar navigation menu."""
    with st.sidebar:
        st.title("ud83dudd27 WrenchAI")
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
        
        # Logs Section
        st.markdown("---")
        st.subheader("Logs")
        if st.button("View Application Logs"):
            st.session_state.show_logs = not st.session_state.get("show_logs", False)
        
        # Session Info
        st.markdown("---")
        st.caption("Session Information")
        st.text(f"API Version: {config.api.version}")

def main_content():
    """Render main content area."""
    st.title("ud83dudd27 WrenchAI Interface")
    
    # Welcome card using themed component
    highlight_card(
        "Welcome to WrenchAI", 
        "An intelligent toolbox for streamlining your development workflow. Select an agent from the sidebar to get started.",
        icon="u2728",
        border_color="#7B42F6"
    )
    
    # Show some metrics with neon styling
    col1, col2, col3 = st.columns(3)
    with col1:
        neon_metric("Active Agents", 3, delta=1)
    with col2:
        neon_metric("Tasks Completed", 42, delta=7)
    with col3:
        neon_metric("API Calls", 156, delta=-12, delta_color="inverse")
    
    # Status indicators
    st.subheader("System Status")
    col1, col2 = st.columns(2)
    with col1:
        status_indicator("success", "API Connected")
    with col2:
        status_indicator("info", "Models Loaded")
    
    # Progress Tracking
    st.subheader("Current Task Progress")
    progress_bar(st.session_state.task_progress, "Processing task...")
    
    # Show logs if requested
    if st.session_state.get("show_logs", False):
        st.subheader("Application Logs")
        log_files = {
            "Streamlit": "wrenchai/streamlit.log",
            "WrenchAI": "wrenchai/wrenchai-ui.log",
            "FastAPI": "wrenchai/fastapi.log"
        }
        log_viewer("wrenchai/streamlit.log")
    
    # Chat Interface with Streaming Output
    st.markdown("---")
    st.subheader("Chat with Agent")
    
    # Output display area for streaming responses
    st.markdown("### Agent Output")
    update_output = create_streaming_output(height=200, key="agent_output")
    
    # File upload for chat
    uploaded_files = chat_file_uploader(allowed_types=["txt", "py", "js", "html", "css", "json", "yaml", "yml", "md", "jpg", "png", "pdf"])
    
    # Input area
    user_input = st.text_area("Enter your message:", key="user_input")
    
    if st.button("Send"):
        if user_input or uploaded_files:
            # Add user message to chat history
            st.session_state.chat_history.append({"role": "user", "content": user_input, "files": uploaded_files})
            
            # Show "thinking" status
            update_output("Processing your request...")
            
            # TODO: Implement agent communication
            # Simulated response for demonstration
            import time
            for i in range(5):
                time.sleep(0.5)
                update_output(f"Step {i+1}: Analyzing input...")
                st.session_state.task_progress = (i + 1) / 5
            
            # Add simulated response to chat history
            response = "I've analyzed your input and prepared a response. Let me know if you need any clarification!"
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            update_output(response, append=True)
            
            # Reset progress
            st.session_state.task_progress = 0.0
    
    # Display chat history
    st.markdown("### Chat History")
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            
            # Display files if present
            if message.get("files"):
                for file in message.get("files", []):
                    display_file_message(file)

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