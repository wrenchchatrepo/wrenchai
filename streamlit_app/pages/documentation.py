"""Documentation page for WrenchAI application."""

import streamlit as st
from typing import Dict, List, Any, Optional

# Import utility functions
from wrenchai.streamlit_app.utils.session_state import StateKey, get_state, set_state
from wrenchai.streamlit_app.utils.logger import get_logger
from wrenchai.streamlit_app.utils.ui_components import status_indicator, display_error, display_success
from wrenchai.streamlit_app.components import section_container

# Setup logger
logger = get_logger(__name__)

st.set_page_config(
    page_title="WrenchAI - Documentation",
    page_icon="🔧",
    layout="wide",
)

def main():
    """Main entry point for the documentation page."""
    st.title("📚 Documentation")
    st.markdown("Learn how to use WrenchAI and its features.")
    
    # Create a sidebar for navigation within documentation
    st.sidebar.title("Documentation")
    
    # Define documentation sections
    doc_sections = [
        "Getting Started",
        "Playbooks",
        "Portfolio Generator",
        "API Reference",
        "FAQs"
    ]
    
    selected_section = st.sidebar.radio("Go to section", doc_sections)
    
    # Display content based on selected section
    if selected_section == "Getting Started":
        render_getting_started()
    elif selected_section == "Playbooks":
        render_playbooks_docs()
    elif selected_section == "Portfolio Generator":
        render_portfolio_docs()
    elif selected_section == "API Reference":
        render_api_reference()
    elif selected_section == "FAQs":
        render_faqs()

def render_getting_started():
    """Render the Getting Started documentation section."""
    st.header("Getting Started with WrenchAI")
    
    # Introduction
    with section_container("Introduction"):
        st.markdown("""
        WrenchAI is a powerful automation tool that helps you streamline your development workflow.
        With WrenchAI, you can:
        
        - Execute automation playbooks for common development tasks
        - Generate professional portfolio websites using Docusaurus
        - Integrate with your existing tools and workflows
        - Customize and extend functionality to meet your needs
        """)
    
    # Installation
    with section_container("Installation & Setup"):
        st.markdown("""
        ### System Requirements
        
        - Python 3.8 or higher
        - Docker (optional, for containerized execution)
        - 2GB RAM minimum (4GB recommended)
        
        ### Installation
        
        Install WrenchAI using pip:
        
        ```bash
        pip install wrenchai
        ```
        
        Or clone the repository and install locally:
        
        ```bash
        git clone https://github.com/yourusername/wrenchai.git
        cd wrenchai
        pip install -e .
        ```
        """)
    
    # Quick Start
    with section_container("Quick Start"):
        st.markdown("""
        ### Running your first playbook
        
        1. Navigate to the **Playbooks** section
        2. Select a playbook from the available options
        3. Configure the required parameters
        4. Click **Execute** to run the playbook
        
        ### Creating your portfolio
        
        1. Navigate to the **Portfolio Generator** section
        2. Follow the step-by-step wizard to configure your portfolio
        3. Preview and generate your portfolio website
        4. Deploy to your preferred hosting platform
        """)
    
    # Next Steps
    with section_container("Next Steps"):
        st.markdown("""
        - Explore the [Playbooks](#playbooks) documentation to learn about available automation options
        - Check out the [Portfolio Generator](#portfolio-generator) guide for detailed customization options
        - Visit our [GitHub repository](https://github.com/yourusername/wrenchai) for the latest updates
        - Join our [community](https://discord.gg/wrenchai) to ask questions and share your experience
        """)

