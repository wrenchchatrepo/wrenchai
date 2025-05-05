## 6. Implementation Plan

### 6.1 Theme Implementation

```python
# utils/theme.py
"""Custom theme configuration for Wrench AI Toolbox."""

import streamlit as st

# Midnight UI color palette
MIDNIGHT_UI = {
    "primary": "#1B03A3",        # Neon Blue
    "secondary": "#9D00FF",      # Neon Purple
    "accent": "#FF10F0",         # Neon Pink
    "error": "#FF3131",          # Neon Red
    "success": "#39FF14",        # Neon Green
    "warning": "#E9FF32",        # Neon Yellow
    "info": "#00FFFF",           # Neon Cyan
    "primary_foreground": "#E3E3E3",      # Soft White
    "secondary_foreground": "#A3A3A3",    # Stone Grey
    "disabled_foreground": "#606770",     # Neutral Grey
    "primary_background": "#010B13",      # Rich Black
    "secondary_background": "#0F1111",    # Charcoal Black
    "surface_background": "#1A1A1A",      # Midnight Black
    "overlay": "#121212AA",              # Transparent Dark
}

def apply_midnight_theme():
    """Apply the Midnight UI theme to the Streamlit app."""
    # Configure the theme using Streamlit's theming
    st.markdown(f"""
    <style>
        /* Base theme - dark mode */
        :root {{
            --background-color: {MIDNIGHT_UI["primary_background"]};
            --secondary-background-color: {MIDNIGHT_UI["secondary_background"]};
            --surface-background-color: {MIDNIGHT_UI["surface_background"]};
            --primary-color: {MIDNIGHT_UI["primary"]};
            --secondary-color: {MIDNIGHT_UI["secondary"]};
            --accent-color: {MIDNIGHT_UI["accent"]};
            --text-color: {MIDNIGHT_UI["primary_foreground"]};
            --secondary-text-color: {MIDNIGHT_UI["secondary_foreground"]};
            --disabled-text-color: {MIDNIGHT_UI["disabled_foreground"]};
            --error-color: {MIDNIGHT_UI["error"]};
            --success-color: {MIDNIGHT_UI["success"]};
            --warning-color: {MIDNIGHT_UI["warning"]};
            --info-color: {MIDNIGHT_UI["info"]};
        }}
        
        /* Apply theme to Streamlit elements */
        .stApp {{
            background-color: var(--background-color);
            color: var(--text-color);
        }}
        
        .stSidebar .sidebar-content {{
            background-color: var(--secondary-background-color);
        }}
        
        /* Buttons */
        .stButton>button {{
            background-color: var(--primary-color);
            color: var(--primary-foreground);
            border: none;
            border-radius: 4px;
            transition: all 0.2s ease-in-out;
        }}
        
        .stButton>button:hover {{
            background-color: var(--secondary-color);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }}
        
        /* Cards and containers */
        .stCard {{
            background-color: var(--surface-background-color);
            border: 1px solid var(--accent-color);
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
            transition: all 0.2s ease-in-out;
        }}
        
        .stCard:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.4);
        }}
        
        /* Text styling */
        h1, h2, h3 {{
            color: var(--primary-foreground);
            font-weight: 600;
        }}
        
        h1 {{
            border-bottom: 2px solid var(--accent-color);
            padding-bottom: 0.5rem;
        }}
        
        /* Link styling */
        a {{
            color: var(--info-color);
            text-decoration: none;
            transition: all 0.2s ease-in-out;
        }}
        
        a:hover {{
            color: var(--accent-color);
            text-decoration: underline;
        }}
        
        /* Notification colors */
        .success-message {{
            background-color: var(--success-color);
            color: var(--primary-background);
            padding: 0.5rem;
            border-radius: 4px;
        }}
        
        .error-message {{
            background-color: var(--error-color);
            color: var(--primary-foreground);
            padding: 0.5rem;
            border-radius: 4px;
        }}
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {{
            width: 10px;
            height: 10px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: var(--surface-background-color);
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: var(--secondary-color);
            border-radius: 5px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: var(--accent-color);
        }}
    </style>
    """, unsafe_allow_html=True)
```