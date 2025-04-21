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
import logging
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("wrenchai-ui.log")
    ]
)
logger = logging.getLogger("wrenchai-ui")

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'config_editor' not in st.session_state:
    st.session_state.config_editor = {}
if 'output' not in st.session_state:
    st.session_state.output = []

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
    logger.info(f"Configuration saved to {path}")
    
def add_log(message):
    """Add a message to the logs"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    st.session_state.logs.append(log_entry)
    logger.info(message)

def add_output(content, type="text"):
    """Add content to the output panel"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    st.session_state.output.append({
        "timestamp": timestamp,
        "type": type,
        "content": content
    })

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
    ["Chat Interface", "Configuration Editor", "Logs Viewer", "Output Viewer"]
)

# Chat Interface
if page == "Chat Interface":
    st.header("💬 Chat with Multi-Agent System")
    
    # Create two columns for chat and output
    chat_col, upload_col = st.columns([2, 1])
    
    with chat_col:
        # Agent/Playbook selection
        col1, col2 = st.columns(2)
        with col1:
            playbooks = ["None"] + [p["name"] for p in configs.get('playbooks', {}).get('playbooks', [])]
            selected_playbook = st.selectbox("Select Playbook", playbooks)
        
        with col2:
            agents = ["SuperAgent", "InspectorAgent", "JourneyAgent", "WebResearcher", 
                     "CodeGenerator", "UXDesigner", "DevOps", "DataScientist",
                     "Codifier", "InfoSec", "Comptroller", "TestEngineer", "DBA"]
            selected_agent = st.selectbox("Direct Agent (if no playbook)", agents)
        
        # Chat history display
        st.subheader("Chat History")
        chat_container = st.container(height=400)
        
        with chat_container:
            for message in st.session_state.chat_history:
                if message['role'] == 'user':
                    st.markdown(f"**You**: {message['content']}")
                else:
                    st.markdown(f"**Agent**: {message['content']}")
        
        # Message input
        user_input = st.text_area("Enter your message", height=100)
        
        # Submit button
        if st.button("Send"):
            if user_input:
                # Add user message to chat history
                st.session_state.chat_history.append({
                    'role': 'user',
                    'content': user_input
                })
                
                # Log the interaction
                add_log(f"User input: {user_input[:50]}{'...' if len(user_input) > 50 else ''}")
                
                # In a real implementation, this would call your API
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
                agent_response = f"Received your message. Using {'playbook: ' + selected_playbook if selected_playbook != 'None' else 'agent: ' + selected_agent}."
                
                # Add agent response to chat history
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': agent_response
                })
                
                # Log the response and add to output panel
                add_log(f"Agent response: {agent_response[:50]}{'...' if len(agent_response) > 50 else ''}")
                add_output(f"Agent response: {agent_response}")
                
                # Refresh the UI
                st.experimental_rerun()
    
    with upload_col:
        # File upload panel
        st.subheader("📎 Upload Files")
        uploaded_files = st.file_uploader(
            "Upload files for processing", 
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
                        add_log(f"Uploaded text file: {file.name}")
                    
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
                        add_log(f"Uploaded image: {file.name}")
                    
                    # Handle PDFs
                    elif file.type == 'application/pdf':
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp.write(file.getvalue())
                            uploaded_content.append({
                                'name': file.name,
                                'type': 'pdf',
                                'path': tmp.name
                            })
                        st.info(f"PDF processed: {file.name}")
                        add_log(f"Uploaded PDF: {file.name}")
                        
                    # Store in output panel
                    add_output(f"Uploaded {file.name}: {file.type}")
                except Exception as e:
                    st.error(f"Error processing file {file.name}: {str(e)}")
                    add_log(f"Error processing file {file.name}: {str(e)}")
                    
        # URL input
        st.subheader("🔗 URL Input")
        url_input = st.text_input("Enter URL to process")
        if url_input and st.button("Process URL"):
            uploaded_content.append({
                'name': url_input,
                'type': 'url',
                'content': url_input
            })
            st.info(f"URL added for processing: {url_input}")
            add_log(f"Added URL for processing: {url_input}")
            add_output(f"Added URL: {url_input}")
            
        # Manual integration options (for future enhancement)
        st.markdown("---")
        st.markdown("### ⚠️ Advanced Options (Future Enhancement)")
        st.info("Integration with external knowledge bases, agents, and systems will be added in future updates")

# Configuration Editor
elif page == "Configuration Editor":
    st.header("⚙️ Configuration Editor")
    
    # Create tabs for different config types
    config_tabs = st.tabs(["Agents", "Tools", "Playbooks", "Custom Config"])
    
    # Agents tab
    with config_tabs[0]:
        config_type = "agents"
        
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
            if st.button(f"Update {config_type.capitalize()} Preview"):
                st.session_state.config_editor[config_type] = config_text
                try:
                    parsed_config = yaml.safe_load(config_text)
                    st.success("YAML is valid")
                    st.json(parsed_config)
                    add_log(f"Updated {config_type} configuration preview")
                except Exception as e:
                    st.error(f"Invalid YAML: {str(e)}")
                    add_log(f"Error in {config_type} YAML: {str(e)}")
        
        with col2:
            if st.button(f"Save {config_type.capitalize()} Configuration"):
                try:
                    config_data = yaml.safe_load(config_text)
                    save_config(config_type, config_data)
                    configs[config_type] = config_data  # Update the loaded configs
                    add_log(f"Saved {config_type} configuration")
                    add_output(f"Saved {config_type} configuration file")
                except Exception as e:
                    st.error(f"Error saving configuration: {str(e)}")
                    add_log(f"Error saving {config_type} configuration: {str(e)}")
        
        # Templates and Help
        with st.expander("Agent Configuration Templates and Help"):
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
    
    # Tools tab
    with config_tabs[1]:
        config_type = "tools"
        
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
            if st.button(f"Update {config_type.capitalize()} Preview"):
                st.session_state.config_editor[config_type] = config_text
                try:
                    parsed_config = yaml.safe_load(config_text)
                    st.success("YAML is valid")
                    st.json(parsed_config)
                    add_log(f"Updated {config_type} configuration preview")
                except Exception as e:
                    st.error(f"Invalid YAML: {str(e)}")
                    add_log(f"Error in {config_type} YAML: {str(e)}")
        
        with col2:
            if st.button(f"Save {config_type.capitalize()} Configuration"):
                try:
                    config_data = yaml.safe_load(config_text)
                    save_config(config_type, config_data)
                    configs[config_type] = config_data  # Update the loaded configs
                    add_log(f"Saved {config_type} configuration")
                    add_output(f"Saved {config_type} configuration file")
                except Exception as e:
                    st.error(f"Error saving configuration: {str(e)}")
                    add_log(f"Error saving {config_type} configuration: {str(e)}")
        
        # Templates and Help
        with st.expander("Tool Configuration Templates and Help"):
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
    
    # Playbooks tab
    with config_tabs[2]:
        config_type = "playbooks"
        
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
            if st.button(f"Update {config_type.capitalize()} Preview"):
                st.session_state.config_editor[config_type] = config_text
                try:
                    parsed_config = yaml.safe_load(config_text)
                    st.success("YAML is valid")
                    st.json(parsed_config)
                    add_log(f"Updated {config_type} configuration preview")
                except Exception as e:
                    st.error(f"Invalid YAML: {str(e)}")
                    add_log(f"Error in {config_type} YAML: {str(e)}")
        
        with col2:
            if st.button(f"Save {config_type.capitalize()} Configuration"):
                try:
                    config_data = yaml.safe_load(config_text)
                    save_config(config_type, config_data)
                    configs[config_type] = config_data  # Update the loaded configs
                    add_log(f"Saved {config_type} configuration")
                    add_output(f"Saved {config_type} configuration file")
                except Exception as e:
                    st.error(f"Error saving configuration: {str(e)}")
                    add_log(f"Error saving {config_type} configuration: {str(e)}")
        
        # Templates and Help
        with st.expander("Playbook Configuration Templates and Help"):
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
    
    # Custom Config tab
    with config_tabs[3]:
        st.subheader("Create/Edit Custom Configuration")
        
        # Input fields
        custom_config_name = st.text_input("Configuration File Name (without .yaml extension)")
        custom_config_path = f"../core/configs/{custom_config_name}.yaml" if custom_config_name else ""
        
        # Load existing config if available
        custom_config_content = ""
        if custom_config_name and os.path.exists(custom_config_path):
            try:
                with open(custom_config_path, 'r') as f:
                    custom_config_content = f.read()
                st.success(f"Loaded existing configuration: {custom_config_path}")
            except Exception as e:
                st.error(f"Error loading configuration: {str(e)}")
        
        # Edit custom configuration
        custom_config_text = st.text_area(
            "Custom YAML Configuration",
            custom_config_content,
            height=400
        )
        
        # Update and save buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Validate Custom Config"):
                try:
                    if not custom_config_name:
                        st.error("Please enter a configuration file name")
                    else:
                        parsed_config = yaml.safe_load(custom_config_text)
                        st.success("YAML is valid")
                        st.json(parsed_config)
                        add_log(f"Validated custom configuration: {custom_config_name}")
                except Exception as e:
                    st.error(f"Invalid YAML: {str(e)}")
                    add_log(f"Error in custom YAML: {str(e)}")
        
        with col2:
            if st.button("Save Custom Config"):
                try:
                    if not custom_config_name:
                        st.error("Please enter a configuration file name")
                    else:
                        # Ensure directory exists
                        os.makedirs(os.path.dirname(custom_config_path), exist_ok=True)
                        
                        # Save the configuration
                        with open(custom_config_path, 'w') as f:
                            f.write(custom_config_text)
                        
                        st.success(f"Saved configuration to {custom_config_path}")
                        add_log(f"Saved custom configuration: {custom_config_name}.yaml")
                        add_output(f"Saved custom configuration file: {custom_config_name}.yaml")
                except Exception as e:
                    st.error(f"Error saving configuration: {str(e)}")
                    add_log(f"Error saving custom configuration: {str(e)}")

# Logs Viewer
elif page == "Logs Viewer":
    st.header("📋 System Logs")
    
    # Controls
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        log_filter = st.text_input("Filter logs", "")
    with col2:
        if st.button("Refresh Logs"):
            st.experimental_rerun()
    with col3:
        if st.button("Clear Logs"):
            st.session_state.logs = []
            st.experimental_rerun()
    
    # Display logs
    st.subheader("Log Entries")
    log_display = st.empty()
    
    # Filter and display logs
    filtered_logs = [log for log in st.session_state.logs if log_filter.lower() in log.lower()]
    filtered_logs.reverse()  # Show newest first
    
    log_display.text_area(
        "System logs",
        "\n".join(filtered_logs),
        height=600,
        disabled=True
    )
    
    # Log file details
    with st.expander("Log File Information"):
        st.info("Logs are stored in wrenchai-ui.log and also displayed here")
        if os.path.exists("wrenchai-ui.log"):
            st.code(f"Log file size: {os.path.getsize('wrenchai-ui.log')} bytes")
            st.download_button(
                "Download Log File", 
                open("wrenchai-ui.log", "r").read(),
                "wrenchai-ui.log",
                "text/plain"
            )

# Output Viewer
elif page == "Output Viewer":
    st.header("📤 Agent System Output")
    
    # Controls
    col1, col2 = st.columns([3, 1])
    with col1:
        output_filter = st.text_input("Filter output", "")
    with col2:
        if st.button("Clear Output"):
            st.session_state.output = []
            st.experimental_rerun()
    
    # Display output items in reverse order (newest first)
    output_items = st.session_state.output.copy()
    output_items.reverse()
    
    # Filter outputs based on text input
    filtered_outputs = [
        output for output in output_items 
        if output_filter.lower() in output["content"].lower()
    ]
    
    # Show outputs
    if not filtered_outputs:
        st.info("No output items to display")
    else:
        for item in filtered_outputs:
            with st.expander(f"{item['timestamp']} - {item['type']} output", expanded=True):
                if item["type"] == "text":
                    st.markdown(item["content"])
                elif item["type"] == "image":
                    # This would display image if we had image outputs
                    st.markdown(f"*Image output - {item['content']}*")
                elif item["type"] == "json":
                    try:
                        # Format JSON outputs nicely
                        st.json(json.loads(item["content"]))
                    except:
                        st.text(item["content"])
                else:
                    st.text(item["content"])
    
    # Output Settings - Future enhancement 
    st.markdown("---")
    st.markdown("### ⚠️ Output Settings (Future Enhancement)")
    col1, col2 = st.columns(2)
    with col1:
        st.info("Auto-refresh: This setting will automatically refresh the output panel at regular intervals")
    with col2:
        st.info("Output format preferences: Configure how different output types are displayed")