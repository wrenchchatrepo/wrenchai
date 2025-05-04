"""Reusable UI Components for WrenchAI Streamlit application.

This module provides a collection of reusable UI components for the WrenchAI Streamlit interface.
These components are designed with the Midnight UI theme in mind, providing a consistent
visual experience throughout the application.
"""

import streamlit as st
from typing import Dict, List, Any, Optional, Callable, Union
import json
import pandas as pd
from datetime import datetime
import time

from streamlit_app.components.midnight_theme import highlight_card, status_indicator


# Information Display Components

def code_block(code: str, language: str = "python", show_copy_button: bool = True):
    """Display a syntax-highlighted code block with optional copy button.
    
    Args:
        code: The code to display
        language: Programming language for syntax highlighting
        show_copy_button: Whether to show a copy button
    """
    if show_copy_button:
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.code(code, language=language)
        with col2:
            if st.button("📋", key=f"copy_{hash(code)}"):
                st.session_state[f"copied_{hash(code)}"] = True
        if st.session_state.get(f"copied_{hash(code)}", False):
            st.success("Copied to clipboard!")
            # Reset after 2 seconds
            time.sleep(0.5)
            st.session_state[f"copied_{hash(code)}"] = False
            st.rerun()
    else:
        st.code(code, language=language)


def json_viewer(data: Dict, expanded: bool = False, title: str = None):
    """Display JSON data in a collapsible, syntax-highlighted viewer.
    
    Args:
        data: Dictionary to display as JSON
        expanded: Whether the viewer should be expanded by default
        title: Optional title for the viewer
    """
    # Format the JSON with indentation
    formatted_json = json.dumps(data, indent=2, default=str)
    
    # Create an expander with optional title
    expander_title = title or "JSON Data"
    with st.expander(expander_title, expanded=expanded):
        code_block(formatted_json, language="json")


def data_table(data: Union[Dict, List, pd.DataFrame], use_container_width: bool = True):
    """Display data in a styled table with sorting and filtering capabilities.
    
    Args:
        data: Dictionary, list, or DataFrame to display
        use_container_width: Whether the table should expand to container width
    """
    # Convert dict or list to DataFrame if needed
    if isinstance(data, dict):
        if all(isinstance(v, (list, dict)) for v in data.values()):
            # Nested dict, convert to dataframe using json_normalize
            df = pd.json_normalize(data)
        else:
            # Simple key-value dict
            df = pd.DataFrame(list(data.items()), columns=['Key', 'Value'])
    elif isinstance(data, list):
        if all(isinstance(item, dict) for item in data):
            # List of dicts
            df = pd.DataFrame(data)
        else:
            # Simple list
            df = pd.DataFrame(data, columns=['Value'])
    else:
        # Already a DataFrame
        df = data
    
    # Display the table with styling
    st.dataframe(
        df,
        use_container_width=use_container_width,
        hide_index=isinstance(data, (list, dict)) and not isinstance(data, pd.DataFrame)
    )


def info_card(title: str, content: str, icon: str = "ℹ️"):
    """Display an information card with a title and content.
    
    Args:
        title: Card title
        content: Card content text/markdown
        icon: Emoji icon to display
    """
    highlight_card(title, content, icon=icon, border_color="#00CCFF")


def warning_card(title: str, content: str, icon: str = "⚠️"):
    """Display a warning card with a title and content.
    
    Args:
        title: Card title
        content: Card content text/markdown
        icon: Emoji icon to display
    """
    highlight_card(title, content, icon=icon, border_color="#FFD600")


def error_card(title: str, content: str, icon: str = "❌"):
    """Display an error card with a title and content.
    
    Args:
        title: Card title
        content: Card content text/markdown
        icon: Emoji icon to display
    """
    highlight_card(title, content, icon=icon, border_color="#FF453A")


def success_card(title: str, content: str, icon: str = "✅"):
    """Display a success card with a title and content.
    
    Args:
        title: Card title
        content: Card content text/markdown
        icon: Emoji icon to display
    """
    highlight_card(title, content, icon=icon, border_color="#00FF9D")


# Interactive Components

