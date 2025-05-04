"""Playbook execution page for WrenchAI application."""

import streamlit as st
from typing import Dict, List, Any, Optional
import time
import random

# Import utility functions
from wrenchai.streamlit_app.utils.session_state import StateKey, get_state, set_state
from wrenchai.streamlit_app.utils.logger import get_logger
from wrenchai.streamlit_app.utils.ui_components import status_indicator, display_error, display_success
from wrenchai.streamlit_app.components import (
    section_container,
    execution_results_display,
    execution_logs_display,
    form_field
)

# Setup logger
logger = get_logger(__name__)

st.set_page_config(
    page_title="WrenchAI - Playbook Execution",
    page_icon="ud83dudd27",
    layout="wide",
)

def main():
    """Main entry point for the playbook execution page."""
    st.title("ud83dudcc3 Playbook Execution")
    
    # Get selected playbook ID
    playbook_id = get_state(StateKey.SELECTED_PLAYBOOK)
    
    if not playbook_id:
        st.warning("No playbook selected. Please select a playbook from the Playbooks page.")
        if st.button("Go to Playbooks"): 
            st.switch_page("wrenchai/streamlit_app/pages/playbooks.py")
        st.stop()
    
    # Find playbook details
    playbook_list = get_state(StateKey.PLAYBOOK_LIST, [])
    playbook = next((p for p in playbook_list if p.get("id") == playbook_id), None)
    
    if not playbook:
        st.error(f"Playbook with ID '{playbook_id}' not found.")
        if st.button("Back to Playbooks"):
            st.switch_page("wrenchai/streamlit_app/pages/playbooks.py")
        st.stop()
    
    # Display playbook details
    render_playbook_details(playbook)
    
    # Create columns for form and execution/results
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Render parameter form
        render_parameter_form(playbook)
    
    with col2:
        # Render execution status and results
        render_execution_status(playbook)

def render_playbook_details(playbook: Dict[str, Any]):
    """Render playbook details.
    
    Args:
        playbook: The playbook dictionary
    """
    with section_container("Playbook Details"):
        # Create columns for details and actions
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Display playbook name and description
            st.subheader(playbook.get("name", "Unnamed Playbook"))
            st.markdown(playbook.get("description", "No description available"))
            
            # Display additional metadata
            st.caption(f"Category: {playbook.get('category', 'general')} | ID: {playbook.get('id')}")
        
        with col2:
            # Actions
            if st.button("Back to Playbooks"):
                # Clear selected playbook and go back
                set_state(StateKey.SELECTED_PLAYBOOK, None)
                st.switch_page("wrenchai/streamlit_app/pages/playbooks.py")
            
            # Favorite button (toggle)
            favorite = playbook.get("favorite", False)
            favorite_label = "ud83dudda4 Remove Favorite" if favorite else "ud83cudf1f Add Favorite"
            if st.button(favorite_label):
                # Toggle favorite status
                playbook["favorite"] = not favorite
                # Update playbook in list
                playbook_list = get_state(StateKey.PLAYBOOK_LIST, [])
                for i, p in enumerate(playbook_list):
                    if p.get("id") == playbook.get("id"):
                        playbook_list[i] = playbook
                        break
                set_state(StateKey.PLAYBOOK_LIST, playbook_list)
                st.rerun()

