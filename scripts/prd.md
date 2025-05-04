# Product Requirements Document: Wrench AI Toolbox

## 1. Introduction

### 1.1 Purpose

The Wrench AI Toolbox is a Streamlit-based application that serves as a user interface for the Wrench AI framework. It enables users to leverage the power of coordinated AI agents through configurable playbooks to solve complex problems automatically. This PRD focuses specifically on implementing a robust Streamlit interface for executing the Docusaurus Portfolio Playbook.

### 1.2 Product Overview

Wrench AI is an intelligent automation platform powered by specialized AI agents that work together to solve complex problems. The platform consists of three core components:

1. **Agents**: Specialized AI assistants with specific skills and expertise
2. **Playbooks**: Workflows that coordinate multiple agents to accomplish tasks
3. **Tools**: Capabilities that agents can use to perform actions

The Streamlit app we're building will allow users to interact with this ecosystem through a clean, intuitive interface that provides clear explanations, guided workflows, and real-time visibility into the execution process.

### 1.3 Business Goals

- Simplify the process of using the Wrench AI framework
- Enable users to create professional portfolio websites without technical expertise
- Showcase the capabilities of AI-driven automation
- Provide transparency into the agent collaboration process
- Create a foundation for future AI automation applications## 2. System Architecture

### 2.1 High-Level Architecture

```
┌────────────────────┐     ┌───────────────────┐     ┌─────────────────┐
│  Streamlit App     │     │                   │     │                 │
│  (Wrench AI        │◄───►│  FastAPI Backend  │◄───►│  Agent System   │
│  Toolbox)          │     │                   │     │                 │
└────────────────────┘     └───────────────────┘     └─────────────────┘
         │                          │                        │
         ▼                          ▼                        ▼
┌────────────────────┐     ┌───────────────────┐     ┌─────────────────┐
│  User Interface    │     │  API Endpoints    │     │  AI Agents      │
│  - Chat            │     │  - Playbooks      │     │  - SuperAgent   │
│  - Playbooks       │     │  - Agents         │     │  - GithubAgent  │
│  - Monitoring      │     │  - Tasks          │     │  - UXDesigner   │
│  - Results         │     │  - Tools          │     │  - CodeGen      │
└────────────────────┘     └───────────────────┘     └─────────────────┘
                                     │
                                     ▼
                           ┌───────────────────┐
                           │  External Tools   │
                           │  - GitHub API     │
                           │  - Web Search     │
                           │  - Code Execution │
                           └───────────────────┘
```

### 2.2 Streamlit App Structure

```
wrenchai/streamlit_app/
├── app.py                 # Main app entry point with onboarding
├── components/            # Reusable UI components
│   ├── agent_card.py      # Agent visualization component
│   ├── error_handler.py   # Error handling
│   ├── playbook_card.py   # Playbook visualization component
│   ├── playbook_results.py# Results visualization
│   ├── task_monitor.py    # Real-time task monitoring
│   ├── tooltips.py        # Contextual help tooltips
│   └── ai_assistant.py    # Synthia AI assistant integration
├── pages/                 # Multi-page app structure
│   ├── 01_chat.py         # Conversational interface
│   ├── 02_playbooks.py    # Playbook browser and executor
│   ├── 03_agents.py       # Agent management
│   ├── 04_tools.py        # Tool browser and testing
│   └── 05_metrics.py      # Monitoring and analytics
├── models/                # Pydantic models for UI generation
│   ├── playbook_config.py # Playbook configuration models
│   ├── agent_config.py    # Agent configuration models
│   └── task_config.py     # Task configuration models
├── services/              # Backend service connections
│   ├── api_client.py      # FastAPI client
│   ├── websocket_client.py# WebSocket client
│   └── playbook_service.py# Playbook operations
└── utils/                 # Utility functions
    ├── config.py          # Configuration management
    ├── session.py         # Session state management
    ├── formatting.py      # Text and data formatting
    └── theme.py           # Custom theme configuration
```## 3. Product Features and Requirements

### 3.1 Core Features

#### 3.1.1 Guided Onboarding
- Interactive tutorial explaining the Wrench AI ecosystem
- Visual explanation of agents, playbooks, and tools
- Sample scenarios and use cases

