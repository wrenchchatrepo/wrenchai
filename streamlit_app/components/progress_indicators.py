"""Progress Bar Component.

This component provides a customizable progress bar with percentage display.
"""

import streamlit as st
from typing import Optional, Tuple, Dict, Any
import time

def progress_bar(progress: float, 
               label: Optional[str] = None,
               color: str = "#00CCFF",
               height: int = 24,
               show_percentage: bool = True,
               key: Optional[str] = None):
    """Display a customized progress bar with percentage.
    
    Args:
        progress: Progress value between 0.0 and 1.0
        label: Text label to display above the progress bar
        color: Color of the progress bar (hex code)
        height: Height of the progress bar in pixels
        show_percentage: Whether to show the percentage text
        key: Unique key for this component
    """
    # Ensure progress is between 0 and 1
    progress = max(0.0, min(1.0, progress))
    
    # Calculate percentage for display
    percentage = int(progress * 100)
    
    # Generate a unique key if not provided
    if key is None:
        key = f"progress_{id(progress)}"
    
    # Display label if provided
    if label:
        st.markdown(f"<p style='margin-bottom: 4px;'>{label}</p>", unsafe_allow_html=True)
    
    # Create the progress bar HTML
    st.markdown(f"""
    <div style="
        width: 100%;
        background-color: #2A2A2A;
        border-radius: 4px;
        margin-bottom: 10px;
        position: relative;
    ">
        <div style="
            width: {percentage}%;
            height: {height}px;
            background-color: {color};
            border-radius: 4px;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: flex-end;
        ">
        </div>
        
        {f'<div style="position: absolute; top: 0; right: 8px; line-height: {height}px;">{percentage}%</div>' if show_percentage else ''}
    </div>
    """, unsafe_allow_html=True)
    
    return progress


def task_progress(tasks: Dict[str, Any], key: str = "task_progress"):
    """Display task progress with subtasks and progress bars.
    
    Args:
        tasks: Dictionary of tasks with structure:
            {
                "task_name": {
                    "progress": 0.5,  # Progress between 0.0 and 1.0
                    "status": "running",  # "pending", "running", "complete", "error" 
                    "subtasks": {  # Optional subtasks
                        "subtask_name": {
                            "progress": 0.7,
                            "status": "running"
                        }
                    }
                }
            }
        key: Unique key for this component
    """
    if not tasks:
        st.info("No tasks available")
        return
    
    # Calculate overall progress
    total_progress = sum(task.get("progress", 0.0) for task in tasks.values()) / len(tasks)
    
    # Display overall progress
    st.subheader("Overall Progress")
    progress_bar(total_progress, height=30, color="#7B42F6")
    
    # Display individual tasks
    st.subheader("Tasks")
    
    # Status color mapping
    status_colors = {
        "pending": "#2A2A2A",   # Dark gray
        "running": "#00CCFF",   # Cyan
        "complete": "#00FF9D",  # Green
        "error": "#FF453A"      # Red
    }
    
    # Display each task with its progress
    for task_name, task_data in tasks.items():
        # Create an expander for this task
        with st.expander(f"{task_name} - {int(task_data.get('progress', 0.0) * 100)}%", 
                         expanded=task_data.get("status") == "running"):
            # Task progress
            progress_bar(
                task_data.get("progress", 0.0),
                color=status_colors.get(task_data.get("status", "pending"), "#00CCFF")
            )
            
            # Status indicator
            status = task_data.get("status", "pending").title()
            st.markdown(f"""
            <div style="
                display: inline-block;
                padding: 4px 8px;
                background-color: {status_colors.get(task_data.get('status', 'pending'), '#2A2A2A')};
                color: #F0F0F0;
                border-radius: 4px;
                font-size: 0.8em;
                margin-top: 5px;
            ">
                {status}
            </div>
            """, unsafe_allow_html=True)
            
            # Subtasks if any
            subtasks = task_data.get("subtasks", {})
            if subtasks:
                st.markdown("**Subtasks:**")
                for subtask_name, subtask_data in subtasks.items():
                    # Subtask status and progress
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        progress_bar(
                            subtask_data.get("progress", 0.0),
                            label=subtask_name,
                            color=status_colors.get(subtask_data.get("status", "pending"), "#00CCFF"),
                            height=16
                        )
                    with col2:
                        subtask_status = subtask_data.get("status", "pending").title()
                        st.markdown(f"""
                        <div style="
                            display: inline-block;
                            padding: 2px 6px;
                            background-color: {status_colors.get(subtask_data.get('status', 'pending'), '#2A2A2A')};
                            color: #F0F0F0;
                            border-radius: 4px;
                            font-size: 0.7em;
                            margin-top: 20px;
                        ">
                            {subtask_status}
                        </div>
                        """, unsafe_allow_html=True)


def animated_progress_bar(key: str = "animated_progress", interval: float = 0.1):
    """Create an animated progress bar that updates automatically.
    
    Args:
        key: Session state key for this component
        interval: Update interval in seconds
    
    Returns:
        Function to update the progress value
    """
    # Initialize session state
    if f"{key}_progress" not in st.session_state:
        st.session_state[f"{key}_progress"] = 0.0
    
    if f"{key}_running" not in st.session_state:
        st.session_state[f"{key}_running"] = False
    
    # Display progress bar
    progress = st.session_state[f"{key}_progress"]
    progress_bar(progress)
    
    # Define update function
    def update_progress(value: Optional[float] = None, increment: Optional[float] = None, complete: bool = False):
        """Update the progress bar value.
        
        Args:
            value: New progress value (between 0.0 and 1.0)
            increment: Amount to increment current progress by
            complete: Whether to complete the progress (set to 1.0)
        """
        if complete:
            st.session_state[f"{key}_progress"] = 1.0
            st.session_state[f"{key}_running"] = False
        elif value is not None:
            st.session_state[f"{key}_progress"] = max(0.0, min(1.0, value))
        elif increment is not None:
            current = st.session_state[f"{key}_progress"]
            st.session_state[f"{key}_progress"] = max(0.0, min(1.0, current + increment))
        
        # Start animation if not at 100%
        if st.session_state[f"{key}_progress"] < 1.0:
            st.session_state[f"{key}_running"] = True
        else:
            st.session_state[f"{key}_running"] = False
            
        st.rerun()
    
    # Auto-increment logic for animation effect
    if st.session_state[f"{key}_running"]:
        time.sleep(interval)
        # Add small increment for animation effect when process is ongoing
        # This gives visual feedback that something is happening
        if st.session_state[f"{key}_progress"] < 0.95:  # Cap visual animation at 95%
            increment_amount = min(0.005, (1.0 - st.session_state[f"{key}_progress"]) / 20)
            st.session_state[f"{key}_progress"] += increment_amount
            st.rerun()
    
    return update_progress