def render_playbooks_docs():
    """Render the Playbooks documentation section."""
    st.header("Playbooks Documentation")
    
    # Overview
    with section_container("Overview"):
        st.markdown("""
        Playbooks are pre-configured automation scripts that help you automate common development tasks.
        Each playbook is designed to solve a specific problem or streamline a particular workflow.
        
        Playbooks are organized by categories, making it easy to find the right automation for your needs.
        You can execute playbooks directly from the WrenchAI interface or via the command-line tool.
        """)
    
    # Playbook Categories
    with section_container("Playbook Categories"):
        # Get playbook categories from config
        config = get_state(StateKey.CONFIG)
        categories = config.playbooks.categories if hasattr(config, 'playbooks') and hasattr(config.playbooks, 'categories') \
            else {"development": "Development", "analysis": "Analysis", "deployment": "Deployment"}
        
        # Display categories and descriptions
        for category_id, category_name in categories.items():
            st.subheader(category_name)
            if category_id == "development":
                st.markdown("""
                Development playbooks help you set up project structures, generate code templates,
                and automate repetitive coding tasks.
                
                **Examples:**
                - Project Scaffolding
                - Code Generation
                - Documentation Generation
                - Test Setup
                """)
            elif category_id == "analysis":
                st.markdown("""
                Analysis playbooks help you analyze code, identify issues, and generate reports.
                
                **Examples:**
                - Code Quality Analysis
                - Dependency Check
                - Security Audit
                - Performance Profiling
                """)
            elif category_id == "deployment":
                st.markdown("""
                Deployment playbooks help you automate the deployment process for various platforms.
                
                **Examples:**
                - CI/CD Pipeline Setup
                - Docker Container Configuration
                - Cloud Deployment
                - Release Management
                """)
    
    # Running Playbooks
    with section_container("Running Playbooks"):
        st.markdown("""
        ### Using the UI
        
        1. Navigate to the **Playbooks** page
        2. Browse or search for the desired playbook
        3. Click on the playbook card to view details
        4. Configure the required parameters
        5. Click **Execute** to run the playbook
        6. Monitor the execution progress and view results
        
        ### Using the CLI
        
        You can also run playbooks using the WrenchAI command-line interface:
        
        ```bash
        wrenchai playbook run <playbook_id> --param1 value1 --param2 value2
        ```
        
        For a list of available playbooks:
        
        ```bash
        wrenchai playbook list
        ```
        """)
    
    # Creating Custom Playbooks
    with section_container("Creating Custom Playbooks"):
        st.markdown("""
        Advanced users can create custom playbooks to automate their specific workflows.
        
        ### Playbook Structure
        
        Playbooks are defined using YAML files with the following structure:
        
        ```yaml
        id: custom_playbook
        name: My Custom Playbook
        description: This is a custom playbook that does something awesome
        category: development
        parameters:
          - name: input_file
            type: file
            description: Input file to process
            required: true
          - name: output_dir
            type: directory
            description: Output directory
            default: ./output
        steps:
          - name: process_file
            action: python_script
            script: process_file.py
            args:
              input: "{{parameters.input_file}}"
              output: "{{parameters.output_dir}}"
        ```
        
        For detailed information on creating custom playbooks, see the [Advanced Playbooks](/advanced-playbooks) documentation.
        """)

def render_portfolio_docs():
    """Render the Portfolio Generator documentation section."""
    st.header("Portfolio Generator Documentation")
    
    # Overview
    with section_container("Overview"):
        st.markdown("""
        The Portfolio Generator is a powerful tool that helps you create a professional portfolio website
        using Docusaurus. It provides a user-friendly interface to configure and customize your portfolio,
        making it easy to showcase your projects, skills, and experience.
        
        The generator takes care of the technical details, so you can focus on your content and presentation.
        """)
    
    # Key Features
    with section_container("Key Features"):
        st.markdown("""
        - **User-friendly Wizard**: Step-by-step process to configure your portfolio
        - **Multiple Themes**: Choose from various pre-designed themes to match your style
        - **Customizable Sections**: Add or remove sections based on your needs
        - **Project Showcase**: Highlight your best work with descriptions and images
        - **Skills & Experience**: Display your skills and professional experience
        - **Responsive Design**: Looks great on all devices, from desktop to mobile
        - **One-click Deployment**: Deploy to GitHub Pages, Netlify, or Vercel with a single click
        - **SEO Optimization**: Built-in SEO features to help your portfolio rank well
        """)
    
    # Using the Generator
    with section_container("Using the Generator"):
        st.markdown("""
        ### Step 1: Basic Setup
        
        Configure the basic settings for your portfolio website, including theme, sections to include,
        and deployment options.
        
        ### Step 2: Personal Information
        
        Add your personal details, including name, job title, about section, and profile image.
        
        ### Step 3: Projects
        
        Add your projects with details such as title, description, tags, image, and links.
        
        ### Step 4: Experience & Skills
        
        Add your work experience, education, and skills to showcase your qualifications.
        
        ### Step 5: Preview & Generate
        
        Preview your portfolio website and generate the final output. You can either download the code
        or deploy directly to your chosen platform.
        """)
    
    # Customization
    with section_container("Customization"):
        st.markdown("""
        While the wizard provides many customization options, advanced users can further customize their portfolio
        by editing the generated code directly.
        
        ### Theme Customization
        
        Each theme includes customization options for colors, fonts, and layout. These can be modified in the
        `docusaurus.config.js` file.
        
        ### Content Customization
        
        All content is stored in Markdown files in the `docs` and `blog` directories. You can edit these files
        to update or expand your content.
        
        ### Component Customization
        
        Advanced users can create custom React components to add unique features to their portfolio.
        See the [Docusaurus documentation](https://docusaurus.io/docs/creating-pages) for more information.
        """)
    
    # Deployment
    with section_container("Deployment"):
        st.markdown("""
        The Portfolio Generator supports multiple deployment options:
        
        ### GitHub Pages
        
        Deploy your portfolio to GitHub Pages with a single click. You'll need a GitHub account and a repository
        to host your portfolio.
        
        ### Netlify
        
        Deploy to Netlify for a fast, global CDN and continuous deployment. Netlify offers a generous free tier
        that's perfect for portfolio websites.
        
        ### Vercel
        
        Deploy to Vercel for excellent performance and developer experience. Like Netlify, Vercel offers a
        free tier suitable for portfolio sites.
        
        ### Local Export
        
        Export your portfolio as a static website that you can host on any web server or hosting service.
        """)

