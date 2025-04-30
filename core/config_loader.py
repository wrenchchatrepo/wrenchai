# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import yaml
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class ToolConfig(BaseModel):
    """Configuration for a tool that agents can use"""
    name: str
    description: str
    parameters: Dict[str, Any]
    implementation: str  # Python path to implementation

class AgentRoleConfig(BaseModel):
    """Configuration for an agent role"""
    name: str
    description: str
    capabilities: List[str]
    model: str
    system_prompt: str

class PlaybookConfig(BaseModel):
    """Configuration for a workflow playbook"""
    name: str
    description: str
    workflow: List[Dict[str, Any]]
    tools_allowed: List[str]
    agents: List[str]

class ToolDependency(BaseModel):
    """Dependency relationship between tools"""
    primary: str
    requires: str

class SystemConfig(BaseModel):
    """Root configuration container"""
    tools: List[ToolConfig]
    tool_dependencies: Optional[List[ToolDependency]] = []
    agent_roles: List[AgentRoleConfig]
    playbooks: List[PlaybookConfig]

def load_config(config_path: str) -> Dict[str, Any]:
    """Load a YAML configuration file"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def load_configs(config_dir: str) -> SystemConfig:
    """Load all configuration files from a directory"""
    if not os.path.isdir(config_dir):
        raise NotADirectoryError(f"Configuration directory not found: {config_dir}")
    
    # Load individual config files
    tools_config = load_config(os.path.join(config_dir, 'tools.yaml'))
    agents_config = load_config(os.path.join(config_dir, 'agents.yaml'))
    playbooks_config = load_config(os.path.join(config_dir, 'playbooks.yaml'))
    
    # Combine into a single SystemConfig
    return SystemConfig(
        tools=tools_config.get('tools', []),
        tool_dependencies=tools_config.get('tool_dependencies', []),
        agent_roles=agents_config.get('agent_roles', []),
        playbooks=playbooks_config.get('playbooks', [])
    )

def validate_playbook_configuration(playbook_config: Dict[str, Any], 
                                   tool_dependencies: List[Dict[str, str]]) -> bool:
    """Validate that a playbook has all required tool dependencies"""
    
    tools_allowed = set(playbook_config.get('tools_allowed', []))
    missing_dependencies = []
    
    # Check for missing dependencies
    for tool in tools_allowed:
        for dependency in tool_dependencies:
            if dependency['primary'] == tool and dependency['requires'] not in tools_allowed:
                missing_dependencies.append({
                    'tool': tool,
                    'missing': dependency['requires']
                })
    
    # Report any issues
    if missing_dependencies:
        errors = []
        for dep in missing_dependencies:
            errors.append(f"Tool '{dep['tool']}' requires '{dep['missing']}' but it's not in tools_allowed")
        
        raise ValueError(f"Playbook '{playbook_config['name']}' has missing dependencies: {', '.join(errors)}")
    
    # Validate agent-LLM mappings if present
    if 'agent_llms' in playbook_config:
        try:
            # Import here to avoid circular imports
            from core.agents.agent_definitions import AGENTS
            from core.agents.agent_llm_mapping import agent_llm_manager
            
            # Check that all agents in the mapping exist in the playbook
            playbook_agents = set(playbook_config.get('agents', []))
            for agent_name in playbook_config['agent_llms']:
                if agent_name not in playbook_agents:
                    raise ValueError(f"Agent-LLM mapping references non-existent agent '{agent_name}'")
                
                # Check that the agent is defined in agent_definitions
                if agent_name not in AGENTS:
                    raise ValueError(f"Agent '{agent_name}' not found in agent definitions")
                    
                # Verify LLM ID (warning only)
                llm_id = playbook_config['agent_llms'][agent_name]
                if not agent_llm_manager.check_llm_availability(llm_id):
                    import logging
                    logging.warning(f"Agent-LLM mapping for '{agent_name}' uses LLM '{llm_id}' which may not be available")
                    
        except ImportError:
            # If we can't import the modules, skip this validation
            import logging
            logging.warning("Could not import agent modules for validation, skipping agent-LLM mapping checks")
    
    return True