def render_parameter_form(playbook: Dict[str, Any]):
    """Render parameter form for playbook execution.
    
    Args:
        playbook: The playbook dictionary
    """
    with section_container("Parameters"):
        # Get playbook parameters
        parameters = playbook.get("parameters", [])
        
        if not parameters:
            st.info("This playbook does not require any parameters.")
        else:
            st.write("Configure the parameters for this playbook:")
        
        # Get stored parameters
        stored_params = get_state(StateKey.PLAYBOOK_PARAMS, {}).get(playbook.get("id"), {})
        
        # Create form for parameters
        with st.form("playbook_parameters_form"):
            # Create fields for each parameter
            param_values = {}
            
            for param in parameters:
                param_name = param.get("name", "")
                param_type = param.get("type", "string")
                param_description = param.get("description", "")
                param_required = param.get("required", False)
                param_default = param.get("default", None)
                
                # Get stored value or default
                stored_value = stored_params.get(param_name, param_default)
                
                # Render appropriate field based on parameter type
                if param_type == "string":
                    param_values[param_name] = st.text_input(
                        f"{param_name}{'*' if param_required else ''}",
                        value=stored_value or "",
                        help=param_description
                    )
                elif param_type == "number":
                    param_values[param_name] = st.number_input(
                        f"{param_name}{'*' if param_required else ''}",
                        value=float(stored_value) if stored_value is not None else 0.0,
                        help=param_description
                    )
                elif param_type == "boolean":
                    param_values[param_name] = st.checkbox(
                        f"{param_name}{'*' if param_required else ''}",
                        value=bool(stored_value) if stored_value is not None else False,
                        help=param_description
                    )
                elif param_type == "select":
                    options = param.get("options", [])
                    param_values[param_name] = st.selectbox(
                        f"{param_name}{'*' if param_required else ''}",
                        options=options,
                        index=options.index(stored_value) if stored_value in options else 0,
                        help=param_description
                    )
                elif param_type == "multiselect":
                    options = param.get("options", [])
                    param_values[param_name] = st.multiselect(
                        f"{param_name}{'*' if param_required else ''}",
                        options=options,
                        default=stored_value or [],
                        help=param_description
                    )
                elif param_type == "file":
                    # For file upload (simplified for demo)
                    uploaded_file = st.file_uploader(
                        f"{param_name}{'*' if param_required else ''}",
                        help=param_description
                    )
                    if uploaded_file is not None:
                        param_values[param_name] = uploaded_file.name
                    else:
                        param_values[param_name] = stored_value
            
            # Execute button
            execute_button = st.form_submit_button(
                "Execute Playbook", 
                type="primary",
                use_container_width=True
            )
        
        # Handle form submission
        if execute_button:
            # Check if all required parameters are provided
            missing_params = []
            for param in parameters:
                if param.get("required", False) and not param_values.get(param.get("name"), ""):
                    missing_params.append(param.get("name"))
            
            if missing_params:
                st.error(f"Missing required parameters: {', '.join(missing_params)}")
            else:
                # Store parameters
                all_params = get_state(StateKey.PLAYBOOK_PARAMS, {})
                all_params[playbook.get("id")] = param_values
                set_state(StateKey.PLAYBOOK_PARAMS, all_params)
                
                # Start execution
                start_execution(playbook, param_values)
                
                # Force rerun to update UI
                st.rerun()

def render_execution_status(playbook: Dict[str, Any]):
    """Render execution status and results.
    
    Args:
        playbook: The playbook dictionary
    """
    with section_container("Execution"):
        # Get execution state
        execution_state = get_state(StateKey.EXECUTION_STATE, {})
        execution_id = execution_state.get("execution_id")
        status = execution_state.get("status")
        
        if not execution_id or status not in ["running", "completed", "failed"]:
            st.info("Configure parameters and click 'Execute Playbook' to start execution.")
            return
        
        # Display execution info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Execution ID", execution_id)
        with col2:
            st.metric("Status", status.capitalize())
        with col3:
            st.metric("Progress", f"{execution_state.get('progress', 0):.0f}%")
        
        # Progress bar
        st.progress(execution_state.get("progress", 0) / 100)
        
        # If running, show cancel button
        if status == "running":
            if st.button("Cancel Execution", type="secondary"):
                cancel_execution()
                st.rerun()
        
        # Display logs in expandable section
        with st.expander("Execution Logs", expanded=True):
            logs = execution_state.get("logs", [])
            if logs:
                execution_logs_display(logs)
            else:
                st.write("No logs available yet.")
        
        # If completed or failed, show results
        if status in ["completed", "failed"]:
            with st.expander("Execution Results", expanded=True):
                results = get_state(StateKey.EXECUTION_RESULTS, {})
                if results:
                    execution_results_display(results)
                else:
                    st.write("No results available.")

def start_execution(playbook: Dict[str, Any], parameters: Dict[str, Any]):
    """Start playbook execution.
    
    Args:
        playbook: The playbook dictionary
        parameters: The parameter values for execution
    """
    # Generate execution ID
    execution_id = f"exec-{random.randint(1000, 9999)}-{int(time.time())}"
    
    # Initialize execution state
    execution_state = {
        "execution_id": execution_id,
        "playbook_id": playbook.get("id"),
        "playbook_name": playbook.get("name"),
        "status": "running",
        "progress": 0,
        "start_time": time.time(),
        "parameters": parameters,
        "logs": [
            {"timestamp": time.time(), "level": "info", "message": f"Starting execution of '{playbook.get('name')}' playbook"}
        ]
    }
    
    # Store execution state
    set_state(StateKey.EXECUTION_STATE, execution_state)
    
    # Clear previous results
    set_state(StateKey.EXECUTION_RESULTS, {})
    
    # Schedule background execution (simulated for demo)
    # In a real app, this would call an API or run a background task
    logger.info(f"Starting execution of '{playbook.get('name')}' playbook with ID {execution_id}")
    
    # Update execution history
    update_execution_history(execution_id, playbook.get("id"), "running")

