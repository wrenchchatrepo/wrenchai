"""Log Viewer Component.

This component provides a way to view log files in the UI.
"""

import streamlit as st
from typing import List, Dict, Optional
import os
import re
import time
from datetime import datetime

def log_viewer(log_file_path: str, max_lines: int = 500, auto_refresh: bool = False, refresh_interval: int = 5):
    """Display a log file with filtering and refresh options.
    
    Args:
        log_file_path: Path to the log file
        max_lines: Maximum number of lines to display
        auto_refresh: Whether to automatically refresh the log
        refresh_interval: Seconds between automatic refreshes
    """
    # Check if file exists
    if not os.path.exists(log_file_path):
        st.error(f"Log file not found: {log_file_path}")
        return
    
    # Sidebar controls
    with st.expander("Log Controls", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Log level filter
            log_level = st.selectbox(
                "Log Level",
                ["All", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                index=0
            )
        
        with col2:
            # Search filter
            search_term = st.text_input("Search", value="")
        
        with col3:
            # Auto-refresh toggle
            auto_refresh = st.checkbox("Auto-refresh", value=auto_refresh)
            refresh_rate = st.slider("Refresh Interval (seconds)", 1, 60, refresh_interval)
    
    # Generate a key for this log viewer instance
    instance_key = f"log_viewer_{hash(log_file_path)}"
    
    # Last refresh time tracking
    if f"{instance_key}_last_refresh" not in st.session_state:
        st.session_state[f"{instance_key}_last_refresh"] = time.time()
    
    # Force refresh button
    refresh_col1, refresh_col2 = st.columns([1, 5])
    with refresh_col1:
        if st.button("Refresh Now"):
            st.session_state[f"{instance_key}_last_refresh"] = time.time()
    
    with refresh_col2:
        # Show last refresh time
        last_refresh = datetime.fromtimestamp(st.session_state[f"{instance_key}_last_refresh"])
        st.caption(f"Last refreshed: {last_refresh.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Read and filter log file
    try:
        with open(log_file_path, 'r') as f:
            # Read from the end of the file for large logs
            try:
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                # Read only the last part of the file for very large files
                if file_size > 1024 * 1024:  # If larger than 1MB
                    f.seek(max(-file_size, -1024 * 1024), os.SEEK_END)
                else:
                    f.seek(0)
                    
                # Skip partial line if we started in the middle
                if file_size > 1024 * 1024:
                    f.readline()
                    
                log_content = f.read()
            except Exception:
                # Fallback method if seeking doesn't work
                f.seek(0)
                log_content = f.read()
        
        # Split into lines
        log_lines = log_content.splitlines()
        
        # Limit to max lines from the end of the file
        log_lines = log_lines[-max_lines:] if len(log_lines) > max_lines else log_lines
        
        # Filter by log level if needed
        if log_level != "All":
            pattern = f"\\b{log_level}\\b"
            log_lines = [line for line in log_lines if re.search(pattern, line, re.IGNORECASE)]
        
        # Filter by search term if provided
        if search_term:
            log_lines = [line for line in log_lines if search_term.lower() in line.lower()]
        
        # Display the log with syntax highlighting
        if log_lines:
            # Add syntax highlighting for log levels
            highlighted_lines = []
            for line in log_lines:
                # Apply different colors to different log levels
                if "CRITICAL" in line or "ERROR" in line:
                    line = re.sub(r"\b(CRITICAL|ERROR)\b", r"<span style='color: #FF453A;'>\1</span>", line)
                elif "WARNING" in line:
                    line = re.sub(r"\bWARNING\b", r"<span style='color: #FFD600;'>\1</span>", line)
                elif "INFO" in line:
                    line = re.sub(r"\bINFO\b", r"<span style='color: #00CCFF;'>\1</span>", line)
                elif "DEBUG" in line:
                    line = re.sub(r"\bDEBUG\b", r"<span style='color: #BBBBBB;'>\1</span>", line)
                    
                highlighted_lines.append(line)
            
            # Join and display
            log_html = "\n".join([f"<div>{line}</div>" for line in highlighted_lines])
            st.markdown(f"""
            <div style="
                background-color: #1E1E1E;
                color: #F0F0F0;
                padding: 10px;
                font-family: 'OpenDyslexic Mono', monospace;
                border: 1px solid #2A2A2A;
                border-radius: 4px;
                height: 400px;
                overflow-y: auto;
                white-space: pre-wrap;
                word-wrap: break-word;
            ">
                {log_html}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No matching log entries found.")
    except Exception as e:
        st.error(f"Error reading log file: {str(e)}")
    
    # Auto-refresh logic
    if auto_refresh:
        time_since_refresh = time.time() - st.session_state[f"{instance_key}_last_refresh"]
        if time_since_refresh >= refresh_rate:
            st.session_state[f"{instance_key}_last_refresh"] = time.time()
            time.sleep(0.1)  # Small delay to prevent UI issues
            st.rerun()


def multi_log_viewer(log_files: Dict[str, str]):
    """Display multiple log files with a tab interface.
    
    Args:
        log_files: Dictionary mapping log names to file paths
    """
    if not log_files:
        st.warning("No log files specified.")
        return
    
    # Create tabs for each log file
    tabs = st.tabs(list(log_files.keys()))
    
    # Display each log in its own tab
    for i, (name, path) in enumerate(log_files.items()):
        with tabs[i]:
            log_viewer(path)