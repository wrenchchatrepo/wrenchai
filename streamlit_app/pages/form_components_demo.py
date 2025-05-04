"""Demo of Form Components for WrenchAI.

This file demonstrates how to use the form components to create UI forms based on Pydantic models.
"""

import streamlit as st
from typing import List, Optional
from enum import Enum
from datetime import date
from pydantic import BaseModel, Field, validator

from streamlit_app.components.midnight_theme import apply_midnight_theme
from streamlit_app.components.form_components import (
    model_form, dynamic_model_form, custom_form, FormBuilder
)

# Apply the Midnight UI theme
apply_midnight_theme()

# Define Pydantic models for the forms
class ProjectType(str, Enum):
    WEB = "web"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    API = "api"
    OTHER = "other"

class LanguageFramework(BaseModel):
    language: str = Field(..., description="Programming language")
    framework: Optional[str] = Field(None, description="Framework or library")
    version: str = Field(..., description="Version number")

class ProjectConfig(BaseModel):
    name: str = Field(..., title="Project Name", description="Name of the project", min_length=3, max_length=50)
    description: str = Field(..., title="Description", description="Brief description of the project")
    project_type: ProjectType = Field(ProjectType.WEB, title="Project Type", description="Type of project")
    start_date: date = Field(default_factory=date.today, title="Start Date", description="Project start date")
    technologies: List[LanguageFramework] = Field([], title="Technologies", description="Languages and frameworks used")
    is_public: bool = Field(False, title="Public Repository", description="Whether the project is public")
    
    @validator('name')
    def name_must_be_valid(cls, v):
        if ' ' not in v:
            return v
        raise ValueError("Project name should not contain spaces")

def main():
    """Main function for the form components demo."""
    st.title("Form Components Demo")
    
    st.markdown("""
    This demo shows how to create forms using Pydantic models with our form components.
    These components make it easy to create forms with validation, custom rendering, and more.
    """)
    
    # Create tabs for different form examples
    tab1, tab2, tab3, tab4 = st.tabs(["Pydantic Model Form", "Dynamic Form", "Custom Form", "Form Builder"])
    
    # Tab 1: Pydantic Model Form
    with tab1:
        st.header("Pydantic Model Form")
        st.markdown("""
        This form is generated automatically from a Pydantic model. 
        It handles validation, field types, and nested models automatically.
        """)
        
        # Create the form using model_form
        project = model_form(ProjectConfig)
        
        # Display the result when submitted
        if project:
            st.success("Form submitted successfully!")
            st.json(project.model_dump_json(indent=2))
    
    # Tab 2: Dynamic Form
    with tab2:
        st.header("Dynamic Form")
        st.markdown("""
        This form is created dynamically from a dictionary of field definitions.
        It's useful when you don't have a predefined Pydantic model.
        """)
        
        # Define dynamic form fields
        fields = {
            "api_key": {
                "type": str,
                "title": "API Key",
                "description": "Your authentication key",
                "default": ""
            },
            "max_tokens": {
                "type": int,
                "title": "Max Tokens",
                "description": "Maximum number of tokens to generate",
                "default": 1000,
                "constraints": {"ge": 1, "le": 4000}
            },
            "temperature": {
                "type": float,
                "title": "Temperature",
                "description": "Sampling temperature",
                "default": 0.7,
                "constraints": {"ge": 0.0, "le": 1.0}
            },
            "use_cache": {
                "type": bool,
                "title": "Use Cache",
                "description": "Whether to use cached results",
                "default": True
            }
        }
        
        # Create dynamic form
        config = dynamic_model_form(fields, title="API Configuration")
        
        # Display the result when submitted
        if config:
            st.success("Form submitted successfully!")
            st.json(config.model_dump_json(indent=2))
    
    # Tab 3: Custom Form
    with tab3:
        st.header("Custom Form")
        st.markdown("""
        This form is created using a list of field definitions and allows for
        custom validation and styling.
        """)
        
        # Define custom form fields
        fields = [
            {
                "name": "username",
                "type": "text",
                "label": "Username",
                "required": True,
                "help": "Your login username",
                "validation": lambda x: True if len(x) >= 5 else "Username must be at least 5 characters"
            },
            {
                "name": "email",
                "type": "text",
                "label": "Email Address",
                "required": True,
                "help": "Your email address",
                "validation": lambda x: True if "@" in x and "." in x else "Invalid email address"
            },
            {
                "name": "roles",
                "type": "multiselect",
                "label": "Roles",
                "options": ["Admin", "User", "Editor", "Viewer"],
                "help": "Select user roles"
            },
            {
                "name": "active",
                "type": "boolean",
                "label": "Active Account",
                "default": True
            }
        ]
        
        # Define submit callback
        def on_submit(data):
            st.session_state.custom_form_data = data
        
        # Create custom form
        form_data = custom_form(fields, key="user_form", on_submit=on_submit)
        
        # Display the result when submitted
        if "custom_form_data" in st.session_state:
            st.success("Form submitted successfully!")
            st.json(st.session_state.custom_form_data)
    
    # Tab 4: Form Builder
    with tab4:
        st.header("Form Builder")
        st.markdown("""
        This form is created using a form builder with a fluent API.
        It's a convenient way to build complex forms with validation.
        """)
        
        # Create form using FormBuilder
        builder = FormBuilder(title="Agent Configuration")
        
        # Add fields to the form
        builder.add_text("agent_name", "Agent Name", required=True, help="Name of the agent")
        builder.add_select("agent_type", "Agent Type", 
                         options=["Assistant", "Code", "Data", "Research", "Custom"], 
                         required=True)
        builder.add_number("max_tokens", "Max Tokens", min=1, max=2000, default=500)
        builder.add_checkbox("streaming", "Enable Streaming", default=True)
        builder.add_textarea("system_prompt", "System Prompt", help="Initial prompt for the agent")
        builder.add_multiselect("capabilities", "Capabilities",
                             options=["Web Search", "Code Generation", "Data Analysis", "File Handling"])
        
        # Add custom validation
        builder.add_validation("agent_name", lambda x: True if not x.startswith("_") else "Name cannot start with underscore")
        
        # Set submit callback
        def on_builder_submit(data):
            st.session_state.builder_form_data = data
        
        builder.on_submit(on_builder_submit)
        
        # Build and render the form
        form_data = builder.build()
        
        # Display the result when submitted
        if "builder_form_data" in st.session_state:
            st.success("Form submitted successfully!")
            st.json(st.session_state.builder_form_data)

if __name__ == "__main__":
    main()