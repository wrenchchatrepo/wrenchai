# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import yaml
import logging
from typing import Dict, List, Any, Optional, Callable
from pydantic_ai import Model, field
from core.config_loader import load_config, validate_playbook_configuration

class Agent(Model):
    """Base agent class powered by Pydantic-AI"""
    role: str
    state: Dict[str, Any] = {}
    assigned_tools: List[str] = []
    
    @field.function
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data according to agent role"""
        # This will be implemented by the LLM
        pass
    
    @field.function
    def use_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Use a tool from the available toolset"""
        # This will be implemented by the LLM
        pass
    
    @field.function
    def update_beliefs(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Update belief state with new evidence"""
        # This will be implemented by the LLM
        pass

class AgentManager:
    """Factory and orchestrator for agent instances"""
    
    def __init__(self, config_dir: str = "core/configs"):
        """Initialize the agent manager with configuration"""
        self.config_dir = config_dir
        self.agents = {}
        self.tool_registry = None  # Will be set by the system
        
        # Load configurations
        self.agent_configs = load_config(os.path.join(config_dir, "agents.yaml"))
        self.playbook_configs = load_config(os.path.join(config_dir, "playbooks.yaml"))
        self.tool_configs = load_config(os.path.join(config_dir, "tools.yaml"))
        
        # Extract tool dependencies
        self.tool_dependencies = self.tool_configs.get('tool_dependencies', [])
    
    def set_tool_registry(self, tool_registry):
        """Set the tool registry for this agent manager"""
        self.tool_registry = tool_registry
    
    def initialize_agent(self, role_name: str) -> Agent:
        """Initialize an agent with a specific role"""
        # Find the role configuration
        role_config = next((r for r in self.agent_configs['agent_roles'] 
                            if r['name'] == role_name), None)
        
        if not role_config:
            raise ValueError(f"Agent role not found: {role_name}")
        
        # Create the agent instance
        agent = Agent(role=role_name)
        
        # Store the agent
        agent_id = id(agent)
        self.agents[agent_id] = agent
        
        return agent
    
    def assign_tools_to_agent(self, agent_id: str, tool_names: List[str]) -> None:
        """Assign tools to an agent, automatically including dependencies"""
        
        if agent_id not in self.agents:
            raise ValueError(f"Agent not found: {agent_id}")
        
        # Start with explicitly requested tools
        final_tool_names = set(tool_names)
        
        # Add required dependencies
        for tool_name in tool_names:
            for dependency in self.tool_dependencies:
                if dependency['primary'] == tool_name:
                    # Add the required dependency
                    required_tool = dependency['requires']
                    final_tool_names.add(required_tool)
                    logging.info(f"Auto-adding required dependency {required_tool} for {tool_name}")
        
        # Assign final tool set to agent
        self.agents[agent_id].assigned_tools = list(final_tool_names)
        
        logging.info(f"Agent {agent_id} assigned tools: {self.agents[agent_id].assigned_tools}")
    
    async def run_workflow(self, playbook_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run a workflow defined in a playbook"""
        # Find the playbook
        playbook = next((p for p in self.playbook_configs['playbooks'] 
                         if p['name'] == playbook_name), None)
        
        if not playbook:
            raise ValueError(f"Playbook not found: {playbook_name}")
        
        # Validate the playbook configuration
        validate_playbook_configuration(playbook, self.tool_dependencies)
        
        # Create workflow context
        context = {"input": input_data, "output": {}, "state": {}}
        
        # Initialize agents required for this playbook
        workflow_agents = {}
        for agent_role in playbook['agents']:
            agent = self.initialize_agent(agent_role)
            workflow_agents[agent_role] = agent
            
            # Assign tools to the agent
            self.assign_tools_to_agent(id(agent), playbook['tools_allowed'])
        
        # Execute workflow steps
        current_step = self._get_initial_step(playbook)
        while current_step:
            # Execute the step
            step_result = await self._execute_step(current_step, context, workflow_agents)
            
            # Update context with step result
            context['state'][current_step['step_id']] = step_result
            
            # Get the next step
            current_step = self._get_next_step(playbook, current_step, context)
        
        # Return the final output
        return context['output']
    
    def _get_initial_step(self, playbook: Dict[str, Any]) -> Dict[str, Any]:
        """Get the initial step of a playbook"""
        # For now, just return the first step
        return playbook['workflow'][0] if playbook['workflow'] else None
    
    def _get_next_step(self, playbook: Dict[str, Any], 
                      current_step: Dict[str, Any], 
                      context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get the next step based on the current step and context"""
        if 'next' not in current_step:
            # This is the last step
            return None
        
        next_step_id = current_step['next']
        return next((step for step in playbook['workflow'] 
                    if step['step_id'] == next_step_id), None)
    
    async def _execute_step(self, step: Dict[str, Any], 
                          context: Dict[str, Any],
                          workflow_agents: Dict[str, Agent]) -> Dict[str, Any]:
        """Execute a workflow step based on its type"""
        step_type = step.get('type', 'standard')
        
        if step_type == 'standard':
            return await self._execute_standard_step(step, context, workflow_agents)
            
        elif step_type == 'parallel':
            return await self._execute_parallel_step(step, context, workflow_agents)
            
        elif step_type == 'partner_loop':
            return await self._execute_partner_loop(step, context, workflow_agents)
            
        else:
            raise ValueError(f"Unknown step type: {step_type}")
    
    async def _execute_standard_step(self, step: Dict[str, Any], 
                                   context: Dict[str, Any],
                                   workflow_agents: Dict[str, Agent]) -> Dict[str, Any]:
        """Execute a standard workflow step"""
        agent_role = step['agent']
        agent = workflow_agents[agent_role]
        
        # Prepare input data for this step
        step_input = {
            "operation": step['operation'],
            "context": context,
            "step": step
        }
        
        # Process the step with the agent
        result = await agent.process(step_input)
        
        return result
    
    async def _execute_parallel_step(self, step: Dict[str, Any],
                                   context: Dict[str, Any],
                                   workflow_agents: Dict[str, Agent]) -> Dict[str, Any]:
        """Execute a parallel workflow step with multiple agents"""
        # This is a simplified implementation - in a real system, 
        # you would use asyncio.gather() for true parallel execution
        
        results = {}
        for agent_spec in step['agents']:
            # Parse agent spec (format: "AgentName:operation")
            parts = agent_spec.split(':')
            agent_role = parts[0]
            operation = parts[1] if len(parts) > 1 else "process"
            
            agent = workflow_agents[agent_role]
            
            # Prepare input for this agent
            agent_input = {
                "operation": operation,
                "context": context,
                "step": step
            }
            
            # Process with the agent
            result = await agent.process(agent_input)
            results[agent_role] = result
        
        # Combine results according to the aggregation strategy
        if 'output_aggregation' in step:
            strategy = step['output_aggregation']['strategy']
            # Implement different aggregation strategies here
            # For now, just return all results
        
        return results
    
    async def _execute_partner_loop(self, step: Dict[str, Any],
                                  context: Dict[str, Any],
                                  workflow_agents: Dict[str, Agent]) -> Dict[str, Any]:
        """Execute a partner loop workflow where agents collaborate iteratively"""
        iterations = step.get('iterations', 3)
        roles = step['roles']
        agents_map = step['agents']
        
        results = []
        current_state = context.copy()
        
        for i in range(iterations):
            iteration_results = {}
            
            for role_config in roles:
                role = role_config['role']
                operation = role_config['operation']
                
                agent_role = agents_map[role]
                agent = workflow_agents[agent_role]
                
                # Prepare input for this role
                role_input = {
                    "operation": operation,
                    "context": current_state,
                    "iteration": i,
                    "step": step
                }
                
                # Process with the agent
                result = await agent.process(role_input)
                iteration_results[role] = result
                
                # Update the state for the next role
                current_state = {**current_state, "previous_result": result}
            
            results.append(iteration_results)
            
            # Check for early termination condition if specified
            if 'termination_condition' in step:
                # Placeholder for termination condition evaluation
                # In a real implementation, this would evaluate the condition
                pass
        
        return {
            "iterations": results,
            "final_state": current_state
        }