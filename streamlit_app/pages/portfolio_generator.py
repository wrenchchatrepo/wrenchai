"""Portfolio Generator page for WrenchAI application."""

import streamlit as st
from typing import Dict, List, Any, Optional

# Import utility functions
from wrenchai.streamlit_app.utils.session_state import StateKey, get_state, set_state
from wrenchai.streamlit_app.utils.logger import get_logger
from wrenchai.streamlit_app.utils.ui_components import status_indicator, display_error, display_success
from wrenchai.streamlit_app.components import (
    section_container,
    step_progress,
    file_preview,
    component_settings
)

# Setup logger
logger = get_logger(__name__)

st.set_page_config(
    page_title="WrenchAI - Portfolio Generator",
    page_icon="ud83dudd27",
    layout="wide",
)

def main():
    """Main entry point for the portfolio generator page."""
    st.title("ud83dudc68u200dud83dudcbb Portfolio Generator")
    st.markdown("Generate a professional portfolio website using Docusaurus.")
    
    # Initialize portfolio state if needed
    if StateKey.PORTFOLIO_CONFIG.value not in st.session_state:
        set_state(StateKey.PORTFOLIO_CONFIG, {
            "theme": get_state(StateKey.PORTFOLIO_THEME, "classic"),
            "sections": get_state(StateKey.PORTFOLIO_SECTIONS, ["introduction", "projects", "contact"]),
            "personal_info": {},
            "projects": [],
            "experience": [],
            "education": [],
            "skills": [],
            "step": 1
        })
    
    # Get current portfolio configuration
    portfolio_config = get_state(StateKey.PORTFOLIO_CONFIG, {})
    current_step = portfolio_config.get("step", 1)
    
    # Display wizard progress
    steps = [
        "Basic Setup",
        "Personal Information",
        "Projects",
        "Experience & Skills",
        "Preview & Generate"
    ]
    step_progress(current_step, steps)
    
    # Content based on current step
    if current_step == 1:
        render_step_1()
    elif current_step == 2:
        render_step_2()
    elif current_step == 3:
        render_step_3()
    elif current_step == 4:
        render_step_4()
    elif current_step == 5:
        render_step_5()