#### 3.1.2 Playbook Browser
- Browse available playbooks with descriptions
- Filter by capabilities, agents used, or use case
- Preview playbook structure and workflow
- Configure and execute playbooks

#### 3.1.3 Docusaurus Portfolio Playbook
- Specialized UI for configuring the portfolio
- Form for inputting portfolio details
- Project configuration options
- Theme selection
- Real-time execution tracking

#### 3.1.4 Real-time Execution Monitoring
- Step-by-step visualization of playbook execution
- Agent activity and reasoning
- Error handling and recovery
- WebSocket connection for live updates

#### 3.1.5 Results Visualization
- Structured output from playbook execution
- Visual representation of portfolio
- Download or export capabilities

#### 3.1.6 AI Assistant Integration
- Contextual help via Synthia AI integration
- Guidance on configuring playbooks
- Troubleshooting assistance

### 3.2 Technical Requirements

#### 3.2.1 Frontend (Streamlit)
- Streamlit 1.46.0 or newer
- Custom theme implementation (Midnight UI)
- Responsive design for different screen sizes
- Accessible UI components
- Integration with Synthia for AI assistance
- Integration with streamlit-pydantic for dynamic form generation

#### 3.2.2 Backend Integration
- HTTP client for API communication (httpx)
- WebSocket client for real-time updates
- Error handling and retry logic
- Authentication support

#### 3.2.3 Data Models
- Pydantic models for configuration validation
- Automatic UI generation from models
- Type hints throughout the codebase## 4. User Experience Design

### 4.1 Design System - Midnight UI

The Wrench AI Toolbox will use the Midnight UI dark color palette for a modern, professional appearance:

| Element | Color Code | Description |
|---------|------------|-------------|
| Primary | `#1B03A3` | Neon Blue |
| Secondary | `#9D00FF` | Neon Purple |
| Accent | `#FF10F0` | Neon Pink |
| Error | `#FF3131` | Neon Red |
| Success | `#39FF14` | Neon Green |
| Warning | `#E9FF32` | Neon Yellow |
| Info | `#00FFFF` | Neon Cyan |
| Primary Foreground | `#E3E3E3` | Soft White |
| Secondary Foreground | `#A3A3A3` | Stone Grey |
| Disabled Foreground | `#606770` | Neutral Grey |
| Primary Background | `#010B13` | Rich Black |
| Secondary Background | `#0F1111` | Charcoal Black |
| Surface Background | `#1A1A1A` | Midnight Black |
| Overlay Color | `#121212AA` | Transparent Dark |

### 4.2 User Flow for Docusaurus Portfolio Generation

+----------------+     +----------------+     +----------------+     +----------------+
|                |     |                |     |                |     |                |
|  Home Page     |---->|  Playbook      |---->|  Configure     |---->|  Execute       |
|  Introduction  |     |  Browser       |     |  Portfolio     |     |  Playbook      |
|                |     |                |     |                |     |                |
+----------------+     +----------------+     +----------------+     +----------------+
                                                                           |
                                                                           |
+----------------+     +----------------+     +----------------+           |
|                |     |                |     |                |           |
|  Portfolio     |<----|  Review        |<----|  Monitor       |<----------+
|  Deployment    |     |  Results       |     |  Execution     |
|                |     |                |     |                |
+----------------+     +----------------+     +----------------+

This diagram represents the 7-stage user flow for Docusaurus Portfolio Generation in the Wrench AI Toolbox. The workflow progresses from left to right in the top row (initial steps), then from right to left in the bottom row (completion steps).

The arrows indicate the direction of user navigation through the application, showing a logical progression from introduction to deployment.

### 4.3 Page Layouts

#### 4.3.1 Home Page
- Welcome message and system overview
- Quick start options for common tasks
- System status indicators
- Navigation to major features

#### 4.3.2 Playbook Browser
- Filterable grid of playbook cards
- Detailed view of selected playbook
- Configuration options for selected playbook
- Execution controls

#### 4.3.3 Playbook Execution
- Real-time progress monitoring
- Agent activity visualization
- Step completion tracking
- Results display
- Error handling and recovery options## 5. Playbook Implementation

