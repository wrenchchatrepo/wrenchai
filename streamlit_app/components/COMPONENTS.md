# WrenchAI UI Components Documentation

This document provides an overview of the reusable UI components available in the WrenchAI Streamlit application. These components are designed to provide a consistent look and feel across the application, while making it easier to build complex UI layouts.

## Table of Contents

1. [Midnight Theme](#midnight-theme)
2. [Information Display Components](#information-display-components)
3. [Interactive Components](#interactive-components)
4. [Streaming Output](#streaming-output)
5. [File Upload](#file-upload)
6. [Log Viewer](#log-viewer)
7. [Progress Indicators](#progress-indicators)
8. [Data Visualization](#data-visualization)
9. [Form Components](#form-components)
10. [Configuration Components](#configuration-components)
11. [Playbook Components](#playbook-components)

## Installation

The components are part of the WrenchAI streamlit application. To use them, ensure you have the required dependencies installed:

```bash
pip install -r streamlit_app/requirements.txt
```

## Midnight Theme

The Midnight UI theme provides a dark-mode interface with neon accents, designed to be visually appealing and reduce eye strain.

### Components

- `apply_midnight_theme()`: Apply the theme to the Streamlit app
- `highlight_card(title, content, icon, border_color)`: Display a highlighted card with a title and content
- `neon_metric(label, value, delta, delta_color)`: Display a metric with neon styling
- `status_indicator(status, text)`: Display a status indicator with appropriate coloring

### Example

```python
from streamlit_app.components import apply_midnight_theme, highlight_card, neon_metric, status_indicator

# Apply the theme
apply_midnight_theme()

# Use a highlight card
highlight_card(
    "Welcome to WrenchAI", 
    "An intelligent toolbox for streamlining your development workflow.",
    icon="✨",
    border_color="#7B42F6"
)

# Display a metric
neon_metric("Active Agents", 3, delta=1)

# Show status
status_indicator("success", "API Connected")
```

## Information Display Components

Components for displaying information in a structured and visually appealing way.

### Components

- `code_block(code, language, show_copy_button)`: Display code with syntax highlighting
- `json_viewer(data, expanded, title)`: Display JSON data in a collapsible viewer
- `data_table(data, use_container_width)`: Display tabular data with styling
- `info_card(title, content, icon)`: Display information in a styled card
- `warning_card(title, content, icon)`: Display a warning message
- `error_card(title, content, icon)`: Display an error message
- `success_card(title, content, icon)`: Display a success message

### Example

```python
from streamlit_app.components import code_block, json_viewer, data_table, info_card

# Display code
code_block("def hello(): return 'world'", language="python", show_copy_button=True)

# Display JSON
json_viewer({"name": "WrenchAI", "version": "1.0.0"}, expanded=True, title="Config")

# Display tabular data
data_table(df)

# Display an info card
info_card("Information", "This is important information.")
```

## Interactive Components

Components that provide enhanced interactivity beyond standard Streamlit widgets.

### Components

- `searchable_selectbox(label, options, key)`: Selectbox with search functionality
- `toggle_button(label, key, default)`: Button that toggles between two states
- `collapsible_container(header, content_function, default_expanded, key)`: Collapsible container
- `error_boundary(content_function, fallback)`: Component that catches errors and shows fallback

### Example

```python
from streamlit_app.components import searchable_selectbox, toggle_button, collapsible_container

# Searchable selectbox
selected = searchable_selectbox("Select Agent", ["Agent1", "Agent2", "Agent3"])

# Toggle button
dark_mode = toggle_button("Dark Mode", "dark_mode", default=True)

# Collapsible container
def container_content():
    st.write("This content is inside the container")

collapsible_container("Click to expand", container_content, default_expanded=False)
```

## Streaming Output

Components for displaying streaming text output in the UI.

### Components

- `create_streaming_output(height, key)`: Create a container for streaming text output
- `simulate_streaming(update_func, texts, delay)`: Simulate streaming text for demos

### Example

```python
from streamlit_app.components import create_streaming_output, simulate_streaming

# Create streaming output
update_output = create_streaming_output(height=200, key="output")

# Update the output
update_output("Processing...")

# Add more text
update_output("Step 1: Loading data...", append=True)

# Simulate streaming for demo
simulate_streaming(update_output, [
    "Step 1: Loading data...",
    "Step 2: Processing...",
    "Step 3: Complete!"
], delay=0.5)
```

## File Upload

Components for file uploads with preview and management.

### Components

- `chat_file_uploader(allowed_types, max_size_mb, key)`: Enhanced file uploader
- `display_file_message(file_info)`: Display a file as a chat message

### Example

```python
from streamlit_app.components import chat_file_uploader, display_file_message

# File uploader
uploaded_files = chat_file_uploader(
    allowed_types=["txt", "py", "jpg", "png", "pdf"],
    max_size_mb=5
)

# Display files
if uploaded_files:
    for file in uploaded_files:
        display_file_message(file)
```

## Log Viewer

Components for viewing and filtering log files.

### Components

- `log_viewer(log_file_path, max_lines, auto_refresh, refresh_interval)`: Display a log file
- `multi_log_viewer(log_files)`: Display multiple log files with tabs

### Example

```python
from streamlit_app.components import log_viewer, multi_log_viewer

# Single log viewer
log_viewer("application.log", auto_refresh=True, refresh_interval=5)

# Multiple logs
log_files = {
    "Application": "app.log",
    "API": "api.log"
}
multi_log_viewer(log_files)
```

## Progress Indicators

Components for tracking and displaying progress.

### Components

- `progress_bar(progress, label, color, height, show_percentage, key)`: Customizable progress bar
- `task_progress(tasks, key)`: Display task progress with subtasks
- `animated_progress_bar(key, interval)`: Progress bar with animation

### Example

```python
from streamlit_app.components import progress_bar, task_progress, animated_progress_bar

# Simple progress bar
progress_bar(0.65, "Processing...")

# Task progress with subtasks
tasks = {
    "Task 1": {
        "progress": 0.8,
        "status": "running",
        "subtasks": {
            "Subtask 1.1": {"progress": 1.0, "status": "complete"},
            "Subtask 1.2": {"progress": 0.5, "status": "running"}
        }
    }
}
task_progress(tasks)

# Animated progress bar
update_progress = animated_progress_bar()
update_progress(increment=0.1)  # Increment progress
```

## Data Visualization

Components for creating data visualizations with consistent styling.

### Components

- `time_series_chart(data, x_column, y_columns, title, height, use_container_width)`: Time series line chart
- `bar_chart(data, x_column, y_column, color_column, horizontal, title, height, use_container_width)`: Bar chart
- `pie_chart(data, names_column, values_column, title, hole, height, use_container_width)`: Pie/donut chart
- `scatter_plot(data, x_column, y_column, color_column, size_column, title, height, use_container_width)`: Scatter plot
- `heatmap(data, x_column, y_column, value_column, title, height, color_scheme, use_container_width)`: Heatmap
- `metric_gauge(value, min_value, max_value, threshold_ranges, title, format_string, height, use_container_width)`: Gauge chart
- `correlation_matrix(data, columns, title, height, use_container_width)`: Correlation matrix heatmap

### Example

```python
from streamlit_app.components import time_series_chart, bar_chart, pie_chart, metric_gauge

# Time series chart
time_series_chart(
    df,
    x_column="date",
    y_columns=["value_1", "value_2"],
    title="Time Series"
)

# Bar chart
bar_chart(
    df,
    x_column="category",
    y_column="value",
    color_column="group"
)

# Pie chart
pie_chart(
    df,
    names_column="segment",
    values_column="value",
    title="Distribution",
    hole=0.4
)

# Gauge
metric_gauge(value=75, title="System Health")
```

## Form Components

Components for creating forms with validation, based on Pydantic models.

### Components

- `model_form(model_class, key)`: Create a form from a Pydantic model
- `dynamic_model_form(fields, title, model_name)`: Create a form from field definitions
- `custom_form(fields, key, on_submit)`: Create a custom form with various input types
- `FormBuilder`: Builder class for creating forms with a fluent API

### Example

```python
from pydantic import BaseModel, Field
from typing import Optional
from streamlit_app.components import model_form, dynamic_model_form, FormBuilder

# Pydantic model form
class UserConfig(BaseModel):
    name: str = Field(..., title="Name")
    email: str = Field(..., title="Email")
    active: bool = Field(True, title="Active")

user = model_form(UserConfig)

# Dynamic form
fields = {
    "api_key": {"type": str, "title": "API Key", "default": ""},
    "max_tokens": {"type": int, "title": "Max Tokens", "default": 1000}
}
config = dynamic_model_form(fields, title="API Configuration")

# Form builder
builder = FormBuilder(title="Settings")
builder.add_text("username", "Username", required=True)
builder.add_checkbox("notifications", "Enable Notifications")
data = builder.build()
```

## Configuration Components

Components for managing application configuration with Pydantic models.

### Components

- `ConfigManager`: Manager for configuration based on Pydantic models
- `configuration_editor(config_manager, title)`: Create a configuration editor UI
- `config_section(title, description, config_form_function)`: Create a collapsible configuration section
- `display_config_field(field_name, value, field_description)`: Display a configuration field
- `config_summary(config, title)`: Display a summary of the configuration

### Example

```python
from pydantic import BaseModel, Field
from streamlit_app.components import ConfigManager, configuration_editor, config_summary

# Define a configuration model
class AppConfig(BaseModel):
    api_url: str = Field("http://localhost:8000", title="API URL")
    debug: bool = Field(False, title="Debug Mode")

# Create a config manager
config_manager = ConfigManager(
    config_model=AppConfig,
    config_path="config.yaml",
    default_config={"api_url": "http://localhost:8000", "debug": False}
)

# Create a configuration editor
updated_config = configuration_editor(config_manager, title="Application Settings")

# Display config summary
config_summary(config_manager.get_config())
```

## Playbook Components

Components for managing and executing playbooks.

### Components

- `PlaybookManager`: Manager for playbook configurations based on Pydantic models
- `playbook_browser(playbook_manager, on_select)`: Create a UI for browsing playbooks
- `playbook_details(playbook)`: Display playbook details
- `playbook_editor(playbook_manager, playbook, on_save)`: Create a UI for editing playbooks
- `playbook_execution_form(playbook, on_execute)`: Create a form for executing a playbook

### Example

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from streamlit_app.components import PlaybookManager, playbook_browser, playbook_editor

# Define a playbook model
class PlaybookModel(BaseModel):
    name: str = Field(..., title="Name")
    description: str = Field("", title="Description")
    steps: List[Dict[str, Any]] = Field([], title="Steps")

# Create a playbook manager
playbook_manager = PlaybookManager(
    playbook_model=PlaybookModel,
    playbooks_dir="playbooks/"
)

# Browse playbooks
selected_playbook = playbook_browser(playbook_manager)

# Edit a playbook
if selected_playbook:
    updated_playbook = playbook_editor(playbook_manager, selected_playbook)
```