def searchable_selectbox(label: str, options: List[str], key: str = None):
    """Display a selectbox with a search input for filtering options.
    
    Args:
        label: Input label
        options: List of options to choose from
        key: Session state key for the component
    
    Returns:
        Selected option
    """
    # Generate a unique key if none provided
    search_key = f"{key}_search" if key else f"search_{hash(str(options))}"
    select_key = key or f"select_{hash(str(options))}"
    
    # Initialize search term in session state if not present
    if search_key not in st.session_state:
        st.session_state[search_key] = ""
    
    # Search input
    search_term = st.text_input(
        f"Search {label}",
        value=st.session_state[search_key],
        key=search_key
    )
    
    # Filter options based on search term
    filtered_options = [opt for opt in options if search_term.lower() in opt.lower()]
    
    # Show number of matches
    if search_term:
        st.caption(f"Found {len(filtered_options)} match(es) out of {len(options)}")
    
    # Select from filtered options
    if filtered_options:
        selected = st.selectbox(label, filtered_options, key=select_key)
    else:
        st.info("No matches found. Try a different search term.")
        selected = None
    
    return selected


def toggle_button(label: str, key: str, default: bool = False):
    """Display a button that toggles between two states.
    
    Args:
        label: Button label
        key: Session state key for the button state
        default: Default state (True/False)
    
    Returns:
        Current state of the toggle (True/False)
    """
    # Initialize state if not present
    if key not in st.session_state:
        st.session_state[key] = default
    
    # Determine button style based on state
    if st.session_state[key]:
        button_text = f"{label} ✓"
        button_type = "primary"
    else:
        button_text = label
        button_type = "secondary"
    
    # Create the button with conditional styling
    if st.button(button_text, key=f"{key}_btn", type=button_type):
        # Toggle state when clicked
        st.session_state[key] = not st.session_state[key]
        st.rerun()
    
    return st.session_state[key]


def collapsible_container(header: str, content_function: Callable, default_expanded: bool = False, key: str = None):
    """Create a collapsible container with custom styling.
    
    Args:
        header: Header text for the collapsible container
        content_function: Function that renders the container's content when called
        default_expanded: Whether the container is expanded by default
        key: Session state key for the component
    """
    # Generate unique key if none provided
    container_key = key or f"container_{hash(header)}"
    
    # Create the expander
    with st.expander(header, expanded=default_expanded):
        # Call the content function to render its contents
        content_function()


# Monitoring Components