### 5.1 Docusaurus Portfolio Playbook Structure

The Docusaurus Portfolio Playbook is designed to automate the creation of a professional portfolio website using Docusaurus. The playbook coordinates multiple specialized agents to handle different aspects of portfolio creation.

```yaml
# Docusaurus Portfolio Playbook

# Workflow Types:
# - standard: Sequential step executed by a single agent
# - work_in_parallel: Multiple operations executed concurrently
# - self_feedback_loop: Agent iteratively improves its own work
# - partner_feedback_loop: Two agents collaborating in a review cycle
# - process: Structured sequence with conditional branching
# - versus: Two agents working competitively on same task
# - handoff: Specialized task delegation based on conditions

- step_id: metadata
  type: standard
  description: "Docusaurus Portfolio Playbook Configuration"
  metadata:
    name: docusaurus_portfolio_playbook
    description: "Build a public-facing Docusaurus portfolio with six sections"
    sections:
      - "GitHub projects (AI/ML in Python)"
      - "Useful scripts (Python, gcloud, SQL, LookML, JS/TS, Git)"
      - "Technical articles"
      - "Frontend examples (NextJS, React)"
      - "Analytics Pipeline"
      - "Data Science (Plotly + Dash, PyMC, PyTorch, SciPy)"
    tools:
      - web_search
      - secrets_manager
      - memory
      - code_generation
      - code_execution
      - github_tool
      - github_mcp
      - puppeteer
      - browser_tools
      - bayesian_update
      - data_analysis
      - test_tool
      - database_tool
      - monitoring_tool
    agents:
      - SuperAgent
      - GithubJourneyAgent
      - CodeGeneratorAgent
      - CodifierAgent
      - UXDesignerAgent
      - InspectorAgent
      - TestEngineerAgent
      - UATAgent
      - DBA
    agent_llms:
      SuperAgent: "claude-3.7-sonnet"
      GithubJourneyAgent: "gpt-4o"
      CodeGeneratorAgent: "claude-3.7-sonnet"
      CodifierAgent: "claude-3.7-sonnet"
      UXDesignerAgent: "gpt-4o"
      InspectorAgent: "claude-3.7-sonnet"
      TestEngineerAgent: "claude-3.7-sonnet"
      UATAgent: "gemini-2.5-flash"
      DBA: "claude-3.7-sonnet"

- step_id: analyze_source_materials
  type: standard
  description: "Analyze source materials and create a comprehensive project plan"
  agent: SuperAgent
  operation: "analyze_and_plan"
  next: setup_repository

- step_id: setup_repository
  type: standard
  description: "Create and configure GitHub repository for Docusaurus site"
  agent: GithubJourneyAgent
  operation: "setup_docusaurus_repo"
  tools:
    - github_tool
    - github_mcp
  parameters:
    repo_name: "portfolio"
    description: "Personal portfolio site built with Docusaurus"
    private: false
    auto_init: true
  next: design_ui

- step_id: design_ui
  type: partner_feedback_loop
  description: "Design UI and site structure with feedback cycles"
  agents:
    creator: UXDesignerAgent
    reviewer: InspectorAgent
  operations:
    - role: creator
      name: "design_site_structure"
    - role: reviewer
      name: "review_design"
    - role: creator
      name: "refine_design"
  iterations: 2
  next: setup_docusaurus

- step_id: setup_docusaurus
  type: standard
  description: "Set up and configure Docusaurus environment"
  agent: CodeGeneratorAgent
  operation: "setup_docusaurus_environment"
  tools:
    - code_execution
    - code_generation
  next: generate_content

- step_id: generate_content
  type: work_in_parallel
  description: "Generate content for all six sections concurrently"
  agents:
    - CodeGeneratorAgent:generate_github_projects
    - CodeGeneratorAgent:generate_useful_scripts
    - CodeGeneratorAgent:generate_technical_articles
    - CodeGeneratorAgent:generate_frontend_examples
    - CodeGeneratorAgent:generate_gcp_pipeline
    - CodeGeneratorAgent:generate_data_science
  input_distribution:
    type: split
    field: "sections"
  output_aggregation:
    type: merge
    strategy: "combine_content"
  next: standardize_code

- step_id: standardize_code
  type: partner_feedback_loop
  description: "Standardize and optimize code across all sections"
  agents:
    creator: CodifierAgent
    reviewer: InspectorAgent
  operations:
    - role: creator
      name: "standardize_code"
    - role: reviewer
      name: "review_code_standards"
    - role: creator
      name: "apply_code_improvements"
  iterations: 2
  next: develop_tests

- step_id: develop_tests
  type: standard
  description: "Develop comprehensive test suite for the portfolio"
  agent: TestEngineerAgent
  operation: "develop_test_suite"
  tools:
    - code_execution
    - github_tool
  next: run_tests

- step_id: run_tests
  type: process
  description: "Run tests with validation and error handling"
  agent: TestEngineerAgent
  input:
    source: "test_suite"
  process:
    - operation: "run_unit_tests"
      condition: "unit_tests_passed == true"
      failure_action: "log_and_fix"
    - operation: "run_integration_tests"
      condition: "integration_tests_passed == true"
      failure_action: "log_and_fix"
    - operation: "run_e2e_tests"
      condition: "e2e_tests_passed == true"
      failure_action: "log_and_fix"
  output:
    destination: "test_results"
  next: user_acceptance_testing

- step_id: user_acceptance_testing
  type: standard
  description: "Perform user acceptance testing"
  agent: UATAgent
  operation: "perform_uat"
  tools:
    - browser_tools
    - memory
  next: final_review

- step_id: final_review
  type: partner_feedback_loop
  description: "Final review and polish of the entire portfolio"
  agents:
    creator: CodifierAgent
    reviewer: InspectorAgent
  operations:
    - role: creator
      name: "final_polish"
    - role: reviewer
      name: "comprehensive_review"
    - role: creator
      name: "apply_final_fixes"
  iterations: 1
  next: deploy

- step_id: deploy
  type: handoff
  description: "Deploy portfolio to GitHub Pages with specialist handling"
  primary_agent: GithubJourneyAgent
  operation: "prepare_deployment"
  handoff_conditions:
    - condition: "needs_ci_cd_setup == true"
      target_agent: CodeGeneratorAgent
      operation: "setup_ci_cd"
    - condition: "needs_domain_config == true"
      target_agent: UXDesignerAgent
      operation: "configure_custom_domain"
  completion_action: "deploy_to_github_pages"
```