def render_api_reference():
    """Render the API Reference documentation section."""
    st.header("API Reference")
    
    # API Overview
    with section_container("API Overview"):
        st.markdown("""
        WrenchAI provides a RESTful API that allows you to integrate its functionality into your own applications
        and workflows. This section documents the available endpoints, authentication methods, and data models.
        
        ### Base URL
        
        ```
        https://api.wrenchai.com/v1
        ```
        
        ### Authentication
        
        The API uses Bearer token authentication. Include the following header in all your requests:
        
        ```
        Authorization: Bearer YOUR_API_KEY
        ```
        
        You can obtain an API key from your WrenchAI account settings.
        """)
    
    # Endpoints
    with section_container("Endpoints"):
        st.markdown("""
        ### Playbooks
        
        #### List Playbooks
        
        ```
        GET /playbooks
        ```
        
        Returns a list of all available playbooks.
        
        #### Get Playbook
        
        ```
        GET /playbooks/{playbook_id}
        ```
        
        Returns details for a specific playbook.
        
        #### Execute Playbook
        
        ```
        POST /playbooks/{playbook_id}/execute
        ```
        
        Executes a playbook with the provided parameters.
        
        #### Get Execution Status
        
        ```
        GET /executions/{execution_id}
        ```
        
        Returns the status of a playbook execution.
        
        ### Portfolio Generator
        
        #### Generate Portfolio
        
        ```
        POST /portfolio/generate
        ```
        
        Generates a portfolio website with the provided configuration.
        
        #### Get Portfolio Status
        
        ```
        GET /portfolio/{portfolio_id}
        ```
        
        Returns the status of a portfolio generation task.
        """)
    
    # Examples
    with section_container("Examples"):
        st.markdown("""
        ### Example: List Playbooks
        
        ```python
        import requests
        
        url = "https://api.wrenchai.com/v1/playbooks"
        headers = {"Authorization": "Bearer YOUR_API_KEY"}
        
        response = requests.get(url, headers=headers)
        playbooks = response.json()
        
        for playbook in playbooks:
            print(f"{playbook['name']} - {playbook['description']}")
        ```
        
        ### Example: Execute Playbook
        
        ```python
        import requests
        
        url = "https://api.wrenchai.com/v1/playbooks/project_scaffolding/execute"
        headers = {
            "Authorization": "Bearer YOUR_API_KEY",
            "Content-Type": "application/json"
        }
        payload = {
            "parameters": {
                "project_name": "my-awesome-project",
                "template": "react",
                "output_dir": "./projects"
            }
        }
        
        response = requests.post(url, json=payload, headers=headers)
        execution = response.json()
        
        print(f"Execution ID: {execution['id']}")
        print(f"Status: {execution['status']}")
        ```
        """)
    
    # SDK
    with section_container("Client SDKs"):
        st.markdown("""
        WrenchAI provides official client SDKs for several programming languages:
        
        ### Python SDK
        
        ```bash
        pip install wrenchai-client
        ```
        
        ```python
        from wrenchai_client import WrenchAIClient
        
        client = WrenchAIClient(api_key="YOUR_API_KEY")
        
        # List playbooks
        playbooks = client.playbooks.list()
        
        # Execute playbook
        execution = client.playbooks.execute(
            "project_scaffolding",
            parameters={
                "project_name": "my-awesome-project",
                "template": "react",
                "output_dir": "./projects"
            }
        )
        ```
        
        ### JavaScript SDK
        
        ```bash
        npm install wrenchai-client
        ```
        
        ```javascript
        const { WrenchAIClient } = require('wrenchai-client');
        
        const client = new WrenchAIClient({ apiKey: 'YOUR_API_KEY' });
        
        // List playbooks
        const playbooks = await client.playbooks.list();
        
        // Execute playbook
        const execution = await client.playbooks.execute(
            'project_scaffolding',
            {
                project_name: 'my-awesome-project',
                template: 'react',
                output_dir: './projects'
            }
        );
        ```
        """)