def progress_tracker(steps: List[str], current_step: int, key: str = "progress_tracker"):
    """Display a horizontal progress tracker for multi-step processes.
    
    Args:
        steps: List of step names/descriptions
        current_step: Index of the current step (0-based)
        key: Session state key for the component
    """
    st.markdown("""
    <style>
    .step-tracker {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 0;
        position: relative;
    }
    .step-tracker:before {
        content: '';
        position: absolute;
        top: 50%;
        left: 0;
        right: 0;
        height: 2px;
        background-color: #2A2A2A;
        z-index: 1;
    }
    .step {
        width: 30px;
        height: 30px;
        border-radius: 50%;
        background-color: #1E1E1E;
        border: 2px solid #2A2A2A;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        z-index: 2;
    }
    .step-completed {
        background-color: #00CCFF;
        border-color: #00CCFF;
        color: #121212;
    }
    .step-current {
        background-color: #1E1E1E;
        border-color: #00CCFF;
        color: #00CCFF;
    }
    .step-text {
        position: absolute;
        top: 35px;
        font-size: 0.8em;
        white-space: nowrap;
        text-align: center;
        width: 100px;
        left: -35px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Generate HTML for progress tracker
    steps_html = """
    <div class="step-tracker">
    """
    
    for i, step_text in enumerate(steps):
        if i < current_step:
            step_class = "step step-completed"
            step_content = "✓"
        elif i == current_step:
            step_class = "step step-current"
            step_content = str(i + 1)
        else:
            step_class = "step"
            step_content = str(i + 1)
        
        steps_html += f"""
        <div class="{step_class}">{step_content}
            <div class="step-text">{step_text}</div>
        </div>
        """
    
    steps_html += """
    </div>
    """
    
    st.markdown(steps_html, unsafe_allow_html=True)
    
    # Progress bar
    progress_percentage = current_step / (len(steps) - 1) if len(steps) > 1 else 0
    st.progress(min(1.0, progress_percentage))


def loading_spinner(content_function: Callable, text: str = "Loading..."):
    """Display content with a loading spinner while content loads.
    
    Args:
        content_function: Function that renders content and may take time to load
        text: Loading text to display
    """
    with st.spinner(text):
        content_function()


def real_time_status(status_function: Callable, update_interval: float = 1.0, max_updates: int = 10):
    """Display real-time status updates that refresh at specified intervals.
    
    Args:
        status_function: Function that returns current status data
        update_interval: Time between updates in seconds
        max_updates: Maximum number of updates before stopping auto-refresh
    """
    # Create a placeholder for the status
    status_placeholder = st.empty()
    
    # Generate a unique key for this component
    status_key = f"status_{hash(status_function)}"
    
    # Initialize or increment update counter
    if f"{status_key}_count" not in st.session_state:
        st.session_state[f"{status_key}_count"] = 0
    else:
        st.session_state[f"{status_key}_count"] += 1
    
    # Auto-refresh button
    auto_refresh = toggle_button(
        "Auto-refresh", 
        key=f"{status_key}_refresh", 
        default=True
    )
    
    # Show current status
    with status_placeholder.container():
        # Get latest status
        status_data = status_function()
        
        # Display timestamp
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
        
        # Display the status data
        if isinstance(status_data, dict):
            for key, value in status_data.items():
                st.text(f"{key}: {value}")
        else:
            st.write(status_data)
    
    # Handle auto-refresh
    if auto_refresh and st.session_state[f"{status_key}_count"] < max_updates:
        time.sleep(update_interval)
        st.rerun()
    
    # Reset counter if refresh is turned off
    if not auto_refresh:
        st.session_state[f"{status_key}_count"] = 0


# Form Components

def validated_text_input(label: str, key: str, validator: Callable = None, error_message: str = "Invalid input", **kwargs):
    """Text input with validation feedback.
    
    Args:
        label: Input label
        key: Session state key for the input
        validator: Function that takes input and returns True if valid
        error_message: Message to display if validation fails
        **kwargs: Additional arguments for st.text_input
    
    Returns:
        Input value and validity as a tuple
    """
    # Track validation state
    validation_key = f"{key}_valid"
    if validation_key not in st.session_state:
        st.session_state[validation_key] = True
    
    # Display the text input
    input_value = st.text_input(label, key=key, **kwargs)
    
    # Validate if we have input and a validator
    is_valid = True
    if input_value and validator:
        is_valid = validator(input_value)
        st.session_state[validation_key] = is_valid
    
    # Show error message if invalid
    if not st.session_state[validation_key]:
        st.error(error_message)
    
    return input_value, st.session_state[validation_key]


def file_upload_area(allowed_types: List[str] = None, max_size_mb: int = 50, multiple: bool = False):
    """File upload area with type restrictions and size validation.
    
    Args:
        allowed_types: List of allowed file extensions (e.g., ['pdf', 'docx'])
        max_size_mb: Maximum file size in MB
        multiple: Whether to allow multiple file upload
    
    Returns:
        Uploaded file(s) if valid, None otherwise
    """
    # Prepare the accepted file types string
    accept_string = None
    if allowed_types:
        accept_string = ",".join([f".{t}" if not t.startswith(".") else t for t in allowed_types])
    
    # Display allowed file types and max size
    if allowed_types:
        file_types_str = ", ".join(allowed_types)
        st.caption(f"Allowed file types: {file_types_str}")
    st.caption(f"Maximum file size: {max_size_mb} MB")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose file(s)",
        type=allowed_types,
        accept_multiple_files=multiple
    )
    
    # Check if we got files
    if not uploaded_files:
        return None
    
    # Convert to list if single file
    files_list = uploaded_files if multiple else [uploaded_files]
    
    # Validate each file
    valid_files = []
    for file in files_list:
        # Check file size
        if file.size > max_size_mb * 1024 * 1024:
            st.error(f"File '{file.name}' exceeds the {max_size_mb} MB size limit")
            continue
            
        valid_files.append(file)
    
    if not valid_files:
        return None
        
    return valid_files if multiple else valid_files[0]


# Error Handling Components

def error_boundary(content_function: Callable, fallback: Callable = None):
    """Error boundary that catches exceptions and displays a fallback UI.
    
    Args:
        content_function: Function that renders content that might error
        fallback: Optional function that renders fallback UI when an error occurs
    """
    try:
        return content_function()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        
        if fallback:
            st.markdown("---")
            st.write("Displaying fallback content:")
            return fallback()
        
        # Default fallback
        error_card(
            "Error",
            f"An error occurred while rendering this component: {str(e)}"
        )
        return None


def exception_alert(exception: Exception, show_traceback: bool = False):
    """Display a detailed exception alert with optional traceback.
    
    Args:
        exception: The exception to display
        show_traceback: Whether to show the full traceback
    """
    import traceback
    
    # Display the error card with exception message
    error_card(
        f"Exception: {type(exception).__name__}",
        str(exception)
    )
    
    # Show traceback if requested
    if show_traceback:
        with st.expander("Show traceback"):
            st.code(traceback.format_exc(), language="python")