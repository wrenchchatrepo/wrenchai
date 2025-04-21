# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import streamlit as st
import requests
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import yaml
import time
import os
from PIL import Image
import io
import tempfile

# Configure the app
st.set_page_config(
    layout="wide", 
    page_title="Wrenchai Multi-Agent Framework",
    page_icon="🤖"
)

# API endpoint (change when deployed)
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'config_editor' not in st.session_state:
    st.session_state.config_editor = {}

# Utility functions
def load_configs():
    """Load all configuration files"""
    configs = {}
    config_paths = {
        'agents': '../core/configs/agents.yaml',
        'tools': '../core/configs/tools.yaml',
        'playbooks': '../core/configs/playbooks.yaml',
    }
    
    for key, path in config_paths.items():
        if os.path.exists(path):
            with open(path, 'r') as f:
                configs[key] = yaml.safe_load(f)
        else:
            configs[key] = {}
    
    return configs

def save_config(config_type, data):
    """Save configuration to file"""
    config_dir = '../core/configs'
    os.makedirs(config_dir, exist_ok=True)
    
    path = f'{config_dir}/{config_type}.yaml'
    with open(path, 'w') as f:
        yaml.dump(data, f, sort_keys=False)
    
    st.success(f"Configuration saved to {path}")
    
def add_log(message):
    """Add a message to the logs"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    st.session_state.logs.append(f"[{timestamp}] {message}")

def run_api_request(endpoint, method="GET", data=None):
    """Run API request and handle errors"""
    url = f"{API_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        else:
            st.error(f"Unsupported method: {method}")
            return None
            
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error(f"Could not connect to API at {url}. Is the server running?")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"HTTP error: {e}")
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

# Load configurations
try:
    configs = load_configs()
except Exception as e:
    st.error(f"Error loading configurations: {str(e)}")
    configs = {'agents': {}, 'tools': {}, 'playbooks': {}}

# Main UI
st.title("🤖 Wrenchai Multi-Agent Framework")

# Sidebar for navigation
st.sidebar.header("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Chat Interface", "Configuration Editor", "Logs Viewer", "Workflow Visualizer"]
)

# Chat Interface
if page == "Chat Interface":
    st.header("💬 Chat with Multi-Agent System")
    
    # Agent/Playbook selection
    col1, col2 = st.columns(2)
    with col1:
        playbooks = ["None"] + [p["name"] for p in configs.get('playbooks', {}).get('playbooks', [])]
        selected_playbook = st.selectbox("Select Playbook", playbooks)
    
    with col2:
        agents = ["SuperAgent", "InspectorAgent", "JourneyAgent"]
        selected_agent = st.selectbox("Direct Agent (if no playbook)", agents)
    
    # File upload
    st.subheader("📎 Upload Files")
    uploaded_files = st.file_uploader(
        "Upload files for the agents to process", 
        accept_multiple_files=True,
        type=["txt", "py", "js", "html", "css", "json", "yaml", "jpg", "jpeg", "png", "pdf"]
    )
    
    # Process uploads
    uploaded_content = []
    if uploaded_files:
        for file in uploaded_files:
            try:
                # Handle text files
                if file.type.startswith('text/') or file.name.endswith(('.py', '.js', '.html', '.css', '.json', '.yaml')):
                    content = file.read().decode('utf-8')
                    uploaded_content.append({
                        'name': file.name,
                        'type': 'text',
                        'content': content
                    })
                    st.info(f"Text file processed: {file.name}")
                
                # Handle images
                elif file.type.startswith('image/'):
                    image = Image.open(file)
                    # Display preview
                    st.image(image, caption=file.name, width=200)
                    # Save for processing
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.type.split('/')[1]}") as tmp:
                        tmp.write(file.getvalue())
                        uploaded_content.append({
                            'name': file.name,
                            'type': 'image',
                            'path': tmp.name
                        })
                    st.info(f"Image processed: {file.name}")
                
                # Handle PDFs
                elif file.type == 'application/pdf':
                    # In a real app, you'd use PyPDF2 or similar
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(file.getvalue())
                        uploaded_content.append({
                            'name': file.name,
                            'type': 'pdf',
                            'path': tmp.name
                        })
                    st.info(f"PDF processed: {file.name}")
                    
            except Exception as e:
                st.error(f"Error processing file {file.name}: {str(e)}")
                
    # URL input
    url_input = st.text_input("Enter URL to process")
    if url_input:
        uploaded_content.append({
            'name': url_input,
            'type': 'url',
            'content': url_input
        })
    
    # Chat history display
    st.subheader("Chat History")
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.chat_history:
            if message['role'] == 'user':
                st.markdown(f"**You**: {message['content']}")
            else:
                st.markdown(f"**Agent**: {message['content']}")
    
    # Message input
    user_input = st.text_area("Enter your message")
    
    # Submit button
    if st.button("Send"):
        if user_input or uploaded_content:
            # Add user message to chat history
            message_content = user_input if user_input else "Uploaded files for processing"
            st.session_state.chat_history.append({
                'role': 'user',
                'content': message_content
            })
            
            # Log the interaction
            add_log(f"User input: {message_content[:50]}{'...' if len(message_content) > 50 else ''}")
            if uploaded_content:
                add_log(f"User uploaded {len(uploaded_content)} files")
            
            # In a real implementation, this would call your API
            # Simulate a response for now
            # Replace with API call when backend is ready:
            # response = run_api_request(
            #    "/api/chat",
            #    method="POST",
            #    data={
            #        "message": user_input,
            #        "playbook": selected_playbook if selected_playbook != "None" else None,
            #        "agent": selected_agent,
            #        "uploads": uploaded_content
            #    }
            # )
            
            # Placeholder response
            time.sleep(1)  # Simulate processing time
            agent_response = f"Received your message and {'files' if uploaded_content else 'input'}. Using {'playbook: ' + selected_playbook if selected_playbook != 'None' else 'agent: ' + selected_agent}."
            
            # Add agent response to chat history
            st.session_state.chat_history.append({
                'role': 'assistant',
                'content': agent_response
            })
            
            # Log the response
            add_log(f"Agent response: {agent_response[:50]}{'...' if len(agent_response) > 50 else ''}")
            
            # Refresh the UI
            st.experimental_rerun()

# Configuration Editor
elif page == "Configuration Editor":
    st.header("⚙️ Configuration Editor")
    
    # Select configuration type
    config_type = st.selectbox(
        "Select configuration type",
        ["agents", "tools", "playbooks"]
    )
    
    # Load current configuration if not in session
    if config_type not in st.session_state.config_editor:
        if config_type in configs:
            st.session_state.config_editor[config_type] = yaml.dump(configs[config_type])
        else:
            st.session_state.config_editor[config_type] = ""
    
    # Edit configuration
    st.subheader(f"Edit {config_type.capitalize()} Configuration")
    config_text = st.text_area(
        "YAML Configuration",
        st.session_state.config_editor[config_type],
        height=400
    )
    
    # Update and save buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Update Preview"):
            st.session_state.config_editor[config_type] = config_text
            try:
                parsed_config = yaml.safe_load(config_text)
                st.success("YAML is valid")
                st.json(parsed_config)
            except Exception as e:
                st.error(f"Invalid YAML: {str(e)}")
    
    with col2:
        if st.button("Save Configuration"):
            try:
                config_data = yaml.safe_load(config_text)
                save_config(config_type, config_data)
                configs[config_type] = config_data  # Update the loaded configs
            except Exception as e:
                st.error(f"Error saving configuration: {str(e)}")
    
    # Templates and Help
    with st.expander("Configuration Templates and Help"):
        if config_type == "agents":
            st.code("""
