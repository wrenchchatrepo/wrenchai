import streamlit as st
from typing import Dict, Any, Optional
import yaml
import asyncio
from httpx import AsyncClient
import os
from datetime import datetime

# Configure page settings
st.set_page_config(
    page_title="WrenchAI Portfolio Generator",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        margin-top: 1rem;
    }
    .stExpander {
        background-color: #f0f2f5;
    }
    </style>
    """, unsafe_allow_html=True)

class DocusaurusPlaybookExecutor:
    def __init__(self):
        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        self.client = AsyncClient(base_url=self.api_base_url)
    
    async def load_playbook(self, playbook_path: str) -> Dict[str, Any]:
        """Load and validate the Docusaurus portfolio playbook."""
        try:
            from core.playbook_validator import perform_full_validation
            from core.playbook_schema import Playbook
            
            valid, error, playbook = perform_full_validation(playbook_path)
            if not valid:
                st.error(f"Failed to load playbook: {error}")
                raise ValueError(error)
                
            return playbook
        except Exception as e:
            st.error(f"Failed to load playbook: {str(e)}")
            raise

    async def execute_playbook(self, playbook: 'Playbook') -> Dict[str, Any]:
        """Execute the Docusaurus portfolio playbook."""
        try:
            # Convert to API format
            api_payload = playbook.to_api_format()
            
            # Use the correct endpoint
            response = await self.client.post(
                "/api/playbooks/run",
                json=api_payload
            )
            response.raise_for_status()
            result = response.json()
            
            # Standardize response format
            if result.get("status") == "started":
                result["success"] = True
                result["task_id"] = result.get("run_id")
            else:
                result["success"] = False
                
            return result
        except Exception as e:
            st.error(f"Failed to execute playbook: {str(e)}")
            raise

def main():
    st.title("🔧 WrenchAI Portfolio Generator")
    
    # Initialize session state
    if 'task_id' not in st.session_state:
        st.session_state.task_id = None
    if 'execution_status' not in st.session_state:
        st.session_state.execution_status = None
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Select Page",
            ["Generate Portfolio", "View Status", "Settings"]
        )
    
    if page == "Generate Portfolio":
        render_portfolio_form()
    elif page == "View Status":
        render_status_page()
    else:
        render_settings_page()

def render_portfolio_form():
    st.header("Portfolio Configuration")
    
    with st.form("portfolio_config"):
        # Basic Settings
        st.subheader("Basic Settings")
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Portfolio Title", help="Enter the title for your portfolio")
        with col2:
            theme = st.selectbox(
                "Theme",
                ["classic", "modern", "minimal"],
                help="Select the visual theme for your portfolio"
            )
        
        description = st.text_area(
            "Portfolio Description",
            help="Enter a brief description of your portfolio"
        )
        
        # Project Settings
        st.subheader("Projects")
        num_projects = st.number_input(
            "Number of Projects",
            min_value=1,
            max_value=10,
            value=3,
            help="Select the number of projects to include"
        )
        
        projects = []
        for i in range(int(num_projects)):
            with st.expander(f"Project {i+1}"):
                project = {
                    "name": st.text_input(f"Project {i+1} Name", key=f"name_{i}"),
                    "description": st.text_area(f"Project {i+1} Description", key=f"desc_{i}"),
                    "github_url": st.text_input(f"Project {i+1} GitHub URL", key=f"url_{i}"),
                    "technologies": st.multiselect(
                        f"Technologies Used",
                        ["Python", "JavaScript", "React", "FastAPI", "Docker", "AWS"],
                        key=f"tech_{i}"
                    )
                }
                projects.append(project)
        
        # Submit Button
        if st.form_submit_button("Generate Portfolio"):
            config = {
                "title": title,
                "theme": theme,
                "description": description,
                "projects": projects
            }
            
            try:
                executor = DocusaurusPlaybookExecutor()
                asyncio.run(execute_portfolio_generation(executor, config))
            except Exception as e:
                st.error(f"Failed to generate portfolio: {str(e)}")

def render_status_page():
    st.header("Generation Status")
    
    if st.session_state.task_id:
        with st.spinner("Fetching status..."):
            # Here we would normally fetch the status from the API
            st.info(f"Task ID: {st.session_state.task_id}")
            st.json(st.session_state.execution_status or {})
    else:
        st.warning("No active portfolio generation task.")

def render_settings_page():
    st.header("Settings")
    
    with st.form("settings"):
        api_url = st.text_input(
            "API Base URL",
            value=os.getenv("API_BASE_URL", "http://localhost:8000"),
            help="The base URL for the WrenchAI API"
        )
        
        if st.form_submit_button("Save Settings"):
            # Here we would normally save these settings
            st.success("Settings saved successfully!")

async def execute_portfolio_generation(
    executor: DocusaurusPlaybookExecutor,
    config: Dict[str, Any]
) -> None:
    """Execute the portfolio generation process."""
    try:
        with st.spinner("Loading playbook..."):
            playbook = await executor.load_playbook(
                "core/playbooks/docusaurus_portfolio_playbook.yaml"
            )
            
            # Update playbook with form data
            playbook = playbook.merge_user_config(config)
        
        with st.spinner("Generating portfolio..."):
            result = await executor.execute_playbook(playbook)
            
            # Update session state
            st.session_state.task_id = result.get("task_id")
            st.session_state.execution_status = result
            
            st.success("Portfolio generation started successfully!")
            st.json(result)
    except Exception as e:
        st.error(f"Failed to generate portfolio: {str(e)}")
        raise

if __name__ == "__main__":
    main() 