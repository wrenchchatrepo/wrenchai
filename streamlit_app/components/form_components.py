"""Pydantic Form Components.

This module provides components for creating forms from Pydantic models
using streamlit-pydantic library.
"""

import streamlit as st
from typing import Type, Dict, Any, Optional, List, Callable, Union, TypeVar, Generic, get_type_hints
from pydantic import BaseModel, Field, create_model, ValidationError
import inspect
from enum import Enum
from datetime import datetime, date
from streamlit_pydantic import st_pydantic

T = TypeVar('T', bound=BaseModel)


def model_form(model_class: Type[T], key: Optional[str] = None) -> Optional[T]:
    """Create a form from a Pydantic model.
    
    Args:
        model_class: Pydantic model class to create a form for
        key: Optional key for the form
        
    Returns:
        Instance of the model if form is submitted and valid, None otherwise
    """
    return st_pydantic(
        model_class=model_class,
        key=key or f"form_{model_class.__name__}"
    )


def dynamic_model_form(fields: Dict[str, Dict[str, Any]], 
                     title: str = "Form", 
                     model_name: str = "DynamicModel") -> Optional[BaseModel]:
    """Create a form from a dictionary of field definitions.
    
    Args:
        fields: Dictionary mapping field names to field properties
            Each field dict should have:
            - type: Python type (str, int, float, bool, etc.)
            - title: Display title for the field
            - description: Optional field description
            - default: Optional default value
            - constraints: Optional dict of constraints (min, max, regex, etc.)
        title: Title for the form
        model_name: Name for the dynamically created model
        
    Returns:
        Instance of the dynamic model if form is submitted and valid, None otherwise
    """
    # Convert field definitions to Pydantic Field objects
    field_definitions = {}
    
    for field_name, field_props in fields.items():
        field_type = field_props.get('type', str)
        field_title = field_props.get('title', field_name)
        field_description = field_props.get('description', '')
        field_default = field_props.get('default', ...)
        constraints = field_props.get('constraints', {})
        
        # Create Field with all properties
        field_obj = Field(
            default=field_default,
            title=field_title,
            description=field_description,
            **constraints
        )
        
        field_definitions[field_name] = (field_type, field_obj)
    
    # Create dynamic model
    dynamic_model = create_model(model_name, **field_definitions)
    
    # Create form for the model
    st.subheader(title)
    return st_pydantic(
        model_class=dynamic_model,
        key=f"form_{model_name}"
    )


class FormData(Dict[str, Any]):
    """Custom dictionary class for storing form data with helpers for validation."""
    
    def to_model(self, model_class: Type[BaseModel]) -> BaseModel:
        """Convert form data to a Pydantic model instance.
        
        Args:
            model_class: Pydantic model class to convert to
            
        Returns:
            Instance of the model
            
        Raises:
            ValidationError: If the data is invalid
        """
        return model_class(**self)