# Agent Role Template
agent_roles:
  - name: SuperAgent
    description: Coordinates workflows and manages task distribution
    capabilities:
      - workflow_management
      - task_distribution
    model: claude-3-sonnet
    system_prompt: |
      You are a Super Agent responsible for coordinating workflows.
            """, language="yaml")
            
        elif config_type == "tools":
            st.code("""
# Tool Template
tools:
  - name: web_search
    description: Search the web for information
    parameters:
      query: string
      max_results: integer
    implementation: core.tools.web_search.search
            """, language="yaml")
            
        elif config_type == "playbooks":
            st.code("""
# Playbook Template
playbooks:
  - name: data_analysis
    description: Analyze data with multiple agents
    workflow:
      - step_id: process_data
        type: parallel
        description: "Process data in parallel"
        agents:
          - InspectorAgent:validate
          - JourneyAgent:transform
    tools_allowed:
      - code_execution
    agents:
      - InspectorAgent
      - JourneyAgent
            """, language="yaml")

# Logs Viewer
elif page == "Logs Viewer":
    st.header("📋 System Logs")
    
    # Controls
    col1, col2 = st.columns([3, 1])
    with col1:
        log_filter = st.text_input("Filter logs", "")
    with col2:
        if st.button("Clear Logs"):
            st.session_state.logs = []
            st.experimental_rerun()
    
    # Display logs
    st.subheader("Log Entries")
    log_display = st.empty()
    
    # Filter and display logs
    filtered_logs = [log for log in st.session_state.logs if log_filter.lower() in log.lower()]
    log_display.text_area(
        "System logs",
        "\n".join(filtered_logs),
        height=400,
        disabled=True
    )

# Workflow Visualizer (Future Enhancement)
elif page == "Workflow Visualizer":
    st.header("🔄 Workflow Visualizer")
    
    st.warning("⚠️ This feature is under development")
    
    # ENHANCEMENT: Implement proper visualization of inter-agent behaviors
    st.markdown("""
    ### Planned Visualizer Features
    
    This module will visualize the complex agent interaction patterns:
    
    1. **Work-in-Parallel (agent-1=agent-n)**
       - Visual representation of concurrent agent execution
       - Input distribution and output aggregation visualization
    
    2. **Self-Feedback Loop (agent)**
       - Cycle visualization with iteration counters
       - Termination condition display
    
    3. **Partner-Feedback Loop (agent-1 -> agent-2 -> agent-1)**
       - Interactive diagram showing information flow between agents
       - Role highlighting for each iteration
    
    4. **Conditional Process**
       - Flowchart-style visualization of agent decision points
       - Branching paths based on conditions
    
    5. **Agent-versus-Agent**
       - Side-by-side comparison of competing agents
       - Turn-based interaction display
       - Scoring visualization
    
    6. **Handoff Pattern**
       - Sequential transfer visualization
       - Condition-based routing display
    
    This visualizer will be interactive, allowing users to:
    - Inspect agent inputs/outputs at each step
    - Watch workflow progress in real-time
    - Modify workflow configuration visually
    """)
    
    # Simple placeholder visualization
    st.subheader("Sample Workflow Diagram")
    
    # Use streamlit built-in visualization for now
    st.markdown("""
    ```mermaid
    graph TD
        A[Start] --> B[SuperAgent]
        B --> C{Decision Point}
        C -->|Technical| D[InspectorAgent]
        C -->|Creative| E[JourneyAgent]
        D --> F[Output]
        E --> F
    ```
    """)
    
    st.info("Full interactive workflow visualization will be implemented in the next iteration.")