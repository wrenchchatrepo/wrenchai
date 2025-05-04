"""Configuration Management Components.

This module provides components for managing application configuration
using Pydantic models for type safety and validation.
"""

import streamlit as st
from typing import Type, Dict, Any, Optional, List, Callable, Union, TypeVar, Generic, get_type_hints
from pydantic import BaseModel, Field, create_model, ValidationError
import yaml
import json
import os
from pathlib import Path

from streamlit_app.components.form_components import model_form
from streamlit_app.components.ui_components import info_card, warning_card, error_card, success_card

T = TypeVar('T', bound=BaseModel)

class ConfigManager(Generic[T]):
    """Manager for configuration based on Pydantic models."""
    
    def __init__(self, 
                config_model: Type[T], 
                config_path: Union[str, Path], 
                default_config: Optional[Dict[str, Any]] = None,
                auto_save: bool = True):
        """
        Initialize the configuration manager.
        
        Args:
            config_model: Pydantic model class for the configuration
            config_path: Path to the configuration file
            default_config: Default configuration values
            auto_save: Whether to automatically save on change
        """
        self.config_model = config_model
        self.config_path = Path(config_path)
        self.default_config = default_config or {}
        self.auto_save = auto_save
        self.current_config = self._load_config()
    
    def _load_config(self) -> T:
        """Load configuration from file or create with defaults."""
        try:
            if self.config_path.exists():
                # Determine file format from extension
                if self.config_path.suffix.lower() == '.yaml' or self.config_path.suffix.lower() == '.yml':
                    with open(self.config_path, 'r') as f:
                        config_dict = yaml.safe_load(f)
                elif self.config_path.suffix.lower() == '.json':
                    with open(self.config_path, 'r') as f:
                        config_dict = json.load(f)
                else:
                    # Default to YAML
                    with open(self.config_path, 'r') as f:
                        config_dict = yaml.safe_load(f)
                
                # Create model instance
                return self.config_model(**config_dict)
            else:
                # Create with defaults
                return self.config_model(**self.default_config)
        except Exception as e:
            st.warning(f"Error loading configuration: {str(e)}. Using defaults.")
            return self.config_model(**self.default_config)
    
    def save_config(self, config: Optional[T] = None) -> bool:
        """Save configuration to file.
        
        Args:
            config: Configuration to save, or current config if None
            
        Returns:
            True if saved successfully, False otherwise
        """
        config_to_save = config or self.current_config
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.config_path.parent, exist_ok=True)
            
            # Determine file format from extension
            if self.config_path.suffix.lower() == '.yaml' or self.config_path.suffix.lower() == '.yml':
                with open(self.config_path, 'w') as f:
                    yaml.dump(config_to_save.model_dump(), f, default_flow_style=False)
            elif self.config_path.suffix.lower() == '.json':
                with open(self.config_path, 'w') as f:
                    json.dump(config_to_save.model_dump(), f, indent=2)
            else:
                # Default to YAML
                with open(self.config_path, 'w') as f:
                    yaml.dump(config_to_save.model_dump(), f, default_flow_style=False)
                    
            self.current_config = config_to_save
            return True
        except Exception as e:
            st.error(f"Error saving configuration: {str(e)}")
            return False
    
    def get_config(self) -> T:
        """Get the current configuration."""
        return self.current_config
    
    def update_config(self, updates: Dict[str, Any]) -> T:
        """Update configuration with new values.
        
        Args:
            updates: Dictionary of configuration updates
            
        Returns:
            Updated configuration
        """
        # Create updated config dict
        updated_dict = self.current_config.model_dump()
        updated_dict.update(updates)
        
        # Create new config instance
        try:
            updated_config = self.config_model(**updated_dict)
            
            # Save if auto_save is enabled
            if self.auto_save:
                self.save_config(updated_config)
                
            self.current_config = updated_config
            return updated_config
        except ValidationError as e:
            st.error(f"Configuration validation error: {str(e)}")
            return self.current_config
    
    def reset_to_defaults(self) -> T:
        """Reset configuration to default values.
        
        Returns:
            Default configuration
        """
        default_config = self.config_model(**self.default_config)
        
        # Save if auto_save is enabled
        if self.auto_save:
            self.save_config(default_config)
            
        self.current_config = default_config
        return default_config


def configuration_editor(config_manager: ConfigManager, title: str = "Configuration") -> Optional[BaseModel]:
    """
    Create a configuration editor UI for a ConfigManager.
    
    Args:
        config_manager: ConfigManager instance
        title: Title for the editor
        
    Returns:
        Updated configuration if saved, None otherwise
    """
    st.subheader(title)
    
    # Get current config
    current_config = config_manager.get_config()
    
    # Create tabs for viewing and editing
    view_tab, edit_tab, reset_tab = st.tabs(["View Configuration", "Edit Configuration", "Reset Configuration"])
    
    # View tab
    with view_tab:
        st.json(current_config.model_dump_json(indent=2))
        
        # Show file path
        st.caption(f"Configuration file: {config_manager.config_path}")
    
    # Edit tab
    with edit_tab:
        # Create a form from the model
        updated_config = model_form(config_manager.config_model, key="config_editor")
        
        if updated_config:
            # Save the updated config
            if config_manager.save_config(updated_config):
                st.success("Configuration saved successfully!")
                return updated_config
            else:
                st.error("Failed to save configuration.")
                return None
    
    # Reset tab
    with reset_tab:
        st.warning("This will reset the configuration to default values.")
        if st.button("Reset to Defaults"):
            default_config = config_manager.reset_to_defaults()
            st.success("Configuration has been reset to defaults.")
            return default_config
    
    return None


def config_section(title: str, description: str, config_form_function: Callable) -> None:
    """Create a collapsible configuration section.
    
    Args:
        title: Section title
        description: Section description
        config_form_function: Function that renders the configuration form
    """
    with st.expander(title, expanded=False):
        st.markdown(description)
        st.markdown("---")
        config_form_function()


def display_config_field(field_name: str, value: Any, field_description: Optional[str] = None):
    """Display a configuration field with label and value.
    
    Args:
        field_name: Name of the field
        value: Value of the field
        field_description: Optional description of the field
    """
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown(f"**{field_name}:**")
    with col2:
        # Format value based on type
        if isinstance(value, bool):
            st.checkbox("Enabled" if value else "Disabled", value=value, disabled=True, key=f"display_{field_name}")
        elif isinstance(value, (list, dict)):
            st.json(value)
        else:
            st.text(str(value))
    
    if field_description:
        st.caption(field_description)


def config_summary(config: BaseModel, title: str = "Configuration Summary"):
    """Display a summary of the configuration.
    
    Args:
        config: Configuration model instance
        title: Title for the summary
    """
    st.subheader(title)
    
    # Get model fields and their descriptions
    model_fields = config.model_fields
    
    # Display each field
    for field_name, field_info in model_fields.items():
        field_description = field_info.description
        field_value = getattr(config, field_name)
        
        display_config_field(field_name, field_value, field_description)
        
        # Add a separator
        st.markdown("---")