def custom_form(fields: List[Dict[str, Any]], key: str = None, on_submit: Callable = None) -> FormData:
    """Create a custom form with various input types.
    
    Args:
        fields: List of field definitions, each containing:
            - name: Field name
            - type: Field type ('text', 'number', 'boolean', 'select', etc.)
            - label: Display label
            - help: Optional help text
            - options: Optional list of options (for select, multiselect)
            - validation: Optional validation function
        key: Optional key for the form
        on_submit: Optional callback function when form is submitted
        
    Returns:
        Dictionary of form values
    """
    form_key = key or f"form_{id(fields)}"
    
    # Initialize form values in session state
    if f"{form_key}_values" not in st.session_state:
        st.session_state[f"{form_key}_values"] = {}
        
        # Set default values
        for field in fields:
            if 'default' in field:
                st.session_state[f"{form_key}_values"][field['name']] = field['default']
    
    # Create form
    with st.form(form_key):
        # Form fields
        for field in fields:
            field_name = field['name']
            field_type = field.get('type', 'text')
            label = field.get('label', field_name)
            help_text = field.get('help', None)
            required = field.get('required', False)
            
            # Add required indicator to label
            if required and not label.endswith('*'):
                label = f"{label} *"
            
            # Different input types
            if field_type == 'text':
                st.text_input(
                    label, 
                    key=f"{form_key}_{field_name}",
                    help=help_text,
                    on_change=lambda: update_form_value(form_key, field_name, f"{form_key}_{field_name}")
                )
            elif field_type == 'textarea':
                st.text_area(
                    label, 
                    key=f"{form_key}_{field_name}",
                    help=help_text,
                    on_change=lambda: update_form_value(form_key, field_name, f"{form_key}_{field_name}")
                )
            elif field_type == 'number':
                st.number_input(
                    label,
                    min_value=field.get('min', None),
                    max_value=field.get('max', None),
                    step=field.get('step', None),
                    key=f"{form_key}_{field_name}",
                    help=help_text,
                    on_change=lambda: update_form_value(form_key, field_name, f"{form_key}_{field_name}")
                )
            elif field_type == 'boolean':
                st.checkbox(
                    label,
                    key=f"{form_key}_{field_name}",
                    help=help_text,
                    on_change=lambda: update_form_value(form_key, field_name, f"{form_key}_{field_name}")
                )
            elif field_type == 'select':
                options = field.get('options', [])
                st.selectbox(
                    label,
                    options=options,
                    key=f"{form_key}_{field_name}",
                    help=help_text,
                    on_change=lambda: update_form_value(form_key, field_name, f"{form_key}_{field_name}")
                )
            elif field_type == 'multiselect':
                options = field.get('options', [])
                st.multiselect(
                    label,
                    options=options,
                    key=f"{form_key}_{field_name}",
                    help=help_text,
                    on_change=lambda: update_form_value(form_key, field_name, f"{form_key}_{field_name}")
                )
            elif field_type == 'date':
                st.date_input(
                    label,
                    key=f"{form_key}_{field_name}",
                    help=help_text,
                    on_change=lambda: update_form_value(form_key, field_name, f"{form_key}_{field_name}")
                )
            elif field_type == 'time':
                st.time_input(
                    label,
                    key=f"{form_key}_{field_name}",
                    help=help_text,
                    on_change=lambda: update_form_value(form_key, field_name, f"{form_key}_{field_name}")
                )
            elif field_type == 'file':
                st.file_uploader(
                    label,
                    type=field.get('accept', None),
                    key=f"{form_key}_{field_name}",
                    help=help_text,
                    on_change=lambda: update_form_value(form_key, field_name, f"{form_key}_{field_name}")
                )
        
        # Submit button
        submit_label = "Submit"
        if 'submit_label' in st.session_state:
            submit_label = st.session_state['submit_label']
            
        submitted = st.form_submit_button(submit_label)
        
        # Update all values on submit
        if submitted:
            for field in fields:
                field_name = field['name']
                update_form_value(form_key, field_name, f"{form_key}_{field_name}")
            
            # Run validation
            is_valid = True
            for field in fields:
                if 'validation' in field and callable(field['validation']):
                    field_name = field['name']
                    field_value = st.session_state[f"{form_key}_values"].get(field_name)
                    validation_result = field['validation'](field_value)
                    
                    if validation_result is not True:
                        is_valid = False
                        error_msg = validation_result if isinstance(validation_result, str) else "Invalid value"
                        st.error(f"{field.get('label', field_name)}: {error_msg}")
            
            # Call on_submit callback if validation passes
            if is_valid and on_submit is not None:
                on_submit(st.session_state[f"{form_key}_values"])
    
    # Return form values
    return FormData(st.session_state[f"{form_key}_values"])


def update_form_value(form_key, field_name, input_key):
    """Update a form value in session state."""
    st.session_state[f"{form_key}_values"][field_name] = st.session_state[input_key]


