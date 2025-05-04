"""Settings page for WrenchAI application."""

import streamlit as st
from typing import Dict, List, Any, Optional
import json

# Import utility functions
from wrenchai.streamlit_app.utils.session_state import StateKey, get_state, set_state, clear_all_state
from wrenchai.streamlit_app.utils.logger import get_logger
from wrenchai.streamlit_app.utils.ui_components import status_indicator, display_error, display_success
from wrenchai.streamlit_app.components import section_container

# Setup logger
logger = get_logger(__name__)

st.set_page_config(
    page_title="WrenchAI - Settings",
    page_icon="ud83dudd27",
    layout="wide",
)

def main():
    """Main entry point for the settings page."""
    st.title("u2699ufe0f Settings")
    st.markdown("Configure your WrenchAI application settings.")
    
    # Create tabs for different settings categories
    tab1, tab2, tab3, tab4 = st.tabs(["General", "API", "Appearance", "Advanced"])
    
    with tab1:
        render_general_settings()
    
    with tab2:
        render_api_settings()
    
    with tab3:
        render_appearance_settings()
    
    with tab4:
        render_advanced_settings()

def render_general_settings():
    """Render general application settings."""
    st.header("General Settings")
    
    # User Preferences
    with section_container("User Preferences"):
        # Get current preferences
        user_prefs = get_state(StateKey.USER_PREFERENCES, {})
        
        # Default startup page
        startup_pages = ["Home", "Playbooks", "Portfolio Generator", "Documentation"]
        selected_startup = st.selectbox(
            "Default Startup Page",
            startup_pages,
            index=startup_pages.index(user_prefs.get("default_page", "Home")) if user_prefs.get("default_page") in startup_pages else 0,
            key="default_page"
        )
        
        # Notification settings
        st.subheader("Notifications")
        
        show_notifications = st.checkbox(
            "Show Desktop Notifications",
            value=user_prefs.get("show_notifications", True),
            key="show_notifications"
        )
        
        notification_level = st.radio(
            "Notification Level",
            ["All", "Important Only", "None"],
            index=["All", "Important Only", "None"].index(user_prefs.get("notification_level", "Important Only")),
            key="notification_level"
        )
        
        # Save buttons
        if st.button("Save General Settings"):
            user_prefs.update({
                "default_page": selected_startup,
                "show_notifications": show_notifications,
                "notification_level": notification_level
            })
            set_state(StateKey.USER_PREFERENCES, user_prefs)
            st.success("General settings saved successfully!")
    
    # File Locations
    with section_container("File Locations"):
        # Get current file paths
        file_paths = user_prefs.get("file_paths", {
            "projects_dir": "~/wrenchai/projects",
            "output_dir": "~/wrenchai/output",
            "templates_dir": "~/wrenchai/templates"
        })
        
        # Project directory
        projects_dir = st.text_input(
            "Projects Directory",
            value=file_paths.get("projects_dir", "~/wrenchai/projects"),
            key="projects_dir"
        )
        
        # Output directory
        output_dir = st.text_input(
            "Output Directory",
            value=file_paths.get("output_dir", "~/wrenchai/output"),
            key="output_dir"
        )
        
        # Templates directory
        templates_dir = st.text_input(
            "Templates Directory",
            value=file_paths.get("templates_dir", "~/wrenchai/templates"),
            key="templates_dir"
        )
        
        # Save buttons
        if st.button("Save File Locations"):
            file_paths.update({
                "projects_dir": projects_dir,
                "output_dir": output_dir,
                "templates_dir": templates_dir
            })
            user_prefs["file_paths"] = file_paths
            set_state(StateKey.USER_PREFERENCES, user_prefs)
            st.success("File locations saved successfully!")