def render_step_1():
    """Render step 1: Basic Setup."""
    with section_container("Website Configuration"):
        st.write("Let's set up the basic configuration for your portfolio website.")
        
        # Option to switch to specialized Docusaurus UI
        st.info("We have a specialized UI for Docusaurus portfolios that provides more options. [Switch to Docusaurus Portfolio UI](docusaurus_portfolio)")
        
        # Get configuration and current portfolio config
        config = get_state(StateKey.CONFIG)
        portfolio_config = get_state(StateKey.PORTFOLIO_CONFIG, {})
        
        # Theme selection
        themes = list(config.docusaurus.themes.keys()) if hasattr(config, 'docusaurus') and hasattr(config.docusaurus, 'themes') \
            else ["classic", "bootstrap", "minimal", "modern"]
        
        theme_names = {k: v for k, v in config.docusaurus.themes.items()} if hasattr(config, 'docusaurus') and hasattr(config.docusaurus, 'themes') \
            else {"classic": "Classic", "bootstrap": "Bootstrap", "minimal": "Minimal", "modern": "Modern"}
        
        selected_theme = st.selectbox(
            "Theme",
            themes,
            format_func=lambda x: theme_names.get(x, x),
            index=themes.index(portfolio_config.get("theme", "classic")) if portfolio_config.get("theme") in themes else 0,
            key="portfolio_theme_select"
        )
        
        # Theme preview image
        st.image(f"https://via.placeholder.com/600x300?text={selected_theme.title()}+Theme+Preview", 
                 caption=f"{theme_names.get(selected_theme, selected_theme)} theme preview")
        
        # Sections selection
        available_sections = ["introduction", "skills", "projects", "experience", "education", "contact", "blog"]
        section_names = {
            "introduction": "Introduction",
            "skills": "Skills",
            "projects": "Projects",
            "experience": "Work Experience",
            "education": "Education",
            "contact": "Contact",
            "blog": "Blog"
        }
        
        selected_sections = st.multiselect(
            "Sections to Include",
            available_sections,
            format_func=lambda x: section_names.get(x, x.title()),
            default=portfolio_config.get("sections", ["introduction", "projects", "contact"]),
            key="portfolio_sections_select"
        )
        
        # Additional website settings
        col1, col2 = st.columns(2)
        with col1:
            site_name = st.text_input(
                "Website Name",
                value=portfolio_config.get("site_name", "My Portfolio"),
                key="site_name_input"
            )
        
        with col2:
            site_tagline = st.text_input(
                "Tagline",
                value=portfolio_config.get("site_tagline", "Personal portfolio and projects"),
                key="site_tagline_input"
            )
        
        # Navigation options
        with st.expander("Advanced Configuration"):
            github_url = st.text_input(
                "GitHub URL",
                value=portfolio_config.get("github_url", ""),
                key="github_url_input"
            )
            
            linkedin_url = st.text_input(
                "LinkedIn URL",
                value=portfolio_config.get("linkedin_url", ""),
                key="linkedin_url_input"
            )
            
            dark_mode = st.checkbox(
                "Enable Dark Mode",
                value=portfolio_config.get("dark_mode", True),
                key="dark_mode_input"
            )
            
            deploy_type = st.radio(
                "Deployment Type",
                ["GitHub Pages", "Netlify", "Vercel", "Local Export"],
                index=["GitHub Pages", "Netlify", "Vercel", "Local Export"].index(portfolio_config.get("deploy_type", "GitHub Pages")),
                key="deploy_type_input"
            )
    
    # Navigation buttons
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("Next: Personal Information →", key="step1_next"):
            # Save current selections to session state
            portfolio_config.update({
                "theme": selected_theme,
                "sections": selected_sections,
                "site_name": site_name,
                "site_tagline": site_tagline,
                "github_url": github_url,
                "linkedin_url": linkedin_url,
                "dark_mode": dark_mode,
                "deploy_type": deploy_type,
                "step": 2
            })
            set_state(StateKey.PORTFOLIO_CONFIG, portfolio_config)
            st.rerun()

def render_step_2():
    """Render step 2: Personal Information."""
    with section_container("Personal Information"):
        st.write("Tell us about yourself. This information will be used throughout your portfolio.")
        
        # Get current portfolio config
        portfolio_config = get_state(StateKey.PORTFOLIO_CONFIG, {})
        personal_info = portfolio_config.get("personal_info", {})
        
        # Basic information
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input(
                "Full Name",
                value=personal_info.get("full_name", ""),
                key="full_name_input"
            )
        
        with col2:
            job_title = st.text_input(
                "Job Title/Position",
                value=personal_info.get("job_title", ""),
                key="job_title_input"
            )
        
        # Contact information
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input(
                "Email Address",
                value=personal_info.get("email", ""),
                key="email_input"
            )
        
        with col2:
            location = st.text_input(
                "Location",
                value=personal_info.get("location", ""),
                placeholder="e.g., San Francisco, CA",
                key="location_input"
            )
        
        # About section
        st.subheader("About Me")
        about_me = st.text_area(
            "Write a brief description about yourself",
            value=personal_info.get("about_me", ""),
            height=150,
            key="about_me_input"
        )
        
        # Profile image
        st.subheader("Profile Image")
        profile_image_url = st.text_input(
            "Profile Image URL",
            value=personal_info.get("profile_image_url", ""),
            key="profile_image_input"
        )
        
        if profile_image_url:
            st.image(profile_image_url, width=150)
    
    # Navigation buttons
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        if st.button("← Back", key="step2_back"):
            portfolio_config["step"] = 1
            set_state(StateKey.PORTFOLIO_CONFIG, portfolio_config)
            st.rerun()
    with col3:
        if st.button("Next: Projects →", key="step2_next"):
            # Save current inputs to session state
            personal_info.update({
                "full_name": full_name,
                "job_title": job_title,
                "email": email,
                "location": location,
                "about_me": about_me,
                "profile_image_url": profile_image_url
            })
            portfolio_config["personal_info"] = personal_info
            portfolio_config["step"] = 3
            set_state(StateKey.PORTFOLIO_CONFIG, portfolio_config)
            st.rerun()

