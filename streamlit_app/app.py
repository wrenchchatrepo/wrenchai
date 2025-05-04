"""
WrenchAI Streamlit Application

This module implements the main Streamlit interface for the WrenchAI framework.
It provides a user interface for interacting with the AI agents and managing workflows.
"""

import os
import asyncio
from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime

import streamlit as st
from httpx import AsyncClient

# Import the initializer, which handles all setup tasks
from streamlit_app.utils.initializer import initialize_app, display_messages

# Import session state utilities
from streamlit_app.utils.session_state import StateKey, get_state, set_state, PlaybookExecutionState

# Import components
from streamlit_app.components.midnight_theme import (
    apply_midnight_theme, highlight_card, neon_metric, status_indicator, themed_container
)
from streamlit_app.components.ui_components import (
    code_block, info_card, warning_card, error_card, success_card,
    searchable_selectbox, toggle_button, progress_tracker
)
from streamlit_app.components.streaming_output import create_streaming_output
from streamlit_app.components.chat_file_upload import chat_file_uploader, display_file_message
from streamlit_app.components.log_viewer import log_viewer
from streamlit_app.components.progress_indicators import progress_bar
from streamlit_app.components.playbook_components import playbook_card, playbook_detail_view

# Import services
from streamlit_app.services import (
    create_api_client, create_websocket_client,
    PlaybookService, ExecutionService
)
from streamlit_app.services.websocket_subscriptions import (
    subscribe_to_execution, setup_websocket_handler
)

# Import models
from streamlit_app.models.playbook_config import (
    PlaybookConfig, PlaybookType, PlaybookCategory, 
    ExecutionState, DocusaurusConfig
)

# Import logger
from streamlit_app.utils.logger import get_logger

# Set up module logger
logger = get_logger(__name__)