def cancel_execution():
    """Cancel current playbook execution."""
    # Get current execution state
    execution_state = get_state(StateKey.EXECUTION_STATE, {})
    
    if execution_state.get("status") == "running":
        # Update execution state
        execution_state["status"] = "cancelled"
        execution_state["end_time"] = time.time()
        execution_state["logs"].append(
            {"timestamp": time.time(), "level": "warning", "message": "Execution cancelled by user"}
        )
        
        # Store updated state
        set_state(StateKey.EXECUTION_STATE, execution_state)
        
        # Update execution history
        update_execution_history(execution_state.get("execution_id"), execution_state.get("playbook_id"), "cancelled")
        
        logger.info(f"Cancelled execution of playbook with ID {execution_state.get('playbook_id')}")

def update_execution_history(execution_id: str, playbook_id: str, status: str):
    """Update execution history with latest execution.
    
    Args:
        execution_id: The execution ID
        playbook_id: The playbook ID
        status: The execution status
    """
    # Get current history
    history = get_state(StateKey.EXECUTION_HISTORY, [])
    
    # Check if execution already in history
    for i, entry in enumerate(history):
        if entry.get("execution_id") == execution_id:
            # Update existing entry
            history[i]["status"] = status
            history[i]["timestamp"] = time.time()
            set_state(StateKey.EXECUTION_HISTORY, history)
            return
    
    # Add new entry
    history.insert(0, {
        "execution_id": execution_id,
        "playbook_id": playbook_id,
        "status": status,
        "timestamp": time.time()
    })
    
    # Limit history size
    if len(history) > 50:
        history = history[:50]
    
    # Store updated history
    set_state(StateKey.EXECUTION_HISTORY, history)

def simulate_execution_progress():
    """Simulate execution progress for demo purposes."""
    # Get current execution state
    execution_state = get_state(StateKey.EXECUTION_STATE, {})
    
    # Check if execution is running
    if execution_state.get("status") != "running":
        return
    
    # Update progress
    current_progress = execution_state.get("progress", 0)
    new_progress = min(current_progress + random.randint(5, 15), 100)
    execution_state["progress"] = new_progress
    
    # Add log entry
    log_message = f"Execution progress: {new_progress}%"
    execution_state["logs"].append(
        {"timestamp": time.time(), "level": "info", "message": log_message}
    )
    
    # If reached 100%, complete execution
    if new_progress >= 100:
        # Set status to completed
        execution_state["status"] = "completed"
        execution_state["end_time"] = time.time()
        execution_state["logs"].append(
            {"timestamp": time.time(), "level": "success", "message": "Execution completed successfully"}
        )
        
        # Generate sample results
        results = {
            "execution_id": execution_state.get("execution_id"),
            "playbook_id": execution_state.get("playbook_id"),
            "status": "completed",
            "duration": time.time() - execution_state.get("start_time", time.time()),
            "output": {
                "summary": "Playbook executed successfully",
                "artifacts": [
                    {"name": "output.txt", "type": "file", "size": "1.2 KB"},
                    {"name": "report.pdf", "type": "file", "size": "245 KB"}
                ],
                "stats": {
                    "files_processed": random.randint(5, 20),
                    "actions_performed": random.randint(10, 50),
                    "warnings": random.randint(0, 3)
                }
            }
        }
        
        # Store results
        set_state(StateKey.EXECUTION_RESULTS, results)
        
        # Update execution history
        update_execution_history(execution_state.get("execution_id"), execution_state.get("playbook_id"), "completed")
    
    # Store updated state
    set_state(StateKey.EXECUTION_STATE, execution_state)

if __name__ == "__main__":
    # Simulate execution progress if an execution is running
    # This simulates the background task updating the execution state
    execution_state = get_state(StateKey.EXECUTION_STATE, {})
    if execution_state.get("status") == "running":
        simulate_execution_progress()
    
    # Render main content
    main()