class FormBuilder:
    """Builder for creating forms with validation and custom rendering."""
    
    def __init__(self, title: str = "Form"):
        """Initialize FormBuilder.
        
        Args:
            title: Title for the form
        """
        self.title = title
        self.fields = []
        self.form_key = f"form_{id(self)}"
        self.on_submit_callback = None
        self.validation_rules = {}
    
    def add_text(self, name: str, label: str, required: bool = False, help: str = None, default: str = ""):
        """Add a text input field."""
        self.fields.append({
            'name': name,
            'type': 'text',
            'label': label,
            'required': required,
            'help': help,
            'default': default
        })
        return self
    
    def add_textarea(self, name: str, label: str, required: bool = False, help: str = None, default: str = ""):
        """Add a text area field."""
        self.fields.append({
            'name': name,
            'type': 'textarea',
            'label': label,
            'required': required,
            'help': help,
            'default': default
        })
        return self
    
    def add_number(self, name: str, label: str, min: Optional[float] = None, max: Optional[float] = None, 
                  step: Optional[float] = None, required: bool = False, help: str = None, default: Optional[float] = None):
        """Add a number input field."""
        self.fields.append({
            'name': name,
            'type': 'number',
            'label': label,
            'min': min,
            'max': max,
            'step': step,
            'required': required,
            'help': help,
            'default': default
        })
        return self
    
    def add_checkbox(self, name: str, label: str, help: str = None, default: bool = False):
        """Add a checkbox field."""
        self.fields.append({
            'name': name,
            'type': 'boolean',
            'label': label,
            'help': help,
            'default': default
        })
        return self
    
    def add_select(self, name: str, label: str, options: List[Any], required: bool = False, 
                  help: str = None, default: Optional[Any] = None):
        """Add a select dropdown field."""
        self.fields.append({
            'name': name,
            'type': 'select',
            'label': label,
            'options': options,
            'required': required,
            'help': help,
            'default': default
        })
        return self
    
    def add_multiselect(self, name: str, label: str, options: List[Any], required: bool = False, 
                       help: str = None, default: Optional[List[Any]] = None):
        """Add a multi-select field."""
        self.fields.append({
            'name': name,
            'type': 'multiselect',
            'label': label,
            'options': options,
            'required': required,
            'help': help,
            'default': default or []
        })
        return self
    
    def add_date(self, name: str, label: str, required: bool = False, help: str = None, default: Optional[date] = None):
        """Add a date input field."""
        self.fields.append({
            'name': name,
            'type': 'date',
            'label': label,
            'required': required,
            'help': help,
            'default': default
        })
        return self
    
    def add_file(self, name: str, label: str, accept: Optional[List[str]] = None, 
                required: bool = False, help: str = None):
        """Add a file upload field."""
        self.fields.append({
            'name': name,
            'type': 'file',
            'label': label,
            'accept': accept,
            'required': required,
            'help': help
        })
        return self
    
    def add_validation(self, field_name: str, validation_func: Callable):
        """Add a validation function for a field.
        
        The validation function should return True if valid, or an error message if invalid.
        """
        # Find the field
        for field in self.fields:
            if field['name'] == field_name:
                field['validation'] = validation_func
                break
        return self
    
    def on_submit(self, callback: Callable):
        """Set callback function to be called when form is submitted and validated."""
        self.on_submit_callback = callback
        return self
    
    def build(self) -> FormData:
        """Build and render the form."""
        # Add default validation for required fields
        for field in self.fields:
            if field.get('required', False) and 'validation' not in field:
                field_name = field['name']
                field_label = field.get('label', field_name)
                
                def required_validator(value, field_label=field_label):
                    if value is None or value == "" or (isinstance(value, (list, dict)) and len(value) == 0):
                        return f"{field_label} is required"
                    return True
                
                field['validation'] = required_validator
        
        # Create the title
        st.subheader(self.title)
        
        # Build and render the form
        return custom_form(
            fields=self.fields,
            key=self.form_key,
            on_submit=self.on_submit_callback
        )