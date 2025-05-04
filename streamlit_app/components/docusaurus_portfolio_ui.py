"""Docusaurus Portfolio Playbook specialized UI component."""

import streamlit as st
from typing import Dict, List, Any, Optional
import json

# This component is intended to be used from the portfolio_generator.py page
# It provides specialized UI for the Docusaurus Portfolio Playbook

def render_docusaurus_portfolio_ui(config: Dict[str, Any], on_generate_callback=None):
    """Render the specialized UI for the Docusaurus Portfolio Playbook.
    
    Args:
        config: The configuration dictionary from session state
        on_generate_callback: Callback function to call when generate button is clicked
    """
    # Theme preview section
    with st.expander("Theme Gallery", expanded=True):
        st.write("Choose a theme for your portfolio website:")
        
        # Get themes from config
        themes = {
            "classic": {"name": "Classic", "description": "Clean, modern design with customizable colors"},
            "bootstrap": {"name": "Bootstrap", "description": "Bootstrap-based design with responsive components"},
            "minimal": {"name": "Minimal", "description": "Minimalist design focusing on content"},
            "modern": {"name": "Modern", "description": "Sleek, contemporary design with animations"}
        }
        
        # Display theme gallery
        cols = st.columns(4)
        selected_theme = st.session_state.get("docusaurus_theme", "classic")
        
        for i, (theme_id, theme_info) in enumerate(themes.items()):
            with cols[i % 4]:
                st.image(f"https://via.placeholder.com/300x200?text={theme_info['name']}+Theme")
                st.write(f"**{theme_info['name']}**")
                st.caption(theme_info['description'])
                
                # Radio button for selection
                if st.radio("Select", ["No", "Yes"], 
                            index=1 if theme_id == selected_theme else 0, 
                            key=f"theme_select_{theme_id}",
                            horizontal=True,
                            label_visibility="collapsed") == "Yes":
                    selected_theme = theme_id
                    st.session_state["docusaurus_theme"] = theme_id
    
    # Content configuration
    with st.expander("Content Configuration", expanded=True):
        st.write("Configure the content sections for your portfolio:")
        
        # Available sections
        available_sections = [
            {"id": "introduction", "name": "Introduction", "description": "About you and your work"},
            {"id": "skills", "name": "Skills", "description": "Your technical and professional skills"},
            {"id": "projects", "name": "Projects", "description": "Showcase of your best work"},
            {"id": "experience", "name": "Experience", "description": "Your work history"},
            {"id": "education", "name": "Education", "description": "Your educational background"},
            {"id": "contact", "name": "Contact", "description": "How to reach you"},
            {"id": "blog", "name": "Blog", "description": "Your thoughts and articles"}
        ]
        
        # Get selected sections from session state or default
        selected_sections = st.session_state.get("docusaurus_sections", ["introduction", "projects", "contact"])
        
        # Display section selection
        cols = st.columns(2)
        for i, section in enumerate(available_sections):
            with cols[i % 2]:
                if st.checkbox(
                    f"{section['name']}", 
                    value=section['id'] in selected_sections,
                    help=section['description'],
                    key=f"section_{section['id']}"
                ):
                    if section['id'] not in selected_sections:
                        selected_sections.append(section['id'])
                else:
                    if section['id'] in selected_sections:
                        selected_sections.remove(section['id'])
        
        # Store selected sections
        st.session_state["docusaurus_sections"] = selected_sections
    
    # Personal information
    with st.expander("Personal Information", expanded=True):
        st.write("Add your personal information:")
        
        # Get personal info from session state or default
        personal_info = st.session_state.get("docusaurus_personal_info", {})
        
        # Basic info
        col1, col2 = st.columns(2)
        with col1:
            personal_info["full_name"] = st.text_input(
                "Full Name",
                value=personal_info.get("full_name", ""),
                key="personal_full_name"
            )
        with col2:
            personal_info["title"] = st.text_input(
                "Professional Title",
                value=personal_info.get("title", ""),
                placeholder="e.g., Software Engineer",
                key="personal_title"
            )
        
        # Contact info
        col1, col2 = st.columns(2)
        with col1:
            personal_info["email"] = st.text_input(
                "Email",
                value=personal_info.get("email", ""),
                key="personal_email"
            )
        with col2:
            personal_info["location"] = st.text_input(
                "Location",
                value=personal_info.get("location", ""),
                placeholder="e.g., San Francisco, CA",
                key="personal_location"
            )
        
        # Social links
        col1, col2, col3 = st.columns(3)
        with col1:
            personal_info["github"] = st.text_input(
                "GitHub URL",
                value=personal_info.get("github", ""),
                key="personal_github"
            )
        with col2:
            personal_info["linkedin"] = st.text_input(
                "LinkedIn URL",
                value=personal_info.get("linkedin", ""),
                key="personal_linkedin"
            )
        with col3:
            personal_info["twitter"] = st.text_input(
                "Twitter URL",
                value=personal_info.get("twitter", ""),
                key="personal_twitter"
            )
        
        # Bio
        personal_info["bio"] = st.text_area(
            "Bio/About Me",
            value=personal_info.get("bio", ""),
            height=150,
            key="personal_bio"
        )
        
        # Profile image
        personal_info["profile_image"] = st.text_input(
            "Profile Image URL",
            value=personal_info.get("profile_image", ""),
            key="personal_image"
        )
        
        if personal_info["profile_image"]:
            st.image(personal_info["profile_image"], width=150)
        
        # Store personal info
        st.session_state["docusaurus_personal_info"] = personal_info
    
    # Projects section
    with st.expander("Projects", expanded="projects" in selected_sections):
        if "projects" not in selected_sections:
            st.info("Enable the Projects section in Content Configuration to add projects.")
        else:
            st.write("Add your projects:")
            
            # Get projects from session state or default
            projects = st.session_state.get("docusaurus_projects", [])
            
            # Display existing projects
            for i, project in enumerate(projects):
                with st.expander(f"{project.get('title', 'Project ' + str(i+1))}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        projects[i]['title'] = st.text_input(
                            "Project Title",
                            value=project.get("title", ""),
                            key=f"project_{i}_title"
                        )
                    with col2:
                        projects[i]['tags'] = st.text_input(
                            "Tags (comma separated)",
                            value=", ".join(project.get("tags", [])),
                            key=f"project_{i}_tags"
                        )
                    
                    projects[i]['description'] = st.text_area(
                        "Project Description",
                        value=project.get("description", ""),
                        height=100,
                        key=f"project_{i}_description"
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        projects[i]['image'] = st.text_input(
                            "Project Image URL",
                            value=project.get("image", ""),
                            key=f"project_{i}_image"
                        )
                    with col2:
                        projects[i]['url'] = st.text_input(
                            "Project URL",
                            value=project.get("url", ""),
                            key=f"project_{i}_url"
                        )
                    
                    if st.button("Remove Project", key=f"remove_project_{i}"):
                        projects.pop(i)
                        st.session_state["docusaurus_projects"] = projects
                        st.rerun()
            
            # Add new project
            st.subheader("Add New Project")
            with st.form("new_project_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_title = st.text_input("Project Title", key="new_project_title")
                with col2:
                    new_tags = st.text_input("Tags (comma separated)", key="new_project_tags")
                
                new_description = st.text_area("Project Description", height=100, key="new_project_description")
                
                col1, col2 = st.columns(2)
                with col1:
                    new_image = st.text_input("Project Image URL", key="new_project_image")
                with col2:
                    new_url = st.text_input("Project URL", key="new_project_url")
                
                submitted = st.form_submit_button("Add Project")
                if submitted and new_title:  # Require at least a title
                    projects.append({
                        "title": new_title,
                        "tags": [tag.strip() for tag in new_tags.split(",") if tag.strip()],
                        "description": new_description,
                        "image": new_image,
                        "url": new_url
                    })
                    st.session_state["docusaurus_projects"] = projects
                    st.rerun()
    
    # Deployment settings
    with st.expander("Deployment Settings", expanded=True):
        st.write("Configure deployment options:")
        
        # Get deployment settings from session state or default
        deployment = st.session_state.get("docusaurus_deployment", {"type": "github"})
        
        # Deployment type
        deployment["type"] = st.radio(
            "Deployment Type",
            ["GitHub Pages", "Netlify", "Vercel", "Download Only"],
            index=["GitHub Pages", "Netlify", "Vercel", "Download Only"].index(deployment.get("type", "GitHub Pages")),
            key="deployment_type"
        )
        
        # GitHub settings
        if deployment["type"] == "GitHub Pages":
            col1, col2 = st.columns(2)
            with col1:
                deployment["github_username"] = st.text_input(
                    "GitHub Username",
                    value=deployment.get("github_username", ""),
                    key="github_username"
                )
            with col2:
                deployment["github_repo"] = st.text_input(
                    "Repository Name",
                    value=deployment.get("github_repo", ""),
                    placeholder="e.g., portfolio",
                    key="github_repo"
                )
            
            deployment["github_token"] = st.text_input(
                "GitHub Personal Access Token (optional)",
                value=deployment.get("github_token", ""),
                type="password",
                key="github_token"
            )
        
        # Netlify settings
        elif deployment["type"] == "Netlify":
            deployment["netlify_token"] = st.text_input(
                "Netlify Personal Access Token",
                value=deployment.get("netlify_token", ""),
                type="password",
                key="netlify_token"
            )
            
            deployment["netlify_site_name"] = st.text_input(
                "Site Name (optional)",
                value=deployment.get("netlify_site_name", ""),
                placeholder="e.g., my-portfolio",
                key="netlify_site_name"
            )
        
        # Vercel settings
        elif deployment["type"] == "Vercel":
            deployment["vercel_token"] = st.text_input(
                "Vercel Personal Access Token",
                value=deployment.get("vercel_token", ""),
                type="password",
                key="vercel_token"
            )
            
            deployment["vercel_project_name"] = st.text_input(
                "Project Name (optional)",
                value=deployment.get("vercel_project_name", ""),
                placeholder="e.g., my-portfolio",
                key="vercel_project_name"
            )
        
        # Store deployment settings
        st.session_state["docusaurus_deployment"] = deployment
    
    # Advanced settings
    with st.expander("Advanced Settings"):
        st.write("Configure advanced options:")
        
        # Get advanced settings from session state or default
        advanced = st.session_state.get("docusaurus_advanced", {})
        
        # Site settings
        col1, col2 = st.columns(2)
        with col1:
            site_name_default = personal_info.get("full_name", "") + "'s Portfolio" if personal_info.get("full_name") else "My Portfolio"
            advanced["site_name"] = st.text_input(
                "Site Name",
                value=advanced.get("site_name", site_name_default),
                key="site_name"
            )
        with col2:
            advanced["site_tagline"] = st.text_input(
                "Site Tagline",
                value=advanced.get("site_tagline", "Personal portfolio and projects"),
                key="site_tagline"
            )
        
        # Theme settings
        col1, col2 = st.columns(2)
        with col1:
            advanced["primary_color"] = st.color_picker(
                "Primary Color",
                value=advanced.get("primary_color", "#3578e5"),
                key="primary_color"
            )
        with col2:
            advanced["enable_dark_mode"] = st.checkbox(
                "Enable Dark Mode",
                value=advanced.get("enable_dark_mode", True),
                key="enable_dark_mode"
            )
        
        # Google Analytics
        advanced["google_analytics"] = st.text_input(
            "Google Analytics ID (optional)",
            value=advanced.get("google_analytics", ""),
            key="google_analytics"
        )
        
        # Custom domain
        advanced["custom_domain"] = st.text_input(
            "Custom Domain (optional)",
            value=advanced.get("custom_domain", ""),
            placeholder="e.g., example.com",
            key="custom_domain"
        )
        
        # Store advanced settings
        st.session_state["docusaurus_advanced"] = advanced
    
    # Generate button
    st.write("")
    generate_col1, generate_col2, generate_col3 = st.columns([1, 2, 1])
    with generate_col2:
        if st.button("Generate Portfolio Website", type="primary", use_container_width=True):
            # Collect all configuration
            portfolio_config = {
                "theme": selected_theme,
                "sections": selected_sections,
                "personal_info": personal_info,
                "projects": projects if "projects" in selected_sections else [],
                "deployment": deployment,
                "advanced": advanced
            }
            
            # Store complete configuration
            st.session_state["docusaurus_portfolio_config"] = portfolio_config
            
            # Call the callback if provided
            if on_generate_callback:
                on_generate_callback(portfolio_config)
            
            # Show success message
            st.success("Portfolio configuration complete! Generating your website...")
            
            # Return the configuration
            return portfolio_config

def render_preview(portfolio_config: Dict[str, Any]):
    """Render a preview of the generated portfolio.
    
    Args:
        portfolio_config: The portfolio configuration dictionary
    """
    st.subheader("Portfolio Preview")
    
    # Get configuration values
    theme = portfolio_config.get("theme", "classic")
    personal_info = portfolio_config.get("personal_info", {})
    
    # Create tabs for different preview modes
    tab1, tab2, tab3 = st.tabs(["Desktop", "Mobile", "Code Preview"])
    
    with tab1:
        # Desktop preview
        st.image(f"https://via.placeholder.com/1200x800?text=Desktop+Preview+({theme.title()})")
        
        # Key information
        st.write(f"**Title:** {personal_info.get('full_name', '')} - {personal_info.get('title', '')}")
        st.write(f"**Theme:** {theme.title()}")
        st.write(f"**Sections:** {', '.join([s.title() for s in portfolio_config.get('sections', [])])}")
    
    with tab2:
        # Mobile preview
        st.image(f"https://via.placeholder.com/400x800?text=Mobile+Preview+({theme.title()})")
    
    with tab3:
        # Code preview
        st.write("Sample of generated code:")
        
        advanced = portfolio_config.get("advanced", {})
        site_name = advanced.get("site_name", "My Portfolio")
        
        # Display a snippet of the generated code
        st.code(f'''
// docusaurus.config.js
module.exports = {{
  title: '{site_name}',
  tagline: '{advanced.get("site_tagline", "Personal portfolio and projects")}',
  url: 'https://{personal_info.get("github", "").split("/")[-1] if portfolio_config.get("deployment", {}).get("type") == "GitHub Pages" else "example.com"}',
  baseUrl: '/',
  favicon: 'img/favicon.ico',
  organizationName: '{personal_info.get("github", "").split("/")[-1]}',
  projectName: '{portfolio_config.get("deployment", {}).get("github_repo", "portfolio")}',
  themeConfig: {{
    colorMode: {{
      defaultMode: 'light',
      disableSwitch: {str(not advanced.get("enable_dark_mode", True)).lower()},
      respectPrefersColorScheme: true,
    }},
    navbar: {{
      title: '{site_name}',
      items: [
''', language="javascript")

def render_deploy_status(status: Dict[str, Any]):
    """Render the deployment status.
    
    Args:
        status: The deployment status dictionary
    """
    st.subheader("Deployment Status")
    
    # Get status values
    deploy_status = status.get("status", "pending")
    progress = status.get("progress", 0)
    message = status.get("message", "")
    url = status.get("url", "")
    
    # Display status
    if deploy_status == "pending":
        st.info("Portfolio generation pending...")
    elif deploy_status == "generating":
        st.info(message or "Generating portfolio website...")
        st.progress(progress / 100)
    elif deploy_status == "deploying":
        st.info(message or "Deploying portfolio website...")
        st.progress(progress / 100)
    elif deploy_status == "completed":
        st.success("Portfolio website deployed successfully!")
        if url:
            st.write(f"**URL:** [{url}]({url})")
            st.link_button("Visit Website", url)
            
            # Download button for code
            st.download_button(
                "Download Source Code",
                data=json.dumps({"message": "This is a placeholder for the actual download functionality."}),
                file_name="portfolio-source.zip",
                mime="application/zip"
            )
    elif deploy_status == "failed":
        st.error(f"Deployment failed: {message or 'Unknown error'}")
        if status.get("logs"):
            with st.expander("Deployment Logs"):
                st.code(status.get("logs"))