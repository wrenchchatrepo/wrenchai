import streamlit as st

"""
Midnight UI Theme - Core Theme Module

This module provides additional styling and component-specific theming
beyond what's possible with Streamlit's config.toml theme settings.

Color Palette:
- Primary Neon: #00CCFF (bright cyan - interactive elements)
- Secondary Neon: #7B42F6 (purple - accents)
- Background Dark: #121212 (nearly black - main background)
- Panel Dark: #1E1E1E (dark gray - sidebar, widgets)
- Highlight Dark: #2A2A2A (lighter dark gray - hover states)
- Success: #00FF9D (bright green)
- Warning: #FFD600 (bright yellow)
- Error: #FF453A (bright red)
- Text Primary: #F0F0F0 (off-white)
- Text Secondary: #BBBBBB (light gray)

Font:
- OpenDyslexic Nerd Font - Accessible font designed to help with dyslexia
"""

# CSS for advanced styling
def apply_midnight_theme():
    """Apply the Midnight UI theme with advanced styling."""
    
    # Main CSS for the Midnight theme
    st.markdown("""
    <style>
    /* Import OpenDyslexic font */
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans&display=swap');
    
    /* Base tweaks */
    .stApp {
        background-color: #121212;
        font-family: 'OpenDyslexic', 'Open Sans', sans-serif !important;
    }
    
    /* Apply font to all elements */
    * {
        font-family: 'OpenDyslexic', 'Open Sans', sans-serif !important;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #1E1E1E;
        border-right: 1px solid #2A2A2A;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #00CCFF !important;
        font-weight: 600 !important;
        font-family: 'OpenDyslexic', 'Open Sans', sans-serif !important;
    }
    
    /* Links */
    a, a:visited {
        color: #7B42F6 !important;
    }
    a:hover {
        color: #00CCFF !important;
        text-decoration: none;
    }
    
    /* Code formatting */
    code {
        background-color: #2A2A2A !important;
        color: #00FF9D !important;
        padding: 0.2em 0.4em !important;
        border-radius: 3px !important;
        font-family: 'OpenDyslexic Mono', monospace !important;
    }
    
    /* DataFrames */
    .dataframe {
        border: none !important;
    }
    .dataframe th {
        background-color: #1E1E1E !important;
        color: #00CCFF !important;
    }
    .dataframe td {
        background-color: #2A2A2A !important;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #1E1E1E !important;
        color: #00CCFF !important;
        border: 1px solid #00CCFF !important;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #00CCFF !important;
        color: #121212 !important;
    }
    
    /* Status colors */
    .status-success {
        color: #00FF9D !important;
    }
    .status-warning {
        color: #FFD600 !important;
    }
    .status-error {
        color: #FF453A !important;
    }
    
    /* Info boxes */
    .info-box {
        background-color: #1E1E1E;
        border-left: 4px solid #00CCFF;
        padding: 10px 15px;
        border-radius: 0 4px 4px 0;
        margin: 1em 0;
    }
    .warning-box {
        background-color: #1E1E1E;
        border-left: 4px solid #FFD600;
        padding: 10px 15px;
        border-radius: 0 4px 4px 0;
        margin: 1em 0;
    }
    .error-box {
        background-color: #1E1E1E;
        border-left: 4px solid #FF453A;
        padding: 10px 15px;
        border-radius: 0 4px 4px 0;
        margin: 1em 0;
    }
    
    /* Progress bars */
    .stProgress > div > div > div > div {
        background-color: #00CCFF !important;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #1E1E1E !important;
        color: #F0F0F0 !important;
    }
    .streamlit-expanderHeader:hover {
        background-color: #2A2A2A !important;
    }
    .streamlit-expanderContent {
        background-color: #1E1E1E !important;
        color: #F0F0F0 !important;
    }
    </style>
    """, unsafe_allow_html=True)


def highlight_card(title, content, icon="🔷", border_color="#00CCFF"):
    """Display content in a highlighted card with custom styling.
    
    Args:
        title (str): The card title
        content (str): The card content (can include markdown)
        icon (str, optional): Emoji or icon for the card. Defaults to "🔷".
        border_color (str, optional): Border color hex. Defaults to "#00CCFF".
    """
    st.markdown(f"""
    <div style="
        background-color: #1E1E1E;
        border-left: 4px solid {border_color};
        border-radius: 4px;
        padding: 15px 20px;
        margin: 1em 0;
    ">
        <h3 style="
            margin-top: 0;
            color: {border_color} !important;
            font-size: 1.2em;
            display: flex;
            align-items: center;
        "><span style="margin-right: 10px;">{icon}</span> {title}</h3>
        <div>{content}</div>
    </div>
    """, unsafe_allow_html=True)


def neon_metric(label, value, delta=None, delta_color="normal"):
    """Display a metric with neon styling.
    
    Args:
        label (str): Metric label
        value (str/int/float): Metric value
        delta (str/int/float, optional): Delta value. Defaults to None.
        delta_color (str, optional): Color for delta ('normal', 'inverse', 'off'). Defaults to "normal".
    """
    if delta is not None:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.metric(label=label, value=value, delta=delta, delta_color=delta_color)
    else:
        st.metric(label=label, value=value)
    
    # Apply custom styling to the last metric widget
    st.markdown("""
    <style>
    div[data-testid="metric-container"]:last-of-type {
        background-color: #1E1E1E;
        border-radius: 5px;
        padding: 10px 15px;
        border: 1px solid #2A2A2A;
    }
    div[data-testid="metric-container"]:last-of-type label[data-testid="stMetricLabel"] {
        color: #BBBBBB !important;
    }
    div[data-testid="metric-container"]:last-of-type p[data-testid="stMetricValue"] {
        color: #00CCFF !important;
        font-size: 2em !important;
    }
    </style>
    """, unsafe_allow_html=True)


def status_indicator(status, text):
    """Display a status indicator with appropriate coloring.
    
    Args:
        status (str): Status type ('success', 'warning', 'error', or 'info')
        text (str): Status text to display
    """
    status_colors = {
        'success': "#00FF9D",
        'warning': "#FFD600",
        'error': "#FF453A",
        'info': "#00CCFF"
    }
    
    color = status_colors.get(status.lower(), "#00CCFF")
    
    st.markdown(f"""
    <div style="
        display: inline-flex;
        align-items: center;
        background-color: #1E1E1E;
        border-radius: 16px;
        padding: 4px 12px;
        margin-right: 10px;
    ">
        <div style="
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: {color};
            margin-right: 8px;
        "></div>
        <span style="color: {color};">{text}</span>
    </div>
    """, unsafe_allow_html=True)


def themed_container(content_function, border_color="#00CCFF", padding=15):
    """Create a themed container with custom styling.
    
    Args:
        content_function: Function that will be called to render content inside the container
        border_color (str, optional): Border color hex. Defaults to "#00CCFF".
        padding (int, optional): Container padding in pixels. Defaults to 15.
    """
    # Create container with custom styling
    container_id = f"container_{id(content_function)}"
    st.markdown(f"""
    <div id="{container_id}" style="
        background-color: #1E1E1E;
        border: 1px solid {border_color};
        border-radius: 5px;
        padding: {padding}px;
        margin: 10px 0;
    ">
    </div>
    """, unsafe_allow_html=True)
    
    # Use st.container() for content
    with st.container():
        content_function()
    
    # Note: This is a bit hacky as we can't directly style st.container()
    # For production, consider custom component development