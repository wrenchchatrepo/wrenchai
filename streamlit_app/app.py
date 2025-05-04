"""WrenchAI Streamlit Application main entry point."""

import streamlit as st
from typing import Dict, List, Any, Optional

# Import utility functions 
from wrenchai.streamlit_app.utils.session_state import (
    StateKey, 
    get_state, 
    set_state, 
    initialize_session_state, 
    display_messages
)
from wrenchai.streamlit_app.utils.logger import get_logger
from wrenchai.streamlit_app.utils.config import load_config, initialize_app
from wrenchai.streamlit_app.utils.ui_components import status_indicator
from wrenchai.streamlit_app.agent_communication import ensure_api_connection

# Import components
from wrenchai.streamlit_app.components import (
    hero_section,
    quick_action_card,
    section_container,
    feature_card
)

# Setup logging
logger = get_logger(__name__)

# Configure page
st.set_page_config(
    page_title="WrenchAI",
    page_icon="ud83dudd27",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Define the main navigation structure using the new Streamlit multipage app pattern
pg = st.navigation([
    st.Page("wrenchai/streamlit_app/app.py", title="Home", icon="ud83cudfe0", default=True),
    st.Page("wrenchai/streamlit_app/pages/playbooks.py", title="Playbooks", icon="ud83euddf0"), 
    st.Page("wrenchai/streamlit_app/pages/portfolio_generator.py", title="Portfolio Generator", icon="ud83dudc68u200dud83dudcbb"),
    st.Page("wrenchai/streamlit_app/pages/docusaurus_portfolio.py", title="Docusaurus Portfolio", icon="ud83dudcd6"),
    st.Page("wrenchai/streamlit_app/pages/documentation.py", title="Documentation", icon="ud83dudcda"),
    st.Page("wrenchai/streamlit_app/pages/settings.py", title="Settings", icon="u2699ufe0f")
])

def sidebar_navigation():
    """Render sidebar navigation menu with additional context-dependent options."""
    with st.sidebar:
        st.title("ud83dudd27 WrenchAI")
        st.markdown("---")
        
        # Get configuration from session state
        config = get_state(StateKey.CONFIG)
        
        # Feature Toggles for all pages
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
    # Hero section with title and subtitle
    hero_section(
        title="Welcome to WrenchAI", 
        subtitle="Your AI-powered development assistant", 
        image_path="https://via.placeholder.com/1200x600?text=WrenchAI+Hero+Image"
    )
    
    # Quick action cards
    st.subheader("Quick Actions")
    cols = st.columns(3)
    
    with cols[0]:
        quick_action_card(
            title="Browse Playbooks", 
            description="Explore automation playbooks for common development tasks", 
            icon="ud83euddf0", 
            button_text="Go to Playbooks", 
            on_click=lambda: st.switch_page("wrenchai/streamlit_app/pages/playbooks.py")
        )
    
    with cols[1]:
        quick_action_card(
            title="Create Portfolio", 
            description="Generate a professional portfolio website with Docusaurus", 
            icon="ud83dudc68u200dud83dudcbb", 
            button_text="Start Now", 
            on_click=lambda: st.switch_page("wrenchai/streamlit_app/pages/docusaurus_portfolio.py")
        )
    
    with cols[2]:
        quick_action_card(
            title="Read Documentation", 
            description="Learn how to use WrenchAI and its features", 
            icon="ud83dudcda", 
            button_text="View Docs", 
            on_click=lambda: st.switch_page("wrenchai/streamlit_app/pages/documentation.py")
        )
    
    # Feature overview
    with section_container("What can WrenchAI do?"):
        st.write("WrenchAI is your AI-powered development assistant, helping you automate common tasks and create professional portfolio websites.")
        
        # Feature rows
        col1, col2 = st.columns(2)
        
        with col1:
            feature_card(
                title="Automation Playbooks", 
                description="Execute pre-configured playbooks for common development tasks, from project setup to deployment.",
                icon="ud83euddf0"
            )
            
            feature_card(
                title="Portfolio Generation", 
                description="Create a professional portfolio website using Docusaurus with just a few clicks.",
                icon="ud83dudc68u200dud83dudcbb"
            )
        
        with col2:
            feature_card(
                title="API Integration", 
                description="Connect to external services and APIs to extend functionality.",
                icon="ud83dudd17"
            )
            
            feature_card(
                title="Customization", 
                description="Tailor WrenchAI to your needs with a wide range of configuration options.",
                icon="ud83dudcdd"
            )
    
    # Recent activity
    with section_container("Recent Activity"):
        # Check if we have any execution history
        execution_history = get_state(StateKey.EXECUTION_HISTORY, [])
        
        if execution_history:
            # Display recent executions
            st.subheader("Recent Playbook Executions")
            
            # Create a dataframe for recent executions
            recent_executions = []
            
            # Get playbook list for reference
            playbook_list = get_state(StateKey.PLAYBOOK_LIST, [])
            playbook_map = {playbook.get("id"): playbook for playbook in playbook_list}
            
            # Get the last 5 executions
            for execution in reversed(execution_history[:5]):
                playbook_id = execution.get("playbook_id")
                playbook = playbook_map.get(playbook_id, {})
                
                recent_executions.append({
                    "Playbook": playbook.get("name", "Unknown Playbook"),
                    "Status": execution.get("status", "Unknown"),
                    "Time": execution.get("timestamp", "Unknown"),
                    "Duration": execution.get("duration", "N/A")
                })
            
            # Display as a dataframe
            st.dataframe(recent_executions, use_container_width=True)
            
            # Link to view all executions
            st.markdown("[View all playbook executions](/)")
        else:
            st.info("No recent activity. Start by running a playbook or generating a portfolio!")

def main_content():
    """Render the page content based on the current page selection."""
    # Include additional page-specific content here if needed
    # The main page rendering is handled by the st.navigation system
    pass

def initialize_client():
    """Initialize the API client."""
    # Get API configuration from session state
    config = get_state(StateKey.CONFIG)
    api_config = config.api if hasattr(config, "api") else {}
    
    # Initialize API client (placeholder)
    client = {
        "api_url": api_config.get("url", "https://api.example.com"),
        "version": api_config.get("version", "v1"),
        "initialized": True
    }
    
    # Ensure API connection
    ensure_api_connection(client)
    
    return client

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
            
        # Render the home page content if on the main page
        if st._is_running_with_streamlit and pg.current.title == "Home":
            render_home_page()
            
        # Render sidebar navigation with additional options
        sidebar_navigation()
        
    except Exception as e:
        logger.exception("Application error")
        st.error(f"Application error: {str(e)}")
        st.stop()

# Run the main function
if __name__ == "__main__":
    main()
    # Run the navigation system
    pg.run()