def render_faqs():
    """Render the FAQs documentation section."""
    st.header("Frequently Asked Questions")
    
    faqs = [
        {
            "question": "What is WrenchAI?",
            "answer": """
            WrenchAI is an automation tool that helps developers streamline their workflow by providing
            ready-to-use playbooks for common tasks and a portfolio generator for creating professional
            portfolio websites using Docusaurus.
            """
        },
        {
            "question": "How do I install WrenchAI?",
            "answer": """
            You can install WrenchAI using pip:
            
            ```bash
            pip install wrenchai
            ```
            
            Or you can clone the repository and install locally:
            
            ```bash
            git clone https://github.com/yourusername/wrenchai.git
            cd wrenchai
            pip install -e .
            ```
            """
        },
        {
            "question": "What are playbooks in WrenchAI?",
            "answer": """
            Playbooks are pre-configured automation scripts that help you automate common development tasks.
            Each playbook is designed to solve a specific problem or streamline a particular workflow.
            WrenchAI provides a library of playbooks for various purposes, and you can also create your own.
            """
        },
        {
            "question": "How do I create a portfolio website with WrenchAI?",
            "answer": """
            WrenchAI includes a Portfolio Generator that helps you create a professional portfolio website
            using Docusaurus. You can access it from the main navigation menu and follow the step-by-step
            wizard to configure and generate your portfolio.
            """
        },
        {
            "question": "Can I customize the generated portfolio?",
            "answer": """
            Yes, the Portfolio Generator provides many customization options through its interface. Additionally,
            advanced users can further customize their portfolio by editing the generated code directly.
            """
        },
        {
            "question": "How do I deploy my portfolio website?",
            "answer": """
            The Portfolio Generator supports multiple deployment options, including GitHub Pages, Netlify,
            Vercel, and local export. You can choose your preferred option during the generation process.
            """
        },
        {
            "question": "Is WrenchAI free to use?",
            "answer": """
            WrenchAI offers both free and premium tiers. The free tier includes basic playbooks and portfolio
            generation, while the premium tier provides additional playbooks, advanced features, and priority support.
            """
        },
        {
            "question": "How do I get support for WrenchAI?",
            "answer": """
            You can get support through the following channels:
            
            - GitHub Issues: For bug reports and feature requests
            - Documentation: For usage information and guides
            - Discord Community: For questions and discussions
            - Email Support: For premium users
            """
        },
        {
            "question": "Can I use WrenchAI in my CI/CD pipeline?",
            "answer": """
            Yes, WrenchAI provides a command-line interface (CLI) and an API that you can integrate into your
            CI/CD pipeline. This allows you to automate tasks and processes as part of your development workflow.
            """
        },
        {
            "question": "How do I contribute to WrenchAI?",
            "answer": """
            We welcome contributions from the community! You can contribute by:
            
            - Reporting bugs or suggesting features on GitHub
            - Submitting pull requests for code improvements
            - Creating and sharing custom playbooks
            - Helping improve documentation
            
            See our [Contribution Guidelines](https://github.com/yourusername/wrenchai/blob/main/CONTRIBUTING.md) for more information.
            """
        }
    ]
    
    # Display FAQs as expandable sections
    for i, faq in enumerate(faqs):
        with st.expander(faq["question"]):
            st.markdown(faq["answer"])

if __name__ == "__main__":
    main()