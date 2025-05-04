"""
Metrics dashboard for monitoring system performance and agent activities.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import json
from typing import Dict, List, Any
import logging

# Import mock metrics data provider
from streamlit_app.components.mock_metrics import MockRedisClient
from streamlit_app.components.midnight_theme import apply_midnight_theme

# Apply the midnight theme
apply_midnight_theme()

logger = logging.getLogger(__name__)

# Create a mock Redis client for metrics
redis_client = MockRedisClient()

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
    
    # Custom colors for the gauges
    colors = {
        "low": "#00FF9D",  # Green
        "medium": "#FFD600",  # Yellow
        "high": "#FF453A"  # Red
    }
    
    # Function to get color based on value
    def get_color(value):
        if value < 40:
            return colors["low"]
        elif value < 70:
            return colors["medium"]
        else:
            return colors["high"]
    
    # CPU Usage
    cpu_usage = metrics.get("cpu_usage", 0)
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=cpu_usage,
        title={"text": "CPU Usage (%)", "font": {"color": "#F0F0F0"}},
        domain={"row": 0, "column": 0},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#F0F0F0"},
            "bar": {"color": get_color(cpu_usage)},
            "bgcolor": "#2A2A2A"
        },
        number={"font": {"color": get_color(cpu_usage)}}
    ))
    
    # Memory Usage
    memory_usage = metrics.get("memory_usage", 0)
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=memory_usage,
        title={"text": "Memory Usage (%)", "font": {"color": "#F0F0F0"}},
        domain={"row": 0, "column": 1},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#F0F0F0"},
            "bar": {"color": get_color(memory_usage)},
            "bgcolor": "#2A2A2A"
        },
        number={"font": {"color": get_color(memory_usage)}}
    ))
    
    # Layout
    fig.update_layout(
        grid={"rows": 1, "columns": 2},
        height=250,
        paper_bgcolor="#121212",
        plot_bgcolor="#121212",
        font={"color": "#F0F0F0"}
    )
    
    return fig

def create_agent_performance_chart(metrics: Dict[str, List[Dict[str, Any]]]) -> go.Figure:
    """Create agent performance chart."""
    fig = go.Figure()
    
    # Theme colors
    colors = ["#00CCFF", "#7B42F6", "#00FF9D", "#FFD600"]
    
    for i, (agent, data) in enumerate(metrics.items()):
        df = pd.DataFrame(data)
        # Convert timestamp strings to datetime
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df["tasks_completed"],
            name=agent,
            mode="lines+markers",
            line={"color": colors[i % len(colors)], "width": 3},
            marker={"size": 8}
        ))
    
    fig.update_layout(
        title={"text": "Agent Performance", "font": {"color": "#F0F0F0"}},
        xaxis_title={"text": "Time", "font": {"color": "#F0F0F0"}},
        yaxis_title={"text": "Tasks Completed", "font": {"color": "#F0F0F0"}},
        height=300,
        paper_bgcolor="#121212",
        plot_bgcolor="#121212",
        font={"color": "#F0F0F0"},
        xaxis={"gridcolor": "#2A2A2A", "zerolinecolor": "#2A2A2A"},
        yaxis={"gridcolor": "#2A2A2A", "zerolinecolor": "#2A2A2A"}
    )
    
    return fig

def create_api_metrics_chart(metrics: Dict[str, Any]) -> go.Figure:
    """Create API metrics chart."""
    fig = go.Figure()
    
    # Response times
    response_data = metrics.get("response_times", [])
    if response_data:
        df = pd.DataFrame(response_data)
        # Group by endpoint
        endpoints = df["endpoint"].unique()
        
        for i, endpoint in enumerate(endpoints):
            endpoint_df = df[df["endpoint"] == endpoint]
            fig.add_trace(go.Box(
                y=endpoint_df["duration"],
                name=endpoint.split("/")[-1],
                boxpoints="outliers",
                marker_color="#00CCFF",
                line_color="#7B42F6"
            ))
    
    fig.update_layout(
        title={"text": "API Response Times (ms)", "font": {"color": "#F0F0F0"}},
        yaxis_title={"text": "Duration (ms)", "font": {"color": "#F0F0F0"}},
        height=300,
        paper_bgcolor="#121212",
        plot_bgcolor="#121212",
        font={"color": "#F0F0F0"},
        xaxis={"gridcolor": "#2A2A2A"},
        yaxis={"gridcolor": "#2A2A2A"}
    )
    
    return fig

def create_error_rate_chart(metrics: Dict[str, Any]) -> go.Figure:
    """Create error rate chart."""
    fig = go.Figure()
    
    error_data = metrics.get("errors", [])
    if error_data:
        df = pd.DataFrame(error_data)
        fig.add_trace(go.Pie(
            labels=df["type"],
            values=df["count"],
            hole=0.4,
            textinfo="label+percent",
            marker={
                "colors": ["#FF453A", "#FFD600", "#00CCFF", "#7B42F6", "#00FF9D"]
            }
        ))
    
    fig.update_layout(
        title={"text": "Error Distribution", "font": {"color": "#F0F0F0"}},
        height=300,
        paper_bgcolor="#121212",
        plot_bgcolor="#121212",
        font={"color": "#F0F0F0"}
    )
    
    return fig

def main():
    """Main dashboard function."""
    st.title("📊 System Metrics Dashboard")
    
    # Sidebar controls
    st.sidebar.subheader("Dashboard Settings")
    
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
    
    # Last refresh time
    last_refresh = datetime.now()
    st.sidebar.caption(f"Last Updated: {last_refresh.strftime('%H:%M:%S')}")
    
    # Display a more modern dashboard layout with cards
    st.markdown("""
    <style>
    .metric-card {
        background-color: #1E1E1E;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # System metrics
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.subheader("💻 System Health")
    metrics = load_system_metrics()
    st.plotly_chart(
        create_system_metrics_chart(metrics),
        use_container_width=True
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Agent metrics
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Agent performance chart
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader("🤖 Agent Performance")
        agent_metrics = load_agent_metrics()
        st.plotly_chart(
            create_agent_performance_chart(agent_metrics),
            use_container_width=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        # Agent status
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader("📡 Agent Status")
        agent_metrics = load_agent_metrics()
        
        # Create a more visually appealing agent status display
        for agent, data in agent_metrics.items():
            is_active = data[-1]["active"] if data else False
            success_rate = data[-1]["success_rate"] if data else 0
            
            # Status indicator
            status_color = "#00FF9D" if is_active else "#FF453A"
            status_text = "Active" if is_active else "Inactive"
            
            # Format success rate as percentage
            success_percentage = f"{success_rate * 100:.1f}%"
            
            # Create a card-like display for each agent
            st.markdown(f"""
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px;
                margin-bottom: 10px;
                background-color: #2A2A2A;
                border-radius: 5px;
            ">
                <div>
                    <div style="font-weight: bold;">{agent}</div>
                    <div style="font-size: 0.8em; color: #BBBBBB;">Success Rate: {success_percentage}</div>
                </div>
                <div style="
                    display: flex;
                    align-items: center;
                    background-color: rgba({','.join(str(int(c)) for c in bytes.fromhex(status_color[1:]))}, 0.2);
                    padding: 5px 10px;
                    border-radius: 20px;
                    color: {status_color};
                ">
                    <div style="
                        width: 10px;
                        height: 10px;
                        border-radius: 50%;
                        background-color: {status_color};
                        margin-right: 5px;
                    "></div>
                    {status_text}
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # API metrics and error analysis
    col3, col4 = st.columns(2)
    
    with col3:
        # API performance
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader("🗜️ API Performance")
        api_metrics = load_api_metrics()
        st.plotly_chart(
            create_api_metrics_chart(api_metrics),
            use_container_width=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        # Error analysis
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader("⛔ Error Analysis")
        st.plotly_chart(
            create_error_rate_chart(api_metrics),
            use_container_width=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Detailed metrics card
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.subheader("📋 Detailed Metrics")
    
    # Create a more visually appealing metrics display
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.markdown("""
        <div style="text-align: center;">
            <div style="font-size: 0.9em; color: #BBBBBB;">Total Requests</div>
            <div style="font-size: 1.8em; color: #00CCFF; font-weight: bold;">{:,}</div>
        </div>
        """.format(api_metrics.get("total_requests", 0)), unsafe_allow_html=True)
    
    with col6:
        st.markdown("""
        <div style="text-align: center;">
            <div style="font-size: 0.9em; color: #BBBBBB;">Avg Response Time</div>
            <div style="font-size: 1.8em; color: #7B42F6; font-weight: bold;">{:.1f} ms</div>
        </div>
        """.format(api_metrics.get("avg_response_time", 0)), unsafe_allow_html=True)
    
    with col7:
        error_rate = api_metrics.get("error_rate", 0)
        error_color = "#00FF9D" if error_rate < 0.05 else "#FFD600" if error_rate < 0.1 else "#FF453A"
        st.markdown("""
        <div style="text-align: center;">
            <div style="font-size: 0.9em; color: #BBBBBB;">Error Rate</div>
            <div style="font-size: 1.8em; color: {}; font-weight: bold;">{:.1%}</div>
        </div>
        """.format(error_color, error_rate), unsafe_allow_html=True)
    
    with col8:
        st.markdown("""
        <div style="text-align: center;">
            <div style="font-size: 0.9em; color: #BBBBBB;">Active Users</div>
            <div style="font-size: 1.8em; color: #00FF9D; font-weight: bold;">{:,}</div>
        </div>
        """.format(api_metrics.get("active_users", 0)), unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

if __name__ == "__main__":
    main()