def sidebar_navigation():
    """Render sidebar navigation menu."""
    with st.sidebar:
        st.title("🔧 WrenchAI")
        st.markdown("---")
        
        # Get configuration from session state
        config = get_state(StateKey.CONFIG)
        
        # Main navigation sections
        st.subheader("Navigation")
        nav_options = ["Home", "Playbooks", "Portfolio Generator", "Documentation", "Settings"]
        
        selected_nav = st.radio("Go To", nav_options, index=0, key="nav_radio")
        if selected_nav != get_state(StateKey.CURRENT_PAGE, "Home"):
            # Update current page
            set_state(StateKey.CURRENT_PAGE, selected_nav)
            # Update breadcrumbs
            set_state(StateKey.BREADCRUMBS, [{"name": "Home", "path": "/"}] if selected_nav == "Home" else 
                                          [{"name": "Home", "path": "/"}, {"name": selected_nav, "path": f"/{selected_nav.lower()}"}])
            # Schedule a rerun to update content
            st.rerun()
        
        st.markdown("---")
        
        # Conditional section based on current page
        current_page = get_state(StateKey.CURRENT_PAGE, "Home")
        
        if current_page == "Playbooks":
            # Playbook categories
            st.subheader("Playbook Categories")
            categories = list(config.playbooks.categories.keys())
            category_names = list(config.playbooks.categories.values())
            selected_category = st.selectbox(
                "Filter by Category",
                categories,
                format_func=lambda x: config.playbooks.categories.get(x, x),
                index=0,
                key="playbook_category"
            )
            # Store selected category in session state
            set_state(StateKey.PLAYBOOK_FILTER, {"category": selected_category, "search": get_state([StateKey.PLAYBOOK_FILTER, "search"], "")})
            
            # Recent playbooks section if any
            execution_history = get_state(StateKey.EXECUTION_HISTORY, [])
            if execution_history:
                st.subheader("Recent Playbooks")
                # Show last 3 unique playbooks from execution history
                unique_playbooks = []
                for execution in reversed(execution_history):
                    playbook_id = execution.get("playbook_id")
                    if playbook_id and playbook_id not in [p.get("id") for p in unique_playbooks] and len(unique_playbooks) < 3:
                        # Find playbook details from playbook list
                        playbook_list = get_state(StateKey.PLAYBOOK_LIST, [])
                        for playbook in playbook_list:
                            if playbook.get("id") == playbook_id:
                                unique_playbooks.append(playbook)
                                break
                
                # Show recent playbooks as buttons
                for playbook in unique_playbooks:
                    if st.button(f"📋 {playbook.get('name', 'Unknown Playbook')}", key=f"recent_{playbook.get('id')}"):
                        set_state(StateKey.SELECTED_PLAYBOOK, playbook.get("id"))
                        st.rerun()
        
        elif current_page == "Portfolio Generator":
            # Portfolio generator options
            st.subheader("Portfolio Options")
            themes = list(config.docusaurus.themes.keys())
            selected_theme = st.selectbox(
                "Theme",
                themes,
                format_func=lambda x: config.docusaurus.themes.get(x, x),
                index=themes.index(config.docusaurus.default_theme) if config.docusaurus.default_theme in themes else 0,
                key="portfolio_theme"
            )
            # Store selected theme in session state
            set_state(StateKey.PORTFOLIO_THEME, selected_theme)
            
            # Portfolio sections selection
            default_sections = config.docusaurus.default_sections
            available_sections = ["introduction", "skills", "projects", "experience", "education", "contact", "blog"]
            selected_sections = st.multiselect(
                "Sections",
                available_sections,
                default=default_sections,
                key="portfolio_sections"
            )
            # Store selected sections in session state
            set_state(StateKey.PORTFOLIO_SECTIONS, selected_sections)
        
        # Feature Toggles for all pages
        st.markdown("---")
        st.subheader("Features")
        for feature, enabled in config.features.items():
            if enabled:
                feature_state = st.checkbox(
                    feature.replace('_', ' ').title(),
                    value=get_state(f"feature_{feature}", True),
                    key=f"feature_{feature}"
                )
                set_state(f"feature_{feature}", feature_state)
        
        # Logs Section
        st.markdown("---")
        st.subheader("Logs & Debugging")
        show_debug = st.checkbox("Debug Mode", value=get_state(StateKey.DEBUG_MODE, False), key="debug_mode")
        set_state(StateKey.DEBUG_MODE, show_debug)
        
        if st.button("View Application Logs"):
            show_logs = not get_state("show_logs", False)
            set_state("show_logs", show_logs)
        
        # Session Info
        st.markdown("---")
        st.caption("Session Information")
        st.text(f"API Version: {config.api.version}")
        
        # API Status indicator
        api_state = get_state(StateKey.API_STATUS)
        if api_state.get("connected", False):
            status_indicator("success", f"API Connected ({api_state.get('ping_latency', 0):.0f}ms)")
        else:
            status_indicator("error", "API Disconnected")