def render_api_settings():
    """Render API connection settings."""
    st.header("API Settings")
    
    # API Connection
    with section_container("API Connection"):
        # Get current API config
        config = get_state(StateKey.CONFIG)
        api_config = config.api if hasattr(config, "api") else {}
        
        # API URL
        api_url = st.text_input(
            "API URL",
            value=api_config.get("url", "https://api.wrenchai.com/v1"),
            key="api_url"
        )
        
        # API Key
        api_key = st.text_input(
            "API Key",
            value=get_state(StateKey.AUTH_TOKEN, ""),
            type="password",
            key="api_key"
        )
        
        # Connection timeout
        timeout = st.number_input(
            "Connection Timeout (seconds)",
            min_value=1,
            max_value=60,
            value=api_config.get("timeout", 30),
            key="timeout"
        )
        
        # Test connection button
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("Test Connection"):
                # Simulate API connection test
                st.info("Testing API connection...")
                # This would normally make an actual API call
                import time
                time.sleep(1)  # Simulate network delay
                set_state(StateKey.API_STATUS, {"connected": True, "ping_latency": 123})
                st.success("API connection successful!")
        
        # Save button
        if st.button("Save API Settings"):
            # Update API configuration
            if hasattr(config, "api"):
                config.api.url = api_url
                config.api.timeout = timeout
            
            # Update session state
            set_state(StateKey.CONFIG, config)
            set_state(StateKey.AUTH_TOKEN, api_key)
            
            st.success("API settings saved successfully!")
    
    # Webhooks
    with section_container("Webhooks"):
        st.markdown("Configure webhooks to receive notifications about events.")
        
        # Get current webhooks
        webhooks = get_state("webhooks", [])
        
        # Display existing webhooks
        if webhooks:
            st.subheader("Configured Webhooks")
            for i, webhook in enumerate(webhooks):
                with st.expander(f"Webhook {i+1}: {webhook.get('name', 'Unnamed')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        webhooks[i]['name'] = st.text_input(
                            "Name",
                            value=webhook.get("name", ""),
                            key=f"webhook_{i}_name"
                        )
                    with col2:
                        webhooks[i]['url'] = st.text_input(
                            "URL",
                            value=webhook.get("url", ""),
                            key=f"webhook_{i}_url"
                        )
                    
                    webhooks[i]['events'] = st.multiselect(
                        "Events",
                        ["playbook.started", "playbook.completed", "playbook.failed", "portfolio.generated"],
                        default=webhook.get("events", []),
                        key=f"webhook_{i}_events"
                    )
                    
                    webhooks[i]['active'] = st.checkbox(
                        "Active",
                        value=webhook.get("active", True),
                        key=f"webhook_{i}_active"
                    )
                    
                    if st.button("Remove", key=f"remove_webhook_{i}"):
                        webhooks.pop(i)
                        set_state("webhooks", webhooks)
                        st.rerun()
        
        # Add new webhook
        st.subheader("Add New Webhook")
        with st.form("new_webhook_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Name", key="new_webhook_name")
            with col2:
                new_url = st.text_input("URL", key="new_webhook_url")
            
            new_events = st.multiselect(
                "Events",
                ["playbook.started", "playbook.completed", "playbook.failed", "portfolio.generated"],
                key="new_webhook_events"
            )
            
            new_active = st.checkbox("Active", value=True, key="new_webhook_active")
            
            submitted = st.form_submit_button("Add Webhook")
            if submitted and new_name and new_url:
                webhooks.append({
                    "name": new_name,
                    "url": new_url,
                    "events": new_events,
                    "active": new_active
                })
                set_state("webhooks", webhooks)
                st.rerun()

def render_appearance_settings():
    """Render appearance and UI settings."""
    st.header("Appearance Settings")
    
    # Theme Settings
    with section_container("Theme Settings"):
        # Get current theme
        current_theme = get_state(StateKey.THEME, "light")
        
        # Theme selection
        theme_mode = st.radio(
            "Theme Mode",
            ["Light", "Dark", "System"],
            index=["Light", "Dark", "System"].index(current_theme.title()) if current_theme.title() in ["Light", "Dark", "System"] else 0,
            key="theme_mode",
            horizontal=True
        )
        
        # Color scheme
        color_schemes = ["Blue", "Green", "Purple", "Orange", "Red"]
        color_scheme = st.selectbox(
            "Color Accent",
            color_schemes,
            index=0,
            key="color_scheme"
        )
        
        # Font selection
        fonts = ["System Default", "Sans-serif", "Serif", "Monospace"]
        font = st.selectbox(
            "Font Family",
            fonts,
            index=0,
            key="font_family"
        )
        
        # Font size
        font_size = st.slider(
            "Font Size",
            min_value=12,
            max_value=20,
            value=14,
            key="font_size"
        )
        
        # Apply button
        if st.button("Apply Theme Settings"):
            # Update theme in session state
            set_state(StateKey.THEME, theme_mode.lower())
            set_state("color_scheme", color_scheme.lower())
            set_state("font_family", font.lower())
            set_state("font_size", font_size)
            
            st.success("Theme settings applied! Some changes may require a page refresh.")
    
    # Layout Settings
    with section_container("Layout Settings"):
        # Sidebar behavior
        sidebar_collapsed = st.checkbox(
            "Start with Sidebar Collapsed",
            value=not get_state(StateKey.SIDEBAR_EXPANDED, True),
            key="sidebar_collapsed"
        )
        
        # Content width
        content_width = st.radio(
            "Content Width",
            ["Wide", "Medium", "Narrow"],
            index=0,
            key="content_width"
        )
        
        # Show breadcrumbs
        show_breadcrumbs = st.checkbox(
            "Show Breadcrumbs",
            value=get_state("show_breadcrumbs", True),
            key="show_breadcrumbs"
        )
        
        # Save layout settings
        if st.button("Save Layout Settings"):
            # Update session state
            set_state(StateKey.SIDEBAR_EXPANDED, not sidebar_collapsed)
            set_state("content_width", content_width.lower())
            set_state("show_breadcrumbs", show_breadcrumbs)
            
            st.success("Layout settings saved!")

