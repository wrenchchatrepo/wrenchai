"""
UI Components Module

This module contains reusable UI components for the WrenchAI Streamlit interface.
Components are implemented as functions that render specific UI elements.
"""

from typing import Dict, List, Optional, Any, Callable
import streamlit as st
from datetime import datetime

def render_chat_message(
    message: Dict[str, Any],
    is_user: bool = False
) -> None:
    """
    Render a chat message with appropriate styling.
    
    Args:
        message: Message data containing content and metadata
        is_user: Whether message is from user (True) or agent (False)
    """
    # Configure message container styling
    container_style = """
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
        max-width: 80%;
    """
    
    if is_user:
        container_style += """
            background-color: #E3F2FD;
            margin-left: auto;
        """
    else:
        container_style += """
            background-color: #F5F5F5;
            margin-right: auto;
        """
    
    with st.container():
        st.markdown(f'<div style="{container_style}">', unsafe_allow_html=True)
        
        # Render message content
        st.markdown(message["content"])
        
        # Show metadata in smaller text
        meta_style = "color: #666; font-size: 0.8em;"
        timestamp = datetime.fromtimestamp(message["timestamp"]).strftime("%H:%M")
        st.markdown(
            f'<p style="{meta_style}">{timestamp}</p>',
            unsafe_allow_html=True
        )
        
        st.markdown('</div>', unsafe_allow_html=True)

def render_agent_selector(
    agents: List[Dict[str, Any]],
    on_select: Callable[[str], None]
) -> None:
    """
    Render agent selection interface.
    
    Args:
        agents: List of available agents with metadata
        on_select: Callback function when agent is selected
    """
    st.sidebar.subheader("Available Agents")
    
    for agent in agents:
        col1, col2 = st.sidebar.columns([3, 1])
        
        with col1:
            st.markdown(f"**{agent['name']}**")
            st.markdown(agent["description"])
            
        with col2:
            if st.button("Select", key=f"select_{agent['id']}"):
                on_select(agent["id"])

def render_playbook_selector(
    playbooks: List[Dict[str, Any]],
    on_select: Callable[[str], None]
) -> None:
    """
    Render playbook selection interface.
    
    Args:
        playbooks: List of available playbooks
        on_select: Callback function when playbook is selected
    """
    st.sidebar.subheader("Available Playbooks")
    
    for playbook in playbooks:
        with st.sidebar.expander(playbook["name"]):
            st.markdown(playbook["description"])
            st.markdown("**Steps:**")
            for step in playbook["steps"]:
                st.markdown(f"- {step}")
                
            if st.button("Use Playbook", key=f"playbook_{playbook['id']}"):
                on_select(playbook["id"])

def render_chat_input(
    on_submit: Callable[[str, Optional[List[Dict[str, Any]]]], None]
) -> None:
    """
    Render chat input interface with file upload.
    
    Args:
        on_submit: Callback for when message is submitted
    """
    with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
            message = st.text_area(
                "Message",
                height=100,
                placeholder="Type your message here..."
            )
        
        with col2:
            files = st.file_uploader(
                "Attachments",
                accept_multiple_files=True,
                type=["txt", "pdf", "py", "json", "yaml"]
            )
            
            if st.button("Send", use_container_width=True):
                if message:
                    attachments = []
                    if files:
                        for file in files:
                            attachments.append({
                                "name": file.name,
                                "content": file.read().decode(),
                                "type": file.type
                            })
                    on_submit(message, attachments)
                    # Clear input
                    st.session_state.message = ""

def render_system_status(status: Dict[str, Any]) -> None:
    """
    Render system status information.
    
    Args:
        status: Dictionary containing system status data
    """
    with st.sidebar.expander("System Status"):
        # Overall health indicator
        health_color = "#00FF00" if status["healthy"] else "#FF0000"
        st.markdown(
            f'<p style="color: {health_color}">●</p>',
            unsafe_allow_html=True
        )
        
        # Component status
        for component, info in status["components"].items():
            st.markdown(f"**{component}**")
            status_color = "#00FF00" if info["status"] == "ok" else "#FF0000"
            st.markdown(
                f'<p style="color: {status_color}">{info["status"]}</p>',
                unsafe_allow_html=True
            )
            if info.get("message"):
                st.markdown(f"_{info['message']}_")

def render_error_message(message: str) -> None:
    """
    Render error message with appropriate styling.
    
    Args:
        message: Error message to display
    """
    st.error(message)

def render_success_message(message: str) -> None:
    """
    Render success message with appropriate styling.
    
    Args:
        message: Success message to display
    """
    st.success(message)

def render_loading_spinner(text: str = "Processing...") -> None:
    """
    Render loading spinner with message.
    
    Args:
        text: Message to show with spinner
    """
    with st.spinner(text):
        st.empty()

def render_settings_panel(
    config: Dict[str, Any],
    on_save: Callable[[Dict[str, Any]], None]
) -> None:
    """
    Render settings configuration panel.
    
    Args:
        config: Current configuration settings
        on_save: Callback when settings are saved
    """
    with st.sidebar.expander("Settings"):
        updated_config = config.copy()
        
        # API Settings
        st.subheader("API Settings")
        updated_config["api_url"] = st.text_input(
            "API URL",
            value=config["api_url"]
        )
        
        # UI Settings
        st.subheader("UI Settings")
        updated_config["theme"] = st.selectbox(
            "Theme",
            options=["light", "dark"],
            index=0 if config["theme"] == "light" else 1
        )
        
        # Feature Flags
        st.subheader("Features")
        for feature, enabled in config.get("features", {}).items():
            updated_config["features"][feature] = st.checkbox(
                feature.replace("_", " ").title(),
                value=enabled
            )
        
        if st.button("Save Settings"):
            on_save(updated_config)
            st.success("Settings saved successfully!") 