def render_step_3():
    """Render step 3: Projects."""
    with section_container("Projects"):
        st.write("Add projects to showcase in your portfolio.")
        
        # Get current portfolio config
        portfolio_config = get_state(StateKey.PORTFOLIO_CONFIG, {})
        projects = portfolio_config.get("projects", [])
        
        # Display existing projects
        if projects:
            st.subheader("Your Projects")
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
                        projects[i]['image_url'] = st.text_input(
                            "Project Image URL",
                            value=project.get("image_url", ""),
                            key=f"project_{i}_image"
                        )
                    with col2:
                        projects[i]['project_url'] = st.text_input(
                            "Project URL",
                            value=project.get("project_url", ""),
                            key=f"project_{i}_url"
                        )
                    
                    if st.button("Remove Project", key=f"remove_project_{i}"):
                        projects.pop(i)
                        portfolio_config["projects"] = projects
                        set_state(StateKey.PORTFOLIO_CONFIG, portfolio_config)
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
                new_image_url = st.text_input("Project Image URL", key="new_project_image")
            with col2:
                new_project_url = st.text_input("Project URL", key="new_project_url")
            
            submitted = st.form_submit_button("Add Project")
            if submitted and new_title:  # Require at least a title
                projects.append({
                    "title": new_title,
                    "tags": [tag.strip() for tag in new_tags.split(",") if tag.strip()],
                    "description": new_description,
                    "image_url": new_image_url,
                    "project_url": new_project_url
                })
                portfolio_config["projects"] = projects
                set_state(StateKey.PORTFOLIO_CONFIG, portfolio_config)
                st.rerun()
    
    # Navigation buttons
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        if st.button("← Back", key="step3_back"):
            portfolio_config["step"] = 2
            set_state(StateKey.PORTFOLIO_CONFIG, portfolio_config)
            st.rerun()
    with col3:
        if st.button("Next: Experience & Skills →", key="step3_next"):
            # Save projects to session state (already saved above)
            portfolio_config["step"] = 4
            set_state(StateKey.PORTFOLIO_CONFIG, portfolio_config)
            st.rerun()