def render_home_page():
    """Render the home page content."""
    st.title("ud83dudd27 WrenchAI Interface")
    
    # Welcome card using themed component
    highlight_card(
        "Welcome to WrenchAI", 
        "An intelligent toolbox for streamlining your development workflow. Select an option from the sidebar to get started.",
        icon="u2728",
        border_color="#7B42F6"
    )
    
    # Quick action buttons
    st.subheader("ud83dudcc3 Quick Actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("ud83dudcd6 Browse Playbooks", use_container_width=True):
            set_state(StateKey.CURRENT_PAGE, "Playbooks")
            set_state(StateKey.BREADCRUMBS, [{"name": "Home", "path": "/"}, {"name": "Playbooks", "path": "/playbooks"}])
            st.rerun()
    with col2:
        if st.button("ud83dudcbb Create Portfolio", use_container_width=True):
            set_state(StateKey.CURRENT_PAGE, "Portfolio Generator")
            set_state(StateKey.BREADCRUMBS, [{"name": "Home", "path": "/"}, {"name": "Portfolio Generator", "path": "/portfolio"}])
            st.rerun()
    with col3:
        if st.button("u2699ufe0f Settings", use_container_width=True):
            set_state(StateKey.CURRENT_PAGE, "Settings")
            set_state(StateKey.BREADCRUMBS, [{"name": "Home", "path": "/"}, {"name": "Settings", "path": "/settings"}])
            st.rerun()
    
    # Show some metrics with neon styling
    st.subheader("ud83dudcca System Overview")
    col1, col2, col3 = st.columns(3)
    with col1:
        neon_metric("Available Playbooks", get_state("playbook_count", 12), delta=2)
    with col2:
        neon_metric("Completed Executions", get_state("execution_count", 42), delta=7)
    with col3:
        neon_metric("API Calls Today", get_state("api_call_count", 156), delta=-12, delta_color="inverse")
    
    # Status indicators
    st.subheader("ud83dudcc8 System Status")
    col1, col2 = st.columns(2)
    with col1:
        api_state = get_state(StateKey.API_STATUS)
        if isinstance(api_state, dict):
            connected = api_state.get("connected", False)
        else:
            connected = getattr(api_state, "connected", False)
            
        if connected:
            status_indicator("success", "API Connected")
        else:
            status_indicator("error", "API Disconnected")
    with col2:
        ws_state = get_state(StateKey.WS_CONNECTION, {"connected": False})
        if ws_state.get("connected", False):
            status_indicator("success", "WebSocket Connected")
        else:
            status_indicator("warning", "WebSocket Disconnected")
    
    # Recent activity
    st.subheader("ud83dudcc5 Recent Activity")
    execution_history = get_state(StateKey.EXECUTION_HISTORY, [])
    if execution_history:
        # Create a table with recent executions
        data = []
        for execution in execution_history[:5]:  # Show last 5
            timestamp = execution.get("timestamp", "")
            if isinstance(timestamp, str):
                try:
                    dt = datetime.fromisoformat(timestamp)
                    timestamp = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    pass
            
            data.append({
                "Time": timestamp,
                "Playbook": execution.get("playbook_id", "Unknown"),
                "Status": execution.get("state", "unknown"),
                "Success": "u2705" if execution.get("success", False) else "u274c" if execution.get("state") in ["completed", "failed", "canceled"] else "u23f3"
            })
        
        # Display data as a DataFrame
        if data:
            import pandas as pd
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
    else:
        info_card("No recent activity", "Execute a playbook to see activity here.")


def render_playbooks_page():
    """Render the playbooks page content."""
    st.title("ud83dudcd6 Playbooks")
    
    # To be implemented
    st.info("Playbooks page will be implemented in Task 9: Develop Playbook Browser and Execution UI")


def render_portfolio_generator_page():
    """Render the portfolio generator page content."""
    st.title("ud83dudcbc Portfolio Generator")
    
    # To be implemented
    st.info("Portfolio Generator page will be implemented in Task 10: Implement Docusaurus Portfolio Playbook Specialized UI")


def render_documentation_page():
    """Render the documentation page content."""
    st.title("ud83dudcd6 Documentation")
    
    # To be implemented
    st.info("Documentation page is under construction")


def render_settings_page():
    """Render the settings page content."""
    st.title("u2699ufe0f Settings")
    
    # To be implemented
    st.info("Settings page is under construction")


def render_breadcrumbs():
    """Render breadcrumb navigation."""
    breadcrumbs = get_state(StateKey.BREADCRUMBS, [{"name": "Home", "path": "/"}])
    
    # Create columns for each breadcrumb plus spacers
    cols = st.columns([1 if i % 2 == 0 else 0.2 for i in range(len(breadcrumbs) * 2 - 1)])
    
    # Fill breadcrumb columns
    for i, breadcrumb in enumerate(breadcrumbs):
        with cols[i * 2]:  # Every other column (0, 2, 4, ...)
            # Make the last breadcrumb non-clickable
            if i == len(breadcrumbs) - 1:
                st.markdown(f"<span style='color: #00CCFF;'>{breadcrumb['name']}</span>", unsafe_allow_html=True)
            else:
                # Create a button for the breadcrumb
                if st.button(f"{breadcrumb['name']}", key=f"breadcrumb_{i}"):
                    set_state(StateKey.CURRENT_PAGE, breadcrumb['name'])
                    # Update breadcrumbs to this level
                    set_state(StateKey.BREADCRUMBS, breadcrumbs[:i+1])
                    st.rerun()
        
        # Add separator between breadcrumbs
        if i < len(breadcrumbs) - 1:
            with cols[i * 2 + 1]:  # Separator columns (1, 3, 5, ...)
                st.markdown("<span style='color: #7B42F6;'>/</span>", unsafe_allow_html=True)


def main_content():
    """Render main content area based on current page."""
    # Get current page from session state
    current_page = get_state(StateKey.CURRENT_PAGE, "Home")
    
    # Render breadcrumb navigation
    render_breadcrumbs()
    
    # Render content based on current page
    if current_page == "Home":
        render_home_page()
    elif current_page == "Playbooks":
        render_playbooks_page()
    elif current_page == "Portfolio Generator":
        render_portfolio_generator_page()
    elif current_page == "Documentation":
        render_documentation_page()
    elif current_page == "Settings":
        render_settings_page()
    else:
        # Unknown page, redirect to home
        st.error(f"Unknown page: {current_page}")
        if st.button("Go to Home"):
            set_state(StateKey.CURRENT_PAGE, "Home")
            set_state(StateKey.BREADCRUMBS, [{"name": "Home", "path": "/"}])
            st.rerun()
    
    # Show logs if requested
    if get_state("show_logs", False) or st.session_state.get("show_logs", False):
        st.subheader("Application Logs")
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
            chat_history = get_state("chat_history", [])
            chat_history.append({"role": "user", "content": user_input, "files": uploaded_files})
            set_state("chat_history", chat_history)
            
            # Show "thinking" status
            update_output("Processing your request...")
            
            # TODO: Implement agent communication
            # Simulated response for demonstration
            import time
            for i in range(5):
                time.sleep(0.5)
                update_output(f"Step {i+1}: Analyzing input...")
                set_state("task_progress", (i + 1) / 5)
            
            # Add simulated response to chat history
            response = "I've analyzed your input and prepared a response. Let me know if you need any clarification!"
            chat_history.append({"role": "assistant", "content": response})
            set_state("chat_history", chat_history)
            update_output(response, append=True)
            
            # Reset progress
            set_state("task_progress", 0.0)
    
    # Display chat history
    st.markdown("### Chat History")
    chat_history = get_state("chat_history", [])
    for message in chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            
            # Display files if present
            if message.get("files"):
                for file in message.get("files", []):
                    display_file_message(file)


def initialize_client() -> AsyncClient:
    """Initialize the API client."""
    config = get_state(StateKey.CONFIG)
    return AsyncClient(
        base_url=config.api.base_url,
        timeout=config.api.timeout,
        verify=config.api.verify_ssl
    )


def main():
    """Main application entry point."""
    try:
        # Initialize application
        config = initialize_app()
        logger.info("Starting WrenchAI Streamlit application")
        
        # Display any pending messages
        display_messages()
        
        # Initialize API client if needed and not already present
        if "client" not in st.session_state:
            st.session_state.client = initialize_client()
        
        # Initialize task progress if not present
        if "task_progress" not in st.session_state:
            st.session_state.task_progress = 0.0
        
        # Initialize chat history if not present
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
            
        # Initialize current page if not present
        if StateKey.CURRENT_PAGE.value not in st.session_state:
            set_state(StateKey.CURRENT_PAGE, "Home")
            
        # Initialize breadcrumbs if not present
        if StateKey.BREADCRUMBS.value not in st.session_state:
            set_state(StateKey.BREADCRUMBS, [{"name": "Home", "path": "/"}])
        
        # Render layout
        sidebar_navigation()
        main_content()
        
    except Exception as e:
        logger.exception("Application error")
        st.error(f"Application error: {str(e)}")
        st.stop()


if __name__ == "__main__":
    # Run the application
    main()