### 5.2 Agent Roles in Portfolio Creation

| Agent | Role | Responsibilities |
|-------|------|------------------|
| SuperAgent | Coordinator | Analyzes requirements, creates project plan, coordinates other agents |
| GithubJourneyAgent | Repository Manager | Creates and configures GitHub repository, handles deployment |
| CodeGeneratorAgent | Developer | Sets up Docusaurus environment, generates code for sections |
| UXDesignerAgent | Designer | Creates UI design and site structure |
| CodifierAgent | Documentation | Standardizes code, creates documentation |
| InspectorAgent | Quality Assurance | Reviews design and code, ensures standards compliance |
| TestEngineerAgent | Testing | Develops and runs test suites |
| UATAgent | User Testing | Performs user acceptance testing |### 5.3 Playbook Configuration Model

```python
# models/playbook_config.py
"""Pydantic models for playbook configuration."""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum

class ThemeType(str, Enum):
    """Theme options for Docusaurus."""
    CLASSIC = "classic"
    MODERN = "modern"
    MINIMAL = "minimal"
    DARK = "dark"

class Technology(str, Enum):
    """Common technology options."""
    PYTHON = "Python"
    JAVASCRIPT = "JavaScript"
    TYPESCRIPT = "TypeScript"
    REACT = "React"
    NEXTJS = "Next.js"
    FASTAPI = "FastAPI"
    DJANGO = "Django"
    DOCKER = "Docker"
    KUBERNETES = "Kubernetes"
    AWS = "AWS"
    GCP = "Google Cloud"
    AZURE = "Azure"
    PYTORCH = "PyTorch"
    TENSORFLOW = "TensorFlow"
    SCIKIT_LEARN = "Scikit-learn"
    SQL = "SQL"
    NOSQL = "NoSQL"

class Project(BaseModel):
    """Project configuration for portfolio."""
    name: str = Field(...,
                      description="Name of the project",
                      min_length=3,
                      max_length=100)
    description: str = Field(...,
                           description="Brief description of the project",
                           min_length=10,
                           max_length=500)
    github_url: Optional[str] = Field(None,
                                     description="GitHub repository URL")
    technologies: List[Technology] = Field(default_factory=list,
                                          description="Technologies used in the project")
    image_url: Optional[str] = Field(None,
                                    description="URL to project image or screenshot")

class SocialLinks(BaseModel):
    """Social media links configuration."""
    github: Optional[str] = Field(None, description="GitHub username")
    linkedin: Optional[str] = Field(None, description="LinkedIn URL or username")
    twitter: Optional[str] = Field(None, description="Twitter/X username")
    personal_website: Optional[str] = Field(None, description="Personal website URL")
    email: Optional[str] = Field(None, description="Public email address")

class DocusaurusConfig(BaseModel):
    """Configuration for Docusaurus portfolio."""
    title: str = Field(...,
                      description="Portfolio title",
                      min_length=3,
                      max_length=100)
    description: str = Field(...,
                           description="Portfolio description",
                           min_length=10,
                           max_length=500)
    theme: ThemeType = Field(default=ThemeType.MODERN,
                           description="Visual theme for the portfolio")
    projects: List[Project] = Field(default_factory=list,
                                   description="Projects to include in the portfolio")
    custom_domain: Optional[str] = Field(None,
                                        description="Custom domain for deployment")
    analytics_id: Optional[str] = Field(None,
                                       description="Google Analytics ID")
    social_links: SocialLinks = Field(default_factory=SocialLinks,
                                     description="Social media links")

    class Config:
        schema_extra = {
            "example": {
                "title": "Jane Doe's Developer Portfolio",
                "description": "A showcase of my software development projects and skills",
                "theme": "modern",
                "projects": [
                    {
                        "name": "AI Chat Application",
                        "description": "A real-time chat application powered by AI",
                        "github_url": "https://github.com/janedoe/ai-chat",
                        "technologies": ["Python", "FastAPI", "React", "PyTorch"]
                    }
                ],
                "custom_domain": "portfolio.janedoe.com",
                "social_links": {
                    "github": "janedoe",
                    "linkedin": "jane-doe",
                    "twitter": "jane_doe_dev"
                }
            }
        }
```## 6. Implementation Plan