def render_step_4():
    """Render step 4: Experience & Skills."""
    # Get current portfolio config
    portfolio_config = get_state(StateKey.PORTFOLIO_CONFIG, {})
    
    # Create two tabs for Experience and Skills
    tab1, tab2 = st.tabs(["Experience", "Skills"])
    
    with tab1:
        # Experience section
        with section_container("Work Experience"):
            st.write("Add your work experience.")
            
            experience = portfolio_config.get("experience", [])
            
            # Display existing experience entries
            if experience:
                st.subheader("Your Experience")
                for i, exp in enumerate(experience):
                    with st.expander(f"{exp.get('company', 'Company ' + str(i+1))} - {exp.get('role', 'Role')}"): 
                        col1, col2 = st.columns(2)
                        with col1:
                            experience[i]['company'] = st.text_input(
                                "Company Name",
                                value=exp.get("company", ""),
                                key=f"exp_{i}_company"
                            )
                        with col2:
                            experience[i]['role'] = st.text_input(
                                "Role/Position",
                                value=exp.get("role", ""),
                                key=f"exp_{i}_role"
                            )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            experience[i]['start_date'] = st.text_input(
                                "Start Date",
                                value=exp.get("start_date", ""),
                                placeholder="e.g., Jan 2020",
                                key=f"exp_{i}_start"
                            )
                        with col2:
                            experience[i]['end_date'] = st.text_input(
                                "End Date",
                                value=exp.get("end_date", ""),
                                placeholder="e.g., Present",
                                key=f"exp_{i}_end"
                            )
                        
                        experience[i]['description'] = st.text_area(
                            "Description",
                            value=exp.get("description", ""),
                            height=100,
                            key=f"exp_{i}_description"
                        )
                        
                        if st.button("Remove Experience", key=f"remove_exp_{i}"):
                            experience.pop(i)
                            portfolio_config["experience"] = experience
                            set_state(StateKey.PORTFOLIO_CONFIG, portfolio_config)
                            st.rerun()
            
            # Add new experience
            st.subheader("Add New Experience")
            with st.form("new_exp_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_company = st.text_input("Company Name", key="new_exp_company")
                with col2:
                    new_role = st.text_input("Role/Position", key="new_exp_role")
                
                col1, col2 = st.columns(2)
                with col1:
                    new_start_date = st.text_input("Start Date", placeholder="e.g., Jan 2020", key="new_exp_start")
                with col2:
                    new_end_date = st.text_input("End Date", placeholder="e.g., Present", key="new_exp_end")
                
                new_exp_description = st.text_area("Description", height=100, key="new_exp_description")
                
                submitted = st.form_submit_button("Add Experience")
                if submitted and new_company and new_role:  # Require at least company and role
                    experience.append({
                        "company": new_company,
                        "role": new_role,
                        "start_date": new_start_date,
                        "end_date": new_end_date,
                        "description": new_exp_description
                    })
                    portfolio_config["experience"] = experience
                    set_state(StateKey.PORTFOLIO_CONFIG, portfolio_config)
                    st.rerun()
    
    with tab2:
        # Skills section
        with section_container("Skills"):
            st.write("Add your skills to showcase.")
            
            skills = portfolio_config.get("skills", [])
            
            # Organize skills by category
            skill_categories = {
                "technical": "Technical Skills",
                "soft": "Soft Skills",
                "languages": "Languages",
                "tools": "Tools & Platforms",
                "other": "Other Skills"
            }
            
            # Display existing skills by category
            if skills:
                st.subheader("Your Skills")
                for category, category_name in skill_categories.items():
                    category_skills = [skill for skill in skills if skill.get("category") == category]
                    if category_skills:
                        with st.expander(category_name, expanded=True):
                            for i, skill in enumerate(category_skills):
                                col1, col2, col3 = st.columns([3, 1, 1])
                                with col1:
                                    skill_index = skills.index(skill)
                                    skills[skill_index]['name'] = st.text_input(
                                        "Skill Name",
                                        value=skill.get("name", ""),
                                        key=f"skill_{skill_index}_name"
                                    )
                                with col2:
                                    skills[skill_index]['level'] = st.slider(
                                        "Proficiency",
                                        min_value=1,
                                        max_value=5,
                                        value=skill.get("level", 3),
                                        key=f"skill_{skill_index}_level"
                                    )
                                with col3:
                                    if st.button("Remove", key=f"remove_skill_{skill_index}"):
                                        skills.pop(skill_index)
                                        portfolio_config["skills"] = skills
                                        set_state(StateKey.PORTFOLIO_CONFIG, portfolio_config)
                                        st.rerun()
            
            # Add new skill
            st.subheader("Add New Skill")
            with st.form("new_skill_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_skill_name = st.text_input("Skill Name", key="new_skill_name")
                with col2:
                    new_skill_category = st.selectbox(
                        "Category",
                        list(skill_categories.keys()),
                        format_func=lambda x: skill_categories.get(x, x),
                        key="new_skill_category"
                    )
                
                new_skill_level = st.slider(
                    "Proficiency",
                    min_value=1,
                    max_value=5,
                    value=3,
                    key="new_skill_level"
                )
                
                submitted = st.form_submit_button("Add Skill")
                if submitted and new_skill_name:  # Require at least a name
                    skills.append({
                        "name": new_skill_name,
                        "category": new_skill_category,
                        "level": new_skill_level
                    })
                    portfolio_config["skills"] = skills
                    set_state(StateKey.PORTFOLIO_CONFIG, portfolio_config)
                    st.rerun()
    
    # Navigation buttons
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        if st.button("← Back", key="step4_back"):
            portfolio_config["step"] = 3
            set_state(StateKey.PORTFOLIO_CONFIG, portfolio_config)
            st.rerun()
    with col3:
        if st.button("Next: Preview & Generate →", key="step4_next"):
            # Save experience and skills to session state (already saved above)
            portfolio_config["step"] = 5
            set_state(StateKey.PORTFOLIO_CONFIG, portfolio_config)
            st.rerun()

def render_step_5():
    """Render step 5: Preview & Generate."""
    with section_container("Website Preview"):
        st.write("Preview your portfolio website and generate it.")
        
        # Get current portfolio config
        portfolio_config = get_state(StateKey.PORTFOLIO_CONFIG, {})
        
        # Display a basic preview of the website
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Visual Preview")
            # Placeholder for actual preview - in a real app, this would be a rendered preview
            preview_image_url = f"https://via.placeholder.com/800x600?text=Portfolio+Preview+({portfolio_config.get('theme', 'classic')})"
            st.image(preview_image_url, use_column_width=True)
        
        with col2:
            st.subheader("Configuration Summary")
            st.write(f"**Theme:** {portfolio_config.get('theme', 'classic').title()}")
            st.write(f"**Website Name:** {portfolio_config.get('site_name', 'My Portfolio')}")
            st.write(f"**Sections:** {', '.join([s.title() for s in portfolio_config.get('sections', [])])}")
            
            st.write(f"**Projects:** {len(portfolio_config.get('projects', []))}")
            st.write(f"**Experience Entries:** {len(portfolio_config.get('experience', []))}")
            st.write(f"**Skills:** {len(portfolio_config.get('skills', []))}")
            
            st.write(f"**Deployment Type:** {portfolio_config.get('deploy_type', 'GitHub Pages')}")
            
            # Generate button
            if st.button("Generate Portfolio Website", type="primary"):
                set_state(StateKey.PORTFOLIO_BUILD_STATUS, {"status": "in_progress", "message": "Generating portfolio website..."})
                # Here we would trigger the actual generation process
                # For this demo, we'll just simulate it with a message
                st.success("Portfolio generation started! This may take a few minutes.")
    
    # Generation options
    with section_container("Generation Options"):
        col1, col2 = st.columns(2)
        
        with col1:
            download_code = st.checkbox("Download Code", value=True, key="download_code")
            include_readme = st.checkbox("Include README", value=True, key="include_readme")
        
        with col2:
            deploy_now = st.checkbox("Deploy After Generation", value=True, key="deploy_now")
            open_preview = st.checkbox("Open Preview When Ready", value=True, key="open_preview")
    
    # Build status
    build_status = get_state(StateKey.PORTFOLIO_BUILD_STATUS, {"status": "pending"})
    if build_status.get("status") == "in_progress":
        with section_container("Build Status"):
            st.info(build_status.get("message", "Processing..."))
            st.progress(build_status.get("progress", 0.0))
    elif build_status.get("status") == "completed":
        with section_container("Build Status"):
            st.success("Portfolio website generated successfully!")
            st.write(f"**Deployment URL:** {build_status.get('deploy_url', 'https://example.com')}")
            col1, col2 = st.columns(2)
            with col1:
                st.link_button("🔗 View Your Website", build_status.get('deploy_url', 'https://example.com'))
            with col2:
                st.link_button("⬇️ Download Code", build_status.get('download_url', '#'))
    
    # Navigation buttons
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("← Back", key="step5_back"):
            portfolio_config["step"] = 4
            set_state(StateKey.PORTFOLIO_CONFIG, portfolio_config)
            st.rerun()

if __name__ == "__main__":
    main()