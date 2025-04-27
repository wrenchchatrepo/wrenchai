"""
Metrics dashboard for monitoring system performance and agent activities.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import redis
import json
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

# Redis connection for metrics
redis_client = redis.from_url(st.secrets["redis_url"])

def load_system_metrics() -> Dict[str, Any]:
    """Load system metrics from Redis."""
    try:
        data = redis_client.get("system_metrics")
        return json.loads(data) if data else {}
    except Exception as e:
        logger.error(f"Failed to load system metrics: {e}")
        return {}

def load_agent_metrics() -> Dict[str, List[Dict[str, Any]]]:
    """Load agent performance metrics."""
    try:
        data = redis_client.get("agent_metrics")
        return json.loads(data) if data else {}
    except Exception as e:
        logger.error(f"Failed to load agent metrics: {e}")
        return {}

def load_api_metrics() -> Dict[str, Any]:
    """Load API performance metrics."""
    try:
        data = redis_client.get("api_metrics")
        return json.loads(data) if data else {}
    except Exception as e:
        logger.error(f"Failed to load API metrics: {e}")
        return {}

def create_system_metrics_chart(metrics: Dict[str, Any]) -> go.Figure:
    """Create system metrics chart."""
    fig = go.Figure()
    
    # CPU Usage
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=metrics.get("cpu_usage", 0),
        title={"text": "CPU Usage (%)"},
        domain={"row": 0, "column": 0},
        gauge={"axis": {"range": [0, 100]}}
    ))
    
    # Memory Usage
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=metrics.get("memory_usage", 0),
        title={"text": "Memory Usage (%)"},
        domain={"row": 0, "column": 1},
        gauge={"axis": {"range": [0, 100]}}
    ))
    
    # Layout
    fig.update_layout(
        grid={"rows": 1, "columns": 2},
        height=250
    )
    
    return fig

def create_agent_performance_chart(metrics: Dict[str, List[Dict[str, Any]]]) -> go.Figure:
    """Create agent performance chart."""
    fig = go.Figure()
    
    for agent, data in metrics.items():
        df = pd.DataFrame(data)
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df["tasks_completed"],
            name=agent,
            mode="lines+markers"
        ))
    
    fig.update_layout(
        title="Agent Performance",
        xaxis_title="Time",
        yaxis_title="Tasks Completed",
        height=300
    )
    
    return fig

def create_api_metrics_chart(metrics: Dict[str, Any]) -> go.Figure:
    """Create API metrics chart."""
    fig = go.Figure()
    
    # Response times
    df = pd.DataFrame(metrics.get("response_times", []))
    fig.add_trace(go.Box(
        y=df["duration"],
        name="Response Time (ms)",
        boxpoints="all"
    ))
    
    fig.update_layout(
        title="API Response Times",
        yaxis_title="Duration (ms)",
        height=300
    )
    
    return fig

def create_error_rate_chart(metrics: Dict[str, Any]) -> go.Figure:
    """Create error rate chart."""
    fig = go.Figure()
    
    df = pd.DataFrame(metrics.get("errors", []))
    if not df.empty:
        fig.add_trace(go.Pie(
            labels=df["type"],
            values=df["count"],
            hole=0.3
        ))
    
    fig.update_layout(
        title="Error Distribution",
        height=300
    )
    
    return fig

def main():
    """Main dashboard function."""
    st.title("System Metrics Dashboard")
    
    # Refresh interval
    refresh_interval = st.sidebar.slider(
        "Refresh Interval (seconds)",
        min_value=5,
        max_value=60,
        value=10
    )
    
    # Time range
    time_range = st.sidebar.selectbox(
        "Time Range",
        ["Last Hour", "Last Day", "Last Week"]
    )
    
    # Auto-refresh checkbox
    auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)
    
    # Main metrics display
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("System Health")
        metrics = load_system_metrics()
        st.plotly_chart(
            create_system_metrics_chart(metrics),
            use_container_width=True
        )
    
    with col2:
        st.subheader("Agent Status")
        agent_metrics = load_agent_metrics()
        status_df = pd.DataFrame([
            {"Agent": agent, "Status": "Active" if data[-1]["active"] else "Inactive"}
            for agent, data in agent_metrics.items()
        ])
        st.dataframe(status_df)
    
    # Agent performance
    st.subheader("Agent Performance")
    agent_metrics = load_agent_metrics()
    st.plotly_chart(
        create_agent_performance_chart(agent_metrics),
        use_container_width=True
    )
    
    # API metrics
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("API Performance")
        api_metrics = load_api_metrics()
        st.plotly_chart(
            create_api_metrics_chart(api_metrics),
            use_container_width=True
        )
    
    with col4:
        st.subheader("Error Analysis")
        st.plotly_chart(
            create_error_rate_chart(api_metrics),
            use_container_width=True
        )
    
    # Detailed metrics table
    st.subheader("Detailed Metrics")
    detailed_metrics = {
        "Total Requests": api_metrics.get("total_requests", 0),
        "Average Response Time": f"{api_metrics.get('avg_response_time', 0):.2f} ms",
        "Error Rate": f"{api_metrics.get('error_rate', 0):.2%}",
        "Active Users": api_metrics.get("active_users", 0),
        "Database Connections": metrics.get("db_connections", 0),
        "Cache Hit Rate": f"{metrics.get('cache_hit_rate', 0):.2%}"
    }
    st.table(pd.DataFrame([detailed_metrics]).T)
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(refresh_interval)
        st.experimental_rerun()

if __name__ == "__main__":
    main() 