### 6.1 Theme Implementation

```python
# utils/theme.py
"""Custom theme configuration for Wrench AI Toolbox."""

import streamlit as st

# Midnight UI color palette
MIDNIGHT_UI = {
    "primary": "#1B03A3",        # Neon Blue
    "secondary": "#9D00FF",      # Neon Purple
    "accent": "#FF10F0",         # Neon Pink
    "error": "#FF3131",          # Neon Red
    "success": "#39FF14",        # Neon Green
    "warning": "#E9FF32",        # Neon Yellow
    "info": "#00FFFF",           # Neon Cyan
    "primary_foreground": "#E3E3E3",      # Soft White
    "secondary_foreground": "#A3A3A3",    # Stone Grey
    "disabled_foreground": "#606770",     # Neutral Grey
    "primary_background": "#010B13",      # Rich Black
    "secondary_background": "#0F1111",    # Charcoal Black
    "surface_background": "#1A1A1A",      # Midnight Black
    "overlay": "#121212AA",              # Transparent Dark
}

def apply_midnight_theme():
    """Apply the Midnight UI theme to the Streamlit app."""
    # Configure the theme using Streamlit's theming
    st.markdown(f"""
    <style>
        /* Base theme - dark mode */
        :root {{
            --background-color: {MIDNIGHT_UI["primary_background"]};
            --secondary-background-color: {MIDNIGHT_UI["secondary_background"]};
            --surface-background-color: {MIDNIGHT_UI["surface_background"]};
            --primary-color: {MIDNIGHT_UI["primary"]};
            --secondary-color: {MIDNIGHT_UI["secondary"]};
            --accent-color: {MIDNIGHT_UI["accent"]};
            --text-color: {MIDNIGHT_UI["primary_foreground"]};
            --secondary-text-color: {MIDNIGHT_UI["secondary_foreground"]};
            --disabled-text-color: {MIDNIGHT_UI["disabled_foreground"]};
            --error-color: {MIDNIGHT_UI["error"]};
            --success-color: {MIDNIGHT_UI["success"]};
            --warning-color: {MIDNIGHT_UI["warning"]};
            --info-color: {MIDNIGHT_UI["info"]};
        }}

        /* Apply theme to Streamlit elements */
        .stApp {{
            background-color: var(--background-color);
            color: var(--text-color);
        }}

        .stSidebar .sidebar-content {{
            background-color: var(--secondary-background-color);
        }}

        /* Buttons */
        .stButton>button {{
            background-color: var(--primary-color);
            color: var(--primary-foreground);
            border: none;
            border-radius: 4px;
            transition: all 0.2s ease-in-out;
        }}

        .stButton>button:hover {{
            background-color: var(--secondary-color);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }}

        /* Cards and containers */
        .stCard {{
            background-color: var(--surface-background-color);
            border: 1px solid var(--accent-color);
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
            transition: all 0.2s ease-in-out;
        }}

        .stCard:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.4);
        }}

        /* Text styling */
        h1, h2, h3 {{
            color: var(--primary-foreground);
            font-weight: 600;
        }}

        h1 {{
            border-bottom: 2px solid var(--accent-color);
            padding-bottom: 0.5rem;
        }}

        /* Link styling */
        a {{
            color: var(--info-color);
            text-decoration: none;
            transition: all 0.2s ease-in-out;
        }}

        a:hover {{
            color: var(--accent-color);
            text-decoration: underline;
        }}

        /* Notification colors */
        .success-message {{
            background-color: var(--success-color);
            color: var(--primary-background);
            padding: 0.5rem;
            border-radius: 4px;
        }}

        .error-message {{
            background-color: var(--error-color);
            color: var(--primary-foreground);
            padding: 0.5rem;
            border-radius: 4px;
        }}

        /* Custom scrollbar */
        ::-webkit-scrollbar {{
            width: 10px;
            height: 10px;
        }}

        ::-webkit-scrollbar-track {{
            background: var(--surface-background-color);
        }}

        ::-webkit-scrollbar-thumb {{
            background: var(--secondary-color);
            border-radius: 5px;
        }}

        ::-webkit-scrollbar-thumb:hover {{
            background: var(--accent-color);
        }}
    </style>
    """, unsafe_allow_html=True)
```### 6.2 Main App Entry Point

