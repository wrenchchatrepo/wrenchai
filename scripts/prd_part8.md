### 6.2 Main App Entry Point

```python
"""
Wrench AI Toolbox Main App

This is the main entry point for the Wrench AI Toolbox Streamlit application.
It provides an overview of the system and guides users to the various features.
"""

import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import custom modules
from streamlit_app.utils.config import load_config
from streamlit_app.utils.session import initialize_session
from streamlit_app.utils.theme import apply_midnight_theme
from streamlit_app.components.tooltips import show_tooltip
from streamlit_app.components.ai_assistant import initialize_assistant, render_assistant

def main():
    # Apply custom theme
    apply_midnight_theme()
    
    # Page configuration
    st.set_page_config(
        page_title="Wrench AI Toolbox",
        page_icon="🔧",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/yourusername/wrenchai',
            'Report a bug': 'https://github.com/yourusername/wrenchai/issues',
            'About': "# Wrench AI Toolbox\nPowered by WrenchAI Framework"
        }
    )
    
    # Initialize session and configuration
    config = load_config()
    initialize_session(config)
    
    # Initialize AI assistant
    assistant = initialize_assistant(api_key=os.getenv("OPENAI_API_KEY"))
    render_assistant()
    
    # Sidebar
    with st.sidebar:
        st.title("🔧 Wrench AI")
        st.markdown("---")
        
        # Navigation
        st.subheader("Navigation")
        st.page_link("app.py", label="🏠 Home", icon="house")
        st.page_link("pages/01_chat.py", label="💬 Chat with Agents", icon="chat")
        st.page_link("pages/02_playbooks.py", label="📚 Playbooks", icon="book")
        st.page_link("pages/03_agents.py", label="🤖 Agents", icon="robot")
        st.page_link("pages/04_tools.py", label="🛠️ Tools", icon="tools")
        st.page_link("pages/05_metrics.py", label="📊 Metrics", icon="bar-chart")
        
        # Settings
        st.markdown("---")
        st.subheader("Settings")
        
        # API Configuration
        api_url = st.text_input(
            "API URL",
            value=st.session_state.get("api_url", "http://localhost:8000"),
            help="URL of the WrenchAI API server"
        )
        if api_url != st.session_state.get("api_url"):
            st.session_state.api_url = api_url
            st.rerun()
            
        # Developer Mode toggle
        if st.toggle("Developer Mode", value=st.session_state.get("developer_mode", False)):
            st.session_state.developer_mode = True
        else:
            st.session_state.developer_mode = False
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🔧 Wrench AI Toolbox")
        st.subheader("Intelligent Automation with AI Agents")
    with col2:
        if st.button("Start Interactive Tour", key="start_tour", 
                    use_container_width=True,
                    help="Take a guided tour of the Wrench AI Toolbox"):
            st.session_state.show_tour = True
    
    # Show interactive tour if requested
    if st.session_state.get("show_tour", False):
        show_interactive_tour()
        return
    
    # Main content
    st.markdown("""
    ## Welcome to Wrench AI
    
    Wrench AI is an intelligent automation platform powered by specialized AI agents that work together to solve complex problems.
    
    ### How It Works
    
    1. **Define Your Objective** - What do you want to achieve?
    2. **Select or Configure a Playbook** - Choose from pre-defined workflows or create your own
    3. **Execute and Monitor** - Watch as AI agents collaborate to accomplish your task
    4. **Review Results** - Examine the output and provide feedback
    
    ### Get Started
    
    Browse the sidebar to explore different features, or try one of these quick starts:
    """)
    
    # Quick start buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.image("https://via.placeholder.com/150", width=150)
            st.markdown("### Create a Portfolio")
            st.markdown("Build a professional portfolio website with Docusaurus")
            if st.button("Start Portfolio", key="start_portfolio", use_container_width=True):
                st.switch_page("pages/02_playbooks.py")
    
    with col2:
        with st.container(border=True):
            st.image("https://via.placeholder.com/150", width=150)
            st.markdown("### Chat with Agents")
            st.markdown("Have a conversation with AI agents to solve problems")
            if st.button("Start Chat", key="start_chat", use_container_width=True):
                st.switch_page("pages/01_chat.py")
    
    with col3:
        with st.container(border=True):
            st.image("https://via.placeholder.com/150", width=150)
            st.markdown("### Browse Playbooks")
            st.markdown("Explore available automation workflows")
            if st.button("Browse Playbooks", key="browse_playbooks", use_container_width=True):
                st.switch_page("pages/02_playbooks.py")
    
    # System status
    st.markdown("---")
    st.subheader("System Status")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        is_connected = st.session_state.get("api_connected", False)
        st.metric("API Status", "Online" if is_connected else "Offline", 
                 delta="Connected" if is_connected else "Disconnected",
                 delta_color="normal")
    with col2:
        agent_count = st.session_state.get("agent_count", 0)
        st.metric("Available Agents", agent_count)
    with col3:
        playbook_count = st.session_state.get("playbook_count", 0)
        st.metric("Available Playbooks", playbook_count)
    
    # Recent executions (if any)
    if st.session_state.get("recent_executions"):
        st.markdown("---")
        st.subheader("Recent Executions")
        
        for execution in st.session_state.recent_executions:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{execution['playbook_name']}**")
                    st.caption(f"ID: {execution['id']}")
                with col2:
                    st.write(f"Status: {execution['status']}")
                with col3:
                    if st.button("View", key=f"view_{execution['id']}"):
                        st.session_state.selected_execution = execution['id']
                        st.switch_page("pages/02_playbooks.py")
    
    # Footer
    st.markdown("---")
    st.caption("Wrench AI Toolbox v1.0.0 | Powered by WrenchAI Framework")
```