def render_advanced_settings():
    """Render advanced application settings."""
    st.header("Advanced Settings")
    
    # Debug Mode
    with section_container("Debug Settings"):
        debug_mode = st.checkbox(
            "Enable Debug Mode",
            value=get_state(StateKey.DEBUG_MODE, False),
            key="debug_mode_setting"
        )
        
        log_level = st.selectbox(
            "Log Level",
            ["ERROR", "WARNING", "INFO", "DEBUG"],
            index=0,
            key="log_level"
        )
        
        # Apply debug settings
        if st.button("Apply Debug Settings"):
            set_state(StateKey.DEBUG_MODE, debug_mode)
            set_state("log_level", log_level)
            st.success("Debug settings applied!")
            
            # Update logger configuration (in real app)
            logger.info(f"Debug mode: {debug_mode}, Log level: {log_level}")
    
    # Cache Management
    with section_container("Cache Management"):
        st.markdown("Manage application cache and temporary files.")
        
        # Display cache status
        st.info("Cache is used to improve application performance.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Clear Session Cache"):
                # Clear specific cache keys but keep essential app state
                keys_to_keep = [StateKey.AUTH_TOKEN.value, StateKey.USER_INFO.value, StateKey.CONFIG.value]
                for key in list(st.session_state.keys()):
                    if key not in keys_to_keep and not key.startswith("_") and key != "debug_mode_setting":
                        del st.session_state[key]
                
                st.success("Session cache cleared!")
        
        with col2:
            if st.button("Clear API Cache"):
                # This would clear API cache in a real app
                st.success("API cache cleared!")
        
        with col3:
            if st.button("Clear All Cache", type="primary"):
                # Reset session state completely
                clear_all_state()
                st.success("All cache cleared! You will be redirected to the home page.")
                st.rerun()
    
    # Export/Import Settings
    with section_container("Export/Import Settings"):
        st.markdown("Export your current settings or import from a file.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Export Settings"):
                # Prepare settings for export
                export_data = {
                    "user_preferences": get_state(StateKey.USER_PREFERENCES, {}),
                    "theme": get_state(StateKey.THEME, "light"),
                    "color_scheme": get_state("color_scheme", "blue"),
                    "font_family": get_state("font_family", "system default"),
                    "font_size": get_state("font_size", 14),
                    "sidebar_expanded": get_state(StateKey.SIDEBAR_EXPANDED, True),
                    "content_width": get_state("content_width", "wide"),
                    "show_breadcrumbs": get_state("show_breadcrumbs", True),
                    "debug_mode": get_state(StateKey.DEBUG_MODE, False),
                    "log_level": get_state("log_level", "ERROR")
                }
                
                # Convert to JSON
                export_json = json.dumps(export_data, indent=2)
                
                # Display download link (in a real app, this would be a file download)
                st.code(export_json, language="json")
                st.info("Copy this JSON to save your settings.")
        
        with col2:
            # Import settings
            import_json = st.text_area(
                "Import Settings (Paste JSON)",
                height=150,
                key="import_settings"
            )
            
            if st.button("Import Settings") and import_json:
                try:
                    # Parse JSON
                    import_data = json.loads(import_json)
                    
                    # Apply imported settings
                    for key, value in import_data.items():
                        if key == "user_preferences":
                            set_state(StateKey.USER_PREFERENCES, value)
                        elif key == "theme":
                            set_state(StateKey.THEME, value)
                        elif key == "sidebar_expanded":
                            set_state(StateKey.SIDEBAR_EXPANDED, value)
                        elif key == "debug_mode":
                            set_state(StateKey.DEBUG_MODE, value)
                        else:
                            set_state(key, value)
                    
                    st.success("Settings imported successfully!")
                except json.JSONDecodeError:
                    st.error("Invalid JSON format. Please check your input.")
                except Exception as e:
                    st.error(f"Error importing settings: {str(e)}")
    
    # System Information
    with section_container("System Information"):
        st.markdown("### Application Information")
        
        # Get configuration
        config = get_state(StateKey.CONFIG)
        
        # Display app info
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Application Version:** v1.0.0")
            st.markdown("**Python Version:** 3.8.10")
        with col2:
            st.markdown(f"**API Version:** {config.api.version if hasattr(config, 'api') and hasattr(config.api, 'version') else 'Unknown'}")
            st.markdown("**Last Updated:** 2023-04-30")
        
        # Display system resources
        st.markdown("### System Resources")
        
        # In a real app, these would be actual metrics
        cpu_usage = 24  # Simulated value
        memory_usage = 42  # Simulated value
        disk_usage = 37  # Simulated value
        
        cols = st.columns(3)
        with cols[0]:
            st.metric("CPU Usage", f"{cpu_usage}%")
        with cols[1]:
            st.metric("Memory Usage", f"{memory_usage}%")
        with cols[2]:
            st.metric("Disk Usage", f"{disk_usage}%")

if __name__ == "__main__":
    main()