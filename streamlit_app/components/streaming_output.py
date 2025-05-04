"""Streaming Text Output Component.

This component provides a way to display streaming text output in the UI,
similar to a terminal window or console.
"""

import streamlit as st
from typing import List, Optional, Union, Callable
import time
import threading

def create_streaming_output(height: int = 300, key: str = "streaming_output"):
    """Creates a container for streaming text output.
    
    Args:
        height: Height of the output window in pixels
        key: Session state key for this component
    
    Returns:
        A callable function that can be used to update the output
    """
    # Initialize session state for this component
    if f"{key}_content" not in st.session_state:
        st.session_state[f"{key}_content"] = []
    
    # Create styled container for output
    st.markdown(f"""
    <div style="
        height: {height}px;
        overflow-y: auto;
        background-color: #1E1E1E;
        color: #F0F0F0;
        padding: 10px;
        font-family: 'OpenDyslexic Mono', monospace;
        border: 1px solid #2A2A2A;
        border-radius: 4px;
        margin-bottom: 10px;
    " id="{key}_container">
        <pre id="{key}_output" style="margin: 0; white-space: pre-wrap;">{"\n".join(st.session_state[f"{key}_content"])}</pre>
    </div>
    
    <script>
        // Auto-scroll to bottom
        const container = document.getElementById("{key}_container");
        container.scrollTop = container.scrollHeight;
    </script>
    """, unsafe_allow_html=True)
    
    # Define update function
    def update_output(text: str, append: bool = True):
        """Update the streaming output with new text.
        
        Args:
            text: Text to add to the output
            append: Whether to append to existing text (True) or replace it (False)
        """
        if append:
            st.session_state[f"{key}_content"].append(text)
        else:
            st.session_state[f"{key}_content"] = [text]
        
        # Limit the number of lines to prevent excessive memory usage
        max_lines = 1000
        if len(st.session_state[f"{key}_content"]) > max_lines:
            st.session_state[f"{key}_content"] = st.session_state[f"{key}_content"][-max_lines:]
        
        st.rerun()
    
    # Provide controls
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Clear", key=f"{key}_clear"):
            st.session_state[f"{key}_content"] = []
            st.rerun()
    
    return update_output


def simulate_streaming(update_func: Callable, texts: List[str], delay: float = 0.1):
    """Simulate streaming output for demonstration purposes.
    
    Args:
        update_func: The update function returned by create_streaming_output
        texts: List of text items to stream
        delay: Delay between updates in seconds
    """
    def stream_worker():
        for text in texts:
            update_func(text)
            time.sleep(delay)
    
    # Run in a separate thread to avoid blocking the UI
    thread = threading.Thread(target=stream_worker)
    thread.daemon = True
    thread.start()