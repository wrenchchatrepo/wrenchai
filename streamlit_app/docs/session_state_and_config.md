# WrenchAI Streamlit Application - Session State and Configuration Management

## Overview

This module provides comprehensive utilities for managing application state, configuration, and user preferences in the WrenchAI Streamlit application. It implements robust mechanisms to maintain state between Streamlit reruns and across different pages of the application.

## Key Components

### Session State Management

The `session_state.py` module provides utilities for managing Streamlit's session state in a standardized way:

- `StateKey`: Enum of standardized session state keys to avoid string keys
- `StateContainer`: Generic container for session state values with default handling
- `PlaybookExecutionState`: Enum of execution states for playbooks (idle, running, completed, etc.)
- `PlaybookSession`: Class for managing playbook execution state and history
- Various utility functions for getting, setting, and manipulating session state

### Configuration Management

The `config_manager.py` module handles loading, validating, and providing application configuration:

- `ApplicationConfig`: Pydantic model for the complete application configuration
- Configuration models for different aspects (API, UI, Logging, Cache, Session, Playbooks, etc.)
- Support for loading configuration from YAML files, environment variables, and defaults
- Config validation and type safety through Pydantic models

### User Preferences

The `user_preferences.py` module manages user-specific preferences and API connection state:

- `UserPreferences`: Model for user UI and feature preferences
- `ApiConnectionState`: Tracks API connection status, features, and metrics
- `ApiCredentials`: Securely manages API authentication and credentials
- Functions for loading/saving preferences to disk for persistence

## Usage Examples

### Session State

```python
from streamlit_app.utils.session_state import get_state, set_state, StateKey

# Get a value with default fallback
playbook_id = get_state(StateKey.SELECTED_PLAYBOOK, default=None)

# Set a value
set_state(StateKey.EXECUTION_STATE, "running")

# Use the PlaybookSession for managing execution
from streamlit_app.utils.session_state import PlaybookSession, PlaybookExecutionState

playbook_session = PlaybookSession()
playbook_session.start_execution("portfolio-generator", {"name": "My Portfolio"})
playbook_session.update_execution_state(PlaybookExecutionState.RUNNING)
```

### Configuration

```python
from streamlit_app.utils.config_manager import get_config

# Load configuration with defaults
config = get_config()

# Access configuration
api_url = config.api.base_url
page_title = config.ui.page_title
docusaurus_themes = config.docusaurus.themes
```

### User Preferences

```python
from streamlit_app.utils.user_preferences import get_user_preferences, update_preference

# Get user preferences
prefs = get_user_preferences()

# Update a single preference
update_preference("theme", "dark")

# Check if a feature is enabled
if prefs.experimental_features:
    # Enable experimental features
    pass
```

### API Connection State

```python
from streamlit_app.utils.user_preferences import get_api_state, update_api_state

# Get API connection state
api_state = get_api_state()

# Check connection status
if api_state.connected:
    # API is connected
    pass

# Update connection status
api_state.update_connection_status(connected=True, status_code=200)
update_api_state(api_state)
```

## Implementation Details

### State Persistence

To address Streamlit's state persistence challenges, this implementation:

1. Uses standardized keys to avoid collisions and typos
2. Provides type-safe containers with default values
3. Automatically initializes required state on application start
4. Tracks state modification times for cache invalidation

### Configuration Layers

Configuration is loaded in the following order, with later sources taking precedence:

1. Default values defined in the Pydantic models
2. Values from config.yaml file
3. Environment variables (prefixed with WRENCHAI_)

This provides flexibility while ensuring configuration always has valid values.

### Security Considerations

For credential management:

1. Passwords are never saved to disk in plain text
2. Token expiration is properly tracked and validated
3. Credentials can be selectively saved based on user preferences
4. Secure methods for authentication state management

## Best Practices

1. Always use the `StateKey` enum when accessing session state
2. Use the state management functions (`get_state`, `set_state`) instead of directly accessing `st.session_state`
3. Initialize all required state early in the application lifecycle
4. Use Pydantic models for type validation and safety
5. Keep UI state separate from application data