```python
"""
Wrench AI Toolbox Main App

This is the main entry point for the Wrench AI Toolbox Streamlit application.
It provides an overview of the system and guides users to the various features.
"""

import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import custom modules
from streamlit_app.utils.config import load_config
from streamlit_app.utils.session import initialize_session
from streamlit_app.utils.theme import apply_midnight_theme
from streamlit_app.components.tooltips import show_tooltip
from streamlit_app.components.ai_assistant import initialize_assistant, render_assistant

def main():
    # Apply custom theme
    apply_midnight_theme()

    # Page configuration
    st.set_page_config(
        page_title="Wrench AI Toolbox",
        page_icon="🔧",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/yourusername/wrenchai',
            'Report a bug': 'https://github.com/yourusername/wrenchai/issues',
            'About': "# Wrench AI Toolbox\nPowered by WrenchAI Framework"
        }
    )

    # Initialize session and configuration
    config = load_config()
    initialize_session(config)

    # Initialize AI assistant
    assistant = initialize_assistant(api_key=os.getenv("OPENAI_API_KEY"))
    render_assistant()

    # Sidebar
    with st.sidebar:
        st.title("🔧 Wrench AI")
        st.markdown("---")

        # Navigation
        st.subheader("Navigation")
        st.page_link("app.py", label="🏠 Home", icon="house")
        st.page_link("pages/01_chat.py", label="💬 Chat with Agents", icon="chat")
        st.page_link("pages/02_playbooks.py", label="📚 Playbooks", icon="book")
        st.page_link("pages/03_agents.py", label="🤖 Agents", icon="robot")
        st.page_link("pages/04_tools.py", label="🛠️ Tools", icon="tools")
        st.page_link("pages/05_metrics.py", label="📊 Metrics", icon="bar-chart")

        # Settings
        st.markdown("---")
        st.subheader("Settings")

        # API Configuration
        api_url = st.text_input(
            "API URL",
            value=st.session_state.get("api_url", "http://localhost:8000"),
            help="URL of the WrenchAI API server"
        )
        if api_url != st.session_state.get("api_url"):
            st.session_state.api_url = api_url
            st.rerun()

        # Developer Mode toggle
        if st.toggle("Developer Mode", value=st.session_state.get("developer_mode", False)):
            st.session_state.developer_mode = True
        else:
            st.session_state.developer_mode = False

    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🔧 Wrench AI Toolbox")
        st.subheader("Intelligent Automation with AI Agents")
    with col2:
        if st.button("Start Interactive Tour", key="start_tour",
                    use_container_width=True,
                    help="Take a guided tour of the Wrench AI Toolbox"):
            st.session_state.show_tour = True

    # Show interactive tour if requested
    if st.session_state.get("show_tour", False):
        show_interactive_tour()
        return

    # Main content
    st.markdown("""
    ## Welcome to Wrench AI

    Wrench AI is an intelligent automation platform powered by specialized AI agents that work together to solve complex problems.

    ### How It Works

    1. **Define Your Objective** - What do you want to achieve?
    2. **Select or Configure a Playbook** - Choose from pre-defined workflows or create your own
    3. **Execute and Monitor** - Watch as AI agents collaborate to accomplish your task
    4. **Review Results** - Examine the output and provide feedback

    ### Get Started

    Browse the sidebar to explore different features, or try one of these quick starts:
    """)

    # Quick start buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.image("https://via.placeholder.com/150", width=150)
            st.markdown("### Create a Portfolio")
            st.markdown("Build a professional portfolio website with Docusaurus")
            if st.button("Start Portfolio", key="start_portfolio", use_container_width=True):
                st.switch_page("pages/02_playbooks.py")

    with col2:
        with st.container(border=True):
            st.image("https://via.placeholder.com/150", width=150)
            st.markdown("### Chat with Agents")
            st.markdown("Have a conversation with AI agents to solve problems")
            if st.button("Start Chat", key="start_chat", use_container_width=True):
                st.switch_page("pages/01_chat.py")

    with col3:
        with st.container(border=True):
            st.image("https://via.placeholder.com/150", width=150)
            st.markdown("### Browse Playbooks")
            st.markdown("Explore available automation workflows")
            if st.button("Browse Playbooks", key="browse_playbooks", use_container_width=True):
                st.switch_page("pages/02_playbooks.py")

    # System status
    st.markdown("---")
    st.subheader("System Status")

    col1, col2, col3 = st.columns(3)
    with col1:
        is_connected = st.session_state.get("api_connected", False)
        st.metric("API Status", "Online" if is_connected else "Offline",
                 delta="Connected" if is_connected else "Disconnected",
                 delta_color="normal")
    with col2:
        agent_count = st.session_state.get("agent_count", 0)
        st.metric("Available Agents", agent_count)
    with col3:
        playbook_count = st.session_state.get("playbook_count", 0)
        st.metric("Available Playbooks", playbook_count)

    # Recent executions (if any)
    if st.session_state.get("recent_executions"):
        st.markdown("---")
        st.subheader("Recent Executions")

        for execution in st.session_state.recent_executions:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{execution['playbook_name']}**")
                    st.caption(f"ID: {execution['id']}")
                with col2:
                    st.write(f"Status: {execution['status']}")
                with col3:
                    if st.button("View", key=f"view_{execution['id']}"):
                        st.session_state.selected_execution = execution['id']
                        st.switch_page("pages/02_playbooks.py")

    # Footer
    st.markdown("---")
    st.caption("Wrench AI Toolbox v1.0.0 | Powered by WrenchAI Framework")
```
