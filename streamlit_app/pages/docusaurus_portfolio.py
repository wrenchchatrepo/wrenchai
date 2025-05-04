"""Portfolio Generation Wizard for Docusaurus in Streamlit"""

import streamlit as st
import time
import random

# Import utility functions
from wrenchai.streamlit_app.utils.session_state import StateKey, get_state, set_state
from wrenchai.streamlit_app.utils.logger import get_logger
from wrenchai.streamlit_app.utils.ui_components import status_indicator, display_error, display_success
from wrenchai.streamlit_app.components import section_container, step_progress
from wrenchai.streamlit_app.components.docusaurus_portfolio_ui import render_docusaurus_portfolio_ui, render_preview, render_deploy_status

# Setup logger
logger = get_logger(__name__)

# Configure page
st.set_page_config(
    page_title="WrenchAI - Portfolio Generator",
    page_icon="ud83dudd27",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main entry point for the Docusaurus Portfolio Generator."""
    st.title("ud83dudc68u200dud83dudcbb Docusaurus Portfolio Generator")
    st.markdown("Create a beautiful portfolio website with Docusaurus in just a few steps.")
    
    # Initialize portfolio state if needed
    if "docusaurus_portfolio_config" not in st.session_state:
        st.session_state["docusaurus_portfolio_config"] = {}
    
    if "docusaurus_deploy_status" not in st.session_state:
        st.session_state["docusaurus_deploy_status"] = {"status": "pending"}
    
    # Check deployment status
    deploy_status = st.session_state["docusaurus_deploy_status"]
    
    # If a deployment is in progress, simulate progress for demo purposes
    if deploy_status.get("status") in ["generating", "deploying"]:
        simulate_deployment_progress()
    
    # If we're in active deployment or viewing results, show that view
    if deploy_status.get("status") in ["generating", "deploying", "completed", "failed"]:
        # We have an active deployment or completed deployment, show that view
        render_deployment_view()
    else:  
        # We're in configuration mode
        render_configuration_view()

def render_configuration_view():
    """Render the configuration view for the Docusaurus Portfolio Generator."""
    # Get current configuration
    config = get_state(StateKey.CONFIG)
    
    # Render the specialized Docusaurus UI component
    render_docusaurus_portfolio_ui(config, on_generate_callback=start_deployment)

def render_deployment_view():
    """Render the deployment view showing status and results."""
    # Get deployment status and portfolio config
    deploy_status = st.session_state["docusaurus_deploy_status"]
    portfolio_config = st.session_state.get("docusaurus_portfolio_config", {})
    
    # Create tabs for status and preview
    tab1, tab2 = st.tabs(["Deployment Status", "Preview"])
    
    with tab1:
        # Show deployment status
        render_deploy_status(deploy_status)
        
        # Show action buttons based on status
        if deploy_status.get("status") in ["completed", "failed"]:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Start New Portfolio"):
                    # Reset deployment status and portfolio config
                    st.session_state["docusaurus_deploy_status"] = {"status": "pending"}
                    st.session_state["docusaurus_portfolio_config"] = {}
                    st.rerun()
            with col2:
                if deploy_status.get("status") == "failed" and st.button("Retry Deployment"):
                    # Retry with the same config
                    start_deployment(portfolio_config)
                    st.rerun()
        elif deploy_status.get("status") in ["generating", "deploying"]:
            if st.button("Cancel Deployment"):
                # Set status to failed
                deploy_status["status"] = "failed"
                deploy_status["message"] = "Deployment cancelled by user"
                st.session_state["docusaurus_deploy_status"] = deploy_status
                st.rerun()
    
    with tab2:
        # Show preview if we have a portfolio config
        if portfolio_config:
            render_preview(portfolio_config)
        else:
            st.info("No portfolio configuration available for preview.")

def start_deployment(portfolio_config):
    """Start the deployment process for the Docusaurus portfolio.
    
    Args:
        portfolio_config: The portfolio configuration dictionary
    """
    # Store portfolio config
    st.session_state["docusaurus_portfolio_config"] = portfolio_config
    
    # Initialize deployment status
    st.session_state["docusaurus_deploy_status"] = {
        "status": "generating",
        "progress": 0,
        "message": "Initializing portfolio generation...",
        "start_time": time.time()
    }
    
    # Log deployment start
    logger.info(f"Starting portfolio deployment with theme: {portfolio_config.get('theme')}")
    
    # In a real app, this would trigger a backend process to generate and deploy the portfolio

def simulate_deployment_progress():
    """Simulate deployment progress for demo purposes."""
    # Get current status
    status = st.session_state["docusaurus_deploy_status"]
    
    # Update progress
    current_progress = status.get("progress", 0)
    new_progress = min(current_progress + random.randint(3, 8), 100)
    status["progress"] = new_progress
    
    # Update message based on progress
    if status.get("status") == "generating":
        if new_progress < 30:
            status["message"] = "Generating site structure and configuration..."
        elif new_progress < 60:
            status["message"] = "Creating content pages and components..."
        elif new_progress < 90:
            status["message"] = "Applying theme and styling..."
        elif new_progress == 100:
            # Move to deploying phase
            status["status"] = "deploying"
            status["progress"] = 0
            status["message"] = "Starting deployment process..."
    elif status.get("status") == "deploying":
        if new_progress < 30:
            status["message"] = "Building static files..."
        elif new_progress < 60:
            status["message"] = "Optimizing assets and images..."
        elif new_progress < 90:
            status["message"] = "Uploading to deployment target..."
        elif new_progress == 100:
            # Complete deployment
            status["status"] = "completed"
            status["message"] = "Portfolio successfully deployed!"
            status["end_time"] = time.time()
            
            # Generate a random URL based on deployment type
            deployment = st.session_state.get("docusaurus_portfolio_config", {}).get("deployment", {})
            deploy_type = deployment.get("type", "GitHub Pages")
            
            if deploy_type == "GitHub Pages":
                github_username = deployment.get("github_username", "username")
                github_repo = deployment.get("github_repo", "portfolio")
                status["url"] = f"https://{github_username}.github.io/{github_repo}"
            elif deploy_type == "Netlify":
                site_name = deployment.get("netlify_site_name", f"portfolio-{random.randint(1000, 9999)}")
                status["url"] = f"https://{site_name}.netlify.app"
            elif deploy_type == "Vercel":
                project_name = deployment.get("vercel_project_name", f"portfolio-{random.randint(1000, 9999)}")
                status["url"] = f"https://{project_name}.vercel.app"
            else:  # Download only
                status["url"] = ""
    
    # Store updated status
    st.session_state["docusaurus_deploy_status"] = status

if __name__ == "__main__":
    main()