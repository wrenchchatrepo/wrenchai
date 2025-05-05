"""
Utilities Package for WrenchAI Streamlit Application.

This package provides various utility modules for the application, including
configuration management, session state handling, logging, and initialization.
"""

# Import key components for easier access
from streamlit_app.utils.config_manager import (
    get_config, 
    get_config_manager,
    ApplicationConfig, 
    ApiConfig,
    UiConfig
)

from streamlit_app.utils.session_state import (
    initialize_session_state,
    get_state,
    set_state,
    delete_state,
    clear_all_state,
    with_state_change_tracking,
    StateKey,
    StateContainer,
    show_messages,
    set_error,
    set_success,
    set_info,
    set_warning
)

from streamlit_app.utils.user_preferences import (
    initialize_user_preferences,
    get_user_preferences,
    update_user_preferences,
    update_preference,
    initialize_api_state,
    get_api_state,
    update_api_state,
    initialize_api_credentials,
    get_api_credentials,
    update_api_credentials,
    clear_api_credentials,
    apply_user_preferences,
    UserPreferences,
    ApiConnectionState,
    ApiCredentials,
    ThemeOption,
    LayoutType
)

from streamlit_app.utils.logger import (
    configure_logging,
    get_logger,
    log_with_context,
    format_exception,
    StreamlitLogHandler,
    streamlit_log_handler
)

from streamlit_app.utils.initializer import (
    initialize_app,
    display_messages,
    AppInitializer
)