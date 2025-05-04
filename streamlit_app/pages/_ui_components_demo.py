"""Test page for demonstrating UI components and theme.

This is a demo page that showcases the Midnight UI theme and reusable UI components.
It is intended for development and testing purposes only.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import random

# Import theme and components
from streamlit_app.components.midnight_theme import apply_midnight_theme, highlight_card, neon_metric, status_indicator
from streamlit_app.components.ui_components import (
    code_block, json_viewer, data_table, info_card, warning_card, error_card, success_card,
    searchable_selectbox, toggle_button, collapsible_container, progress_tracker,
    loading_spinner, validated_text_input, error_boundary
)
from streamlit_app.components.visualizations import (
    time_series_chart, bar_chart, pie_chart, scatter_plot, heatmap, metric_gauge, correlation_matrix
)

# Apply the Midnight UI theme
apply_midnight_theme()

def main():
    """Demo page for UI components and theme."""
    st.title("ud83eudde9 Midnight UI Components Demo")
    
    highlight_card(
        "Theme and Component Showcase", 
        "This demo page showcases the Midnight UI theme and reusable UI components for the WrenchAI Streamlit application.",
        icon="u2728"
    )
    
    # Navigation
    st.sidebar.title("ud83cudfa8 Component Gallery")
    section = st.sidebar.radio(
        "Select Section",
        ["Information Display", "Interactive Components", "Monitoring", "Forms", "Error Handling", "Visualizations"]
    )
    
    # Display selected section
    if section == "Information Display":
        show_information_display()
    elif section == "Interactive Components":
        show_interactive_components()
    elif section == "Monitoring":
        show_monitoring_components()
    elif section == "Forms":
        show_form_components()
    elif section == "Error Handling":
        show_error_handling()
    elif section == "Visualizations":
        show_visualizations()

def show_information_display():
    """Show information display components."""
    st.header("Information Display Components")
    
    # Code Block
    st.subheader("Code Block")
    example_code = '''def hello_world():
    """Say hello to the world."""
    print("Hello, World!")
    return True'''
    code_block(example_code, language="python")
    
    # JSON Viewer
    st.subheader("JSON Viewer")
    example_json = {
        "name": "WrenchAI",
        "version": "1.0.0",
        "components": ["UI", "API", "Agents"],
        "config": {
            "theme": "midnight",
            "debug": False,
            "features": ["playbooks", "portfolio"]
        }
    }
    json_viewer(example_json, expanded=True, title="Application Configuration")
    
    # Data Table
    st.subheader("Data Table")
    df = pd.DataFrame({
        "Agent": ["SuperAgent", "InspectorAgent", "JourneyAgent"],
        "Status": ["Active", "Inactive", "Active"],
        "Tasks": [42, 17, 23],
        "Success Rate": [0.95, 0.87, 0.92]
    })
    data_table(df)
    
    # Info Cards
    st.subheader("Info Cards")
    col1, col2 = st.columns(2)
    with col1:
        info_card("Information", "This is an informational message.")
        warning_card("Warning", "This is a warning message!")
    with col2:
        success_card("Success", "Operation completed successfully!")
        error_card("Error", "Something went wrong. Please try again.")

def show_interactive_components():
    """Show interactive components."""
    st.header("Interactive Components")
    
    # Searchable Selectbox
    st.subheader("Searchable Selectbox")
    options = [
        "SuperAgent", "InspectorAgent", "JourneyAgent", "RepoAgent",
        "PortfolioAgent", "AnalyticsAgent", "DocAgent", "DeployAgent"
    ]
    selected = searchable_selectbox("Select Agent", options)
    if selected:
        st.write(f"You selected: {selected}")
    
    # Toggle Button
    st.subheader("Toggle Button")
    col1, col2 = st.columns(2)
    with col1:
        dark_mode = toggle_button("Dark Mode", "dark_mode_toggle", default=True)
        st.write(f"Dark Mode: {dark_mode}")
    with col2:
        notifications = toggle_button("Notifications", "notifications_toggle")
        st.write(f"Notifications: {notifications}")
    
    # Collapsible Container
    st.subheader("Collapsible Container")
    def container_content():
        st.write("This content is inside a collapsible container.")
        st.write("It can contain any Streamlit components.")
        st.metric("Container Metric", 42, 7)
    
    collapsible_container("Expandable Section", container_content, default_expanded=True)

def mock_status_function():
    """Mock function that returns dynamic status data."""
    return {
        "CPU Usage": f"{random.randint(5, 95)}%",
        "Memory": f"{random.randint(30, 80)}%",
        "Active Connections": random.randint(1, 10),
        "Queue Size": random.randint(0, 20)
    }

def show_monitoring_components():
    """Show monitoring components."""
    st.header("Monitoring Components")
    
    # Progress Tracker
    st.subheader("Progress Tracker")
    steps = ["Input", "Processing", "Validation", "Output", "Complete"]
    current_step = st.slider("Current Step", 0, len(steps) - 1, 1)
    progress_tracker(steps, current_step)
    
    # Loading Spinner
    st.subheader("Loading Spinner")
    if st.button("Start Loading"):
        def slow_operation():
            for i in range(5):
                time.sleep(0.5)
                st.write(f"Step {i + 1} completed")
            st.success("Operation complete!")
        
        loading_spinner(slow_operation, "Performing operation...")
    
    # Status Indicators
    st.subheader("Status Indicators")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status_indicator("success", "Online")
    with col2:
        status_indicator("warning", "Degraded")
    with col3:
        status_indicator("error", "Offline")
    with col4:
        status_indicator("info", "Updating")

def show_form_components():
    """Show form components."""
    st.header("Form Components")
    
    # Validated Text Input
    st.subheader("Validated Text Input")
    
    def validate_email(email):
        return "@" in email and "." in email
    
    email, is_valid = validated_text_input(
        "Email Address",
        "email_input",
        validator=validate_email,
        error_message="Please enter a valid email address",
        placeholder="user@example.com"
    )
    
    if email and is_valid:
        st.success(f"Valid email: {email}")
    
    # More form components could be added here

def show_error_handling():
    """Show error handling components."""
    st.header("Error Handling Components")
    
    # Error Boundary
    st.subheader("Error Boundary")
    
    def problematic_function():
        if st.checkbox("Cause Error", key="error_trigger"):
            # This will cause a ZeroDivisionError
            result = 1 / 0
            st.write(f"Result: {result}")
        else:
            st.write("Check the box to trigger an error")
    
    def fallback_ui():
        st.info("This is fallback content when an error occurs")
        if st.button("Reset"):
            st.session_state.error_trigger = False
            st.rerun()
    
    error_boundary(problematic_function, fallback_ui)
    
    # Exception Handling
    st.subheader("Exception Display")
    
    if st.button("Show Sample Exception"):
        try:
            # Deliberately trigger an exception
            non_existent_var = undefined_variable  # noqa
        except Exception as e:
            from components.ui_components import exception_alert
            exception_alert(e, show_traceback=True)

def show_visualizations():
    """Show visualization components."""
    st.header("Visualization Components")
    
    # Generate sample data
    @st.cache_data
    def generate_sample_data():
        # Time series data
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=30, freq='D')
        ts_data = pd.DataFrame({
            'date': dates,
            'value_1': np.random.normal(100, 15, 30).cumsum(),
            'value_2': np.random.normal(50, 10, 30).cumsum()
        })
        
        # Bar chart data
        categories = ['Category A', 'Category B', 'Category C', 'Category D', 'Category E']
        bar_data = pd.DataFrame({
            'category': categories,
            'value': np.random.randint(10, 100, 5),
            'group': np.random.choice(['Group 1', 'Group 2'], 5)
        })
        
        # Pie chart data
        pie_data = pd.DataFrame({
            'segment': ['Segment 1', 'Segment 2', 'Segment 3', 'Segment 4'],
            'value': np.random.randint(10, 100, 4)
        })
        
        # Scatter plot data
        n = 50
        scatter_data = pd.DataFrame({
            'x': np.random.normal(0, 1, n),
            'y': np.random.normal(0, 1, n),
            'size': np.random.randint(5, 25, n),
            'category': np.random.choice(['A', 'B', 'C'], n)
        })
        
        # Heatmap data
        x_labels = ['X1', 'X2', 'X3', 'X4', 'X5']
        y_labels = ['Y1', 'Y2', 'Y3', 'Y4', 'Y5']
        heatmap_data = []
        for x in x_labels:
            for y in y_labels:
                heatmap_data.append({
                    'x': x,
                    'y': y,
                    'value': np.random.uniform(0, 100)
                })
        heatmap_df = pd.DataFrame(heatmap_data)
        
        # Correlation matrix data
        corr_data = pd.DataFrame(np.random.randn(100, 5), columns=['A', 'B', 'C', 'D', 'E'])
        # Add some correlation
        corr_data['B'] = corr_data['A'] + np.random.randn(100) * 0.5
        corr_data['C'] = -corr_data['A'] + np.random.randn(100) * 0.5
        
        return ts_data, bar_data, pie_data, scatter_data, heatmap_df, corr_data
    
    # Get the sample data
    ts_data, bar_data, pie_data, scatter_data, heatmap_data, corr_data = generate_sample_data()
    
    # Select visualization type
    viz_type = st.selectbox(
        "Select Visualization Type",
        ["Time Series", "Bar Chart", "Pie Chart", "Scatter Plot", "Heatmap", "Gauge", "Correlation Matrix"]
    )
    
    # Show selected visualization
    if viz_type == "Time Series":
        st.subheader("Time Series Chart")
        time_series_chart(
            ts_data,
            x_column="date",
            y_columns=["value_1", "value_2"],
            title="Sample Time Series"
        )
        
    elif viz_type == "Bar Chart":
        st.subheader("Bar Chart")
        orientation = st.radio("Orientation", ["Vertical", "Horizontal"])
        bar_chart(
            bar_data,
            x_column="category",
            y_column="value",
            color_column="group",
            horizontal=(orientation == "Horizontal"),
            title="Sample Bar Chart"
        )
        
    elif viz_type == "Pie Chart":
        st.subheader("Pie/Donut Chart")
        hole_size = st.slider("Donut Hole Size", 0.0, 0.8, 0.4, 0.1)
        pie_chart(
            pie_data,
            names_column="segment",
            values_column="value",
            title="Sample Pie Chart",
            hole=hole_size
        )
        
    elif viz_type == "Scatter Plot":
        st.subheader("Scatter Plot")
        scatter_plot(
            scatter_data,
            x_column="x",
            y_column="y",
            color_column="category",
            size_column="size",
            title="Sample Scatter Plot"
        )
        
    elif viz_type == "Heatmap":
        st.subheader("Heatmap")
        heatmap(
            heatmap_data,
            x_column="x",
            y_column="y",
            value_column="value",
            title="Sample Heatmap"
        )
        
    elif viz_type == "Gauge":
        st.subheader("Metric Gauge")
        value = st.slider("Gauge Value", 0, 100, 65)
        metric_gauge(
            value=value,
            min_value=0,
            max_value=100,
            title="Sample Gauge"
        )
        
    elif viz_type == "Correlation Matrix":
        st.subheader("Correlation Matrix")
        correlation_matrix(
            corr_data,
            title="Sample Correlation Matrix"
        )

if __name__ == "__main__":
    main()