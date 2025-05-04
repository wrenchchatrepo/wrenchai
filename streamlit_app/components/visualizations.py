"""Data visualization components for WrenchAI Streamlit application.

This module provides a collection of visualization components built on top of
Streamlit and various charting libraries, styled to match the Midnight UI theme.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
import altair as alt
import plotly.express as px
import plotly.graph_objects as go

# Set base colors for visualization components
COLOR_PALETTE = {
    'primary': '#00CCFF',    # Bright cyan
    'secondary': '#7B42F6',  # Purple
    'tertiary': '#00FF9D',   # Bright green
    'quaternary': '#FFD600', # Bright yellow
    'danger': '#FF453A',     # Bright red
    'dark': '#121212',       # Nearly black
    'dark_panel': '#1E1E1E', # Dark gray
    'dark_highlight': '#2A2A2A', # Lighter dark gray
    'text': '#F0F0F0',       # Off-white
    'text_secondary': '#BBBBBB' # Light gray
}

# Streamlit doesn't yet allow full control over chart styling
# We can set some base styles for Altair and Plotly
alt.themes.register('midnightui', lambda: {
    'config': {
        'background': COLOR_PALETTE['dark'],
        'title': {'color': COLOR_PALETTE['primary']},
        'style': {'cell': {'stroke': 'transparent'}},
        'header': {'labelColor': COLOR_PALETTE['primary']},
        'axis': {
            'labelColor': COLOR_PALETTE['text'],
            'titleColor': COLOR_PALETTE['text'],
            'gridColor': COLOR_PALETTE['dark_highlight'],
            'domainColor': COLOR_PALETTE['dark_highlight']
        },
        'legend': {
            'labelColor': COLOR_PALETTE['text'],
            'titleColor': COLOR_PALETTE['text'],
        },
        'range': {
            'category': [
                COLOR_PALETTE['primary'],
                COLOR_PALETTE['secondary'],
                COLOR_PALETTE['tertiary'],
                COLOR_PALETTE['quaternary'],
                COLOR_PALETTE['danger']
            ]
        }
    }
})

# Set the default theme for Altair
alt.themes.enable('midnightui')

# Default Plotly template
PLOTLY_TEMPLATE = {
    'layout': {
        'paper_bgcolor': COLOR_PALETTE['dark'],
        'plot_bgcolor': COLOR_PALETTE['dark'],
        'font': {'color': COLOR_PALETTE['text']},
        'title': {'font': {'color': COLOR_PALETTE['primary']}},
        'xaxis': {
            'gridcolor': COLOR_PALETTE['dark_highlight'],
            'zerolinecolor': COLOR_PALETTE['dark_highlight'],
            'title': {'font': {'color': COLOR_PALETTE['text']}},
            'tickfont': {'color': COLOR_PALETTE['text']}
        },
        'yaxis': {
            'gridcolor': COLOR_PALETTE['dark_highlight'],
            'zerolinecolor': COLOR_PALETTE['dark_highlight'],
            'title': {'font': {'color': COLOR_PALETTE['text']}},
            'tickfont': {'color': COLOR_PALETTE['text']}
        },
        'legend': {'font': {'color': COLOR_PALETTE['text']}},
        'colorway': [
            COLOR_PALETTE['primary'],
            COLOR_PALETTE['secondary'],
            COLOR_PALETTE['tertiary'],
            COLOR_PALETTE['quaternary'],
            COLOR_PALETTE['danger']
        ]
    }
}


def time_series_chart(data: pd.DataFrame, x_column: str, y_columns: Union[str, List[str]], 
                   title: str = "Time Series", height: int = 400, use_container_width: bool = True):
    """Create a time series line chart using Altair.
    
    Args:
        data: DataFrame with the data to plot
        x_column: Column name for the x-axis (typically a date/time column)
        y_columns: Column name(s) for the y-axis values
        title: Chart title
        height: Chart height in pixels
        use_container_width: Whether to expand chart to container width
    
    Returns:
        Altair chart object
    """
    # Convert y_columns to a list if it's a string
    if isinstance(y_columns, str):
        y_columns = [y_columns]
        
    # Create a base chart
    base = alt.Chart(data).encode(
        x=alt.X(x_column, title=x_column.replace('_', ' ').title()),
        tooltip=[x_column] + y_columns
    ).properties(
        title=title,
        height=height
    )
    
    # Create a line for each y column
    lines = []
    for i, col in enumerate(y_columns):
        # Use a different color for each line
        color = list(COLOR_PALETTE.values())[i % 5]  # Cycle through the first 5 colors
        
        line = base.mark_line(strokeWidth=3).encode(
            y=alt.Y(col, title=col.replace('_', ' ').title()),
            color=alt.value(color)
        )
        
        # Add points on the line
        points = base.mark_circle(size=80, opacity=0.7, stroke=COLOR_PALETTE['dark'], strokeWidth=1).encode(
            y=alt.Y(col),
            color=alt.value(color)
        )
        
        lines.extend([line, points])
    
    # Combine all layers
    chart = alt.layer(*lines)
    
    # Display the chart
    st.altair_chart(chart, use_container_width=use_container_width)
    
    return chart


def bar_chart(data: pd.DataFrame, x_column: str, y_column: str, 
            color_column: Optional[str] = None, horizontal: bool = False,
            title: str = "Bar Chart", height: int = 400, use_container_width: bool = True):
    """Create a bar chart using Altair with midnight theme styling.
    
    Args:
        data: DataFrame with the data to plot
        x_column: Column name for the x-axis categories
        y_column: Column name for the y-axis values
        color_column: Optional column name for color encoding
        horizontal: Whether to create a horizontal bar chart
        title: Chart title
        height: Chart height in pixels
        use_container_width: Whether to expand chart to container width
    
    Returns:
        Altair chart object
    """
    # Determine which encoding is x and which is y based on orientation
    if horizontal:
        x_encoding = alt.X(y_column, title=y_column.replace('_', ' ').title())
        y_encoding = alt.Y(x_column, title=x_column.replace('_', ' ').title(), sort='-x')
    else:
        x_encoding = alt.X(x_column, title=x_column.replace('_', ' ').title())
        y_encoding = alt.Y(y_column, title=y_column.replace('_', ' ').title())
    
    # Create color encoding if specified
    encodings = {'x': x_encoding, 'y': y_encoding, 'tooltip': [x_column, y_column]}
    if color_column:
        encodings['color'] = alt.Color(color_column, scale=alt.Scale(
            range=[COLOR_PALETTE['primary'], COLOR_PALETTE['secondary'], 
                  COLOR_PALETTE['tertiary'], COLOR_PALETTE['quaternary']]
        ))
        encodings['tooltip'].append(color_column)
    
    # Create the bar chart
    chart = alt.Chart(data).mark_bar().encode(
        **encodings
    ).properties(
        title=title,
        height=height
    )
    
    # Display the chart
    st.altair_chart(chart, use_container_width=use_container_width)
    
    return chart


def pie_chart(data: pd.DataFrame, names_column: str, values_column: str, 
            title: str = "Pie Chart", hole: float = 0.4, height: int = 400, 
            use_container_width: bool = True):
    """Create a donut/pie chart using Plotly with midnight theme styling.
    
    Args:
        data: DataFrame with the data to plot
        names_column: Column name for the pie slice names/categories
        values_column: Column name for the pie slice values/sizes
        title: Chart title
        hole: Size of the donut hole (0 for pie chart, 0-1 for donut)
        height: Chart height in pixels
        use_container_width: Whether to expand chart to container width
    
    Returns:
        Plotly figure object
    """
    # Create a color sequence cycling through our palette
    colors = [COLOR_PALETTE['primary'], COLOR_PALETTE['secondary'], 
              COLOR_PALETTE['tertiary'], COLOR_PALETTE['quaternary'], 
              COLOR_PALETTE['danger']]
              
    # Create the pie chart
    fig = go.Figure(data=[go.Pie(
        labels=data[names_column],
        values=data[values_column],
        hole=hole,
        textinfo='label+percent',
        insidetextorientation='radial',
        marker_colors=colors
    )])
    
    # Apply styling
    fig.update_layout(
        title_text=title,
        height=height,
        paper_bgcolor=COLOR_PALETTE['dark'],
        plot_bgcolor=COLOR_PALETTE['dark'],
        font=dict(color=COLOR_PALETTE['text']),
        legend=dict(font=dict(color=COLOR_PALETTE['text']))
    )
    
    # Display the chart
    st.plotly_chart(fig, use_container_width=use_container_width)
    
    return fig


def scatter_plot(data: pd.DataFrame, x_column: str, y_column: str, 
               color_column: Optional[str] = None, size_column: Optional[str] = None,
               title: str = "Scatter Plot", height: int = 500, use_container_width: bool = True):
    """Create an interactive scatter plot using Plotly with midnight theme styling.
    
    Args:
        data: DataFrame with the data to plot
        x_column: Column name for the x-axis
        y_column: Column name for the y-axis
        color_column: Optional column name for point colors
        size_column: Optional column name for point sizes
        title: Chart title
        height: Chart height in pixels
        use_container_width: Whether to expand chart to container width
    
    Returns:
        Plotly figure object
    """
    # Create the scatter plot with Plotly Express
    fig = px.scatter(
        data,
        x=x_column,
        y=y_column,
        color=color_column,
        size=size_column,
        title=title,
        height=height,
        template='plotly',  # We'll override this with our custom styling
        color_discrete_sequence=[COLOR_PALETTE['primary'], COLOR_PALETTE['secondary'], 
                                COLOR_PALETTE['tertiary'], COLOR_PALETTE['quaternary']]
    )
    
    # Apply custom styling from our template
    fig.update_layout(**PLOTLY_TEMPLATE['layout'])
    
    # Custom marker styling
    fig.update_traces(
        marker=dict(
            line=dict(width=1, color=COLOR_PALETTE['dark']),
            opacity=0.8
        )
    )
    
    # Display the chart
    st.plotly_chart(fig, use_container_width=use_container_width)
    
    return fig


def heatmap(data: pd.DataFrame, x_column: str, y_column: str, value_column: str,
          title: str = "Heatmap", height: int = 400, color_scheme: str = "viridis",
          use_container_width: bool = True):
    """Create a heatmap using Altair with midnight theme styling.
    
    Args:
        data: DataFrame with the data to plot
        x_column: Column name for the x-axis
        y_column: Column name for the y-axis
        value_column: Column name for the cell values/colors
        title: Chart title
        height: Chart height in pixels
        color_scheme: Color scheme for the heatmap
        use_container_width: Whether to expand chart to container width
    
    Returns:
        Altair chart object
    """
    # Create the heatmap
    chart = alt.Chart(data).mark_rect().encode(
        x=alt.X(x_column, title=x_column.replace('_', ' ').title()),
        y=alt.Y(y_column, title=y_column.replace('_', ' ').title()),
        color=alt.Color(value_column, scale=alt.Scale(scheme=color_scheme)),
        tooltip=[x_column, y_column, value_column]
    ).properties(
        title=title,
        height=height
    )
    
    # Display the chart
    st.altair_chart(chart, use_container_width=use_container_width)
    
    return chart


def metric_gauge(value: float, min_value: float = 0, max_value: float = 100,
               threshold_ranges: Optional[List[Tuple[float, float, str]]] = None,
               title: str = "Metric", format_string: str = "{:.1f}",
               height: int = 300, use_container_width: bool = True):
    """Create a gauge chart for a single metric using Plotly.
    
    Args:
        value: The metric value to display
        min_value: Minimum scale value
        max_value: Maximum scale value
        threshold_ranges: List of (min, max, color) tuples defining color ranges
        title: Chart title
        format_string: Format string for the value display
        height: Chart height in pixels
        use_container_width: Whether to expand chart to container width
    
    Returns:
        Plotly figure object
    """
    # Default threshold ranges if none provided
    if threshold_ranges is None:
        threshold_ranges = [
            (min_value, max_value * 0.4, COLOR_PALETTE['danger']),    # 0-40%: Red
            (max_value * 0.4, max_value * 0.7, COLOR_PALETTE['quaternary']),  # 40-70%: Yellow
            (max_value * 0.7, max_value, COLOR_PALETTE['tertiary'])      # 70-100%: Green
        ]
        
    # Format the display value
    display_value = format_string.format(value)
    
    # Determine the color based on thresholds
    value_color = COLOR_PALETTE['primary']  # Default color
    for min_thresh, max_thresh, color in threshold_ranges:
        if min_thresh <= value <= max_thresh:
            value_color = color
            break
            
    # Create the gauge chart
    fig = go.Figure()
    
    # Add the gauge
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title},
        number={
            'valueformat': format_string,
            'font': {'color': value_color, 'size': 40}
        },
        gauge={
            'axis': {
                'range': [min_value, max_value],
                'tickcolor': COLOR_PALETTE['text'],
                'tickfont': {'color': COLOR_PALETTE['text']}
            },
            'bar': {'color': value_color},
            'bgcolor': COLOR_PALETTE['dark_highlight'],
            'borderwidth': 0,
            'steps': [
                {'range': [range_min, range_max], 'color': color}
                for range_min, range_max, color in threshold_ranges
            ]
        }
    ))
    
    # Apply custom styling
    fig.update_layout(
        height=height,
        paper_bgcolor=COLOR_PALETTE['dark'],
        font={'color': COLOR_PALETTE['text']}
    )
    
    # Display the chart
    st.plotly_chart(fig, use_container_width=use_container_width)
    
    return fig


def correlation_matrix(data: pd.DataFrame, columns: Optional[List[str]] = None,
                     title: str = "Correlation Matrix", height: int = 500,
                     use_container_width: bool = True):
    """Create a correlation matrix heatmap using Plotly.
    
    Args:
        data: DataFrame with the numerical data
        columns: List of columns to include in the correlation matrix
        title: Chart title
        height: Chart height in pixels
        use_container_width: Whether to expand chart to container width
    
    Returns:
        Plotly figure object
    """
    # Select columns if specified, otherwise use all numeric columns
    if columns:
        df = data[columns].select_dtypes(include=['number'])
    else:
        df = data.select_dtypes(include=['number'])
        
    # Calculate correlation matrix
    corr = df.corr()
    
    # Create the heatmap
    fig = go.Figure(data=go.Heatmap(
        z=corr.values,
        x=corr.columns,
        y=corr.columns,
        colorscale=[
            [0, COLOR_PALETTE['danger']],  # Negative correlation
            [0.5, COLOR_PALETTE['dark_highlight']],  # No correlation
            [1, COLOR_PALETTE['primary']]   # Positive correlation
        ],
        zmin=-1,
        zmax=1,
        hoverongaps=False
    ))
    
    # Apply custom styling
    fig.update_layout(
        title=title,
        height=height,
        paper_bgcolor=COLOR_PALETTE['dark'],
        plot_bgcolor=COLOR_PALETTE['dark'],
        font={'color': COLOR_PALETTE['text']}
    )
    
    # Display the chart
    st.plotly_chart(fig, use_container_width=use_container_width)
    
    return fig