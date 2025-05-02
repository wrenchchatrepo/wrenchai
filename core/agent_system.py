# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import yaml
import logging
from typing import Dict, List, Any, Optional, Callable, TypeVar, Generic, Union
from dataclasses import dataclass
# Import Pydantic AI's Agent and RunContext for LLM agent functionality
# Reference: https://ai.pydantic.dev/agents/
from pydantic_ai import Agent as PydanticAgent, RunContext, Agent
from typing import Optional, List
import asyncio

# Try to import MCP components
try:
    # Import Pydantic AI's MCP server interfaces for multi-component processing
    # Reference: https://ai.pydantic.dev/agents/#agents-are-designed-for-reuse-like-fastapi-apps
    from pydantic_ai.mcp import MCPServerHTTP, MCPServerStdio
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
from pydantic import BaseModel
from core.config_loader import load_config, validate_playbook_configuration

# Define dependency and output types
T = TypeVar('T')  # For dependencies
O = TypeVar('O')  # For output

@dataclass
class AgentDependencies:
    """Dependencies for agents"""
    tool_registry: Any = None
    bayesian_engine: Any = None

class ToolSuccess(BaseModel, Generic[T]):
    """Successful result from a tool execution"""
    data: Union[T, Dict[str, Any]]

class ToolError(BaseModel):
    """Error result from a tool execution
    
    This is a Pydantic BaseModel representing an error returned by a tool.
    See Pydantic AI tools documentation: https://ai.pydantic.dev/agents/#function-tool-tools
    """
    error: str
    details: Optional[Dict[str, Any]] = None

# Define tool result as a union of success and error
ToolResult = Union[ToolSuccess, ToolError]

class AgentWrapper(Generic[T, O]):
    """Base agent wrapper class powered by Pydantic-AI"""
    
    def __init__(self, 
                role: str, 
                model: str,
                instructions: str,
                dependencies: Optional[T] = None,
                tools: Optional[List[str]] = None,
                mcp_servers: Optional[List[Union[MCPServerHTTP, MCPServerStdio]]] = None):
        """Initialize a Pydantic-AI agent
        
        Args:
            role: The agent's role name
            model: The LLM model to use (e.g., 'claude-3-sonnet')
            instructions: Agent behavior instructions
            dependencies: Optional dependencies for the agent
            tools: Optional list of tool names that the agent can use
            mcp_servers: Optional list of MCP servers to attach to the agent
        """
        self.role = role
        self.state = {}
        self.assigned_tools = tools or []
        self.mcp_servers = mcp_servers or []
        
        # Create the Pydantic-AI agent
        self.agent = PydanticAgent(
            model,
            deps_type=T,
            output_type=O,
            instructions=instructions
        )
        
        # Store dependencies
        self.dependencies = dependencies
        
        # Register tools methods
        self._register_tools()
        
    def _register_tools(self):
        """Register tools with the agent"""
        
        @self.agent.tool
        async def use_tool(ctx: RunContext[T], tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
            """Use a tool from the available toolset
            
            Args:
                tool_name: The name of the tool to use
                parameters: The parameters to pass to the tool
                
            Returns:
                Either a ToolSuccess with the tool's result data or a ToolError with error details
            """
            if tool_name not in self.assigned_tools:
                return ToolError(
                    error=f"Tool '{tool_name}' is not available to this agent",
                    details={"available_tools": self.assigned_tools}
                )
                
            try:
                # Get the tool registry from dependencies
                tool_registry = ctx.deps.tool_registry
                if tool_registry is None:
                    return ToolError(
                        error="Tool registry not available"
                    )
                    
                # Get the tool function
                tool_func = tool_registry.get_tool(tool_name)
                
                # Execute the tool
                result = await tool_func(**parameters)
                return ToolSuccess(data=result)
            except Exception as e:
                return ToolError(
                    error=f"Error executing tool '{tool_name}'",
                    details={"exception": str(e), "parameters": parameters}
                )
        
        @self.agent.tool
        async def update_beliefs(ctx: RunContext[T], evidence: Dict[str, Any]) -> ToolResult:
            """Update belief state with new evidence"""
            try:
                # Get the Bayesian engine from dependencies
                bayesian_engine = ctx.deps.bayesian_engine
                if bayesian_engine is None:
                    return ToolResult(
                        success=False,
                        data={},
                        error="Bayesian engine not available"
                    )
                
                # Create or update a model if specified
                if "model_name" in evidence and "variables" in evidence:
                    bayesian_engine.create_model(
                        evidence["model_name"], 
                        evidence["variables"]
                    )
                    
                # Update beliefs if model and evidence provided
                if "model" in evidence and "data" in evidence:
                    updated_beliefs = bayesian_engine.update_beliefs(
                        evidence["model"], 
                        evidence["data"]
                    )
                    return ToolResult(success=True, data=updated_beliefs)
                    
                # Store in local state otherwise
                self.state.update(evidence)
                return ToolResult(success=True, data=self.state)
            except Exception as e:
                return ToolResult(success=False, data={}, error=str(e))
    
    @property
    def system_prompt(self):
        """Get the system prompt for this agent"""
        return self.agent.instructions
                
    async def process(self, input_data: Dict[str, Any], message_history=None) -> O:
        """Process input data according to agent role
        
        Args:
            input_data: The input data to process
            message_history: Optional message history to provide conversation context
        """
        if self.mcp_servers and MCP_AVAILABLE:
            # Run with MCP servers if available
            async with self.agent.run_mcp_servers(*self.mcp_servers):
                return await self.agent.run(
                    self.dependencies, 
                    input_data, 
                    message_history=message_history
                )
        else:
            # Run without MCP servers
            return await self.agent.run(
                self.dependencies, 
                input_data, 
                message_history=message_history
            )
        
    async def process_stream(self, input_data: Dict[str, Any], message_history=None):
        """Process input data and stream the response
        
        Args:
            input_data: The input data to process
            message_history: Optional message history to provide conversation context
        """
        if self.mcp_servers and MCP_AVAILABLE:
            # Stream with MCP servers if available
            async with self.agent.run_mcp_servers(*self.mcp_servers):
                async for chunk in self.agent.run_stream(
                    self.dependencies, 
                    input_data, 
                    message_history=message_history
                ):
                    yield chunk
        else:
            # Stream without MCP servers
            async for chunk in self.agent.run_stream(
                self.dependencies, 
                input_data, 
                message_history=message_history
            ):
                yield chunk
            
    def get_message_history(self):
        """Get the message history from the agent's last run"""
        return self.agent.messages
        
    def get_new_messages(self):
        """Get only the new messages from the agent's last run"""
        return self.agent.messages.new_messages()

class AgentManager:
    """Factory and orchestrator for agent instances"""
    
    def __init__(self, config_dir: str = "core/configs"):
        """Initialize the agent manager with configuration"""
        self.config_dir = config_dir
        self.agents = {}
        self.tool_registry = None  # Will be set by the system
        self.bayesian_engine = None  # Will be set by the system
        
        # Load configurations
        self.agent_configs = load_config(os.path.join(config_dir, "agents.yaml"))
        self.playbook_configs = load_config(os.path.join(config_dir, "playbooks.yaml"))
        self.tool_configs = load_config(os.path.join(config_dir, "tools.yaml"))
        
        # Extract tool dependencies
        self.tool_dependencies = self.tool_configs.get('tool_dependencies', [])
        
        # Enable instrumentation for all agents
        try:
            Agent.instrument_all()
            logging.info("Pydantic AI agent instrumentation enabled")
        except Exception as e:
            logging.warning(f"Failed to enable agent instrumentation: {e}")
    
    def set_tool_registry(self, tool_registry):
        """Set the tool registry for this agent manager"""
        self.tool_registry = tool_registry
    
    def set_bayesian_engine(self, bayesian_engine):
        """Set the Bayesian engine for this agent manager"""
        self.bayesian_engine = bayesian_engine
    
    def initialize_agent(self, role_name: str, mcp_servers: Optional[List[str]] = None) -> AgentWrapper:
        """
        Initializes and configures an agent for a specified role.
        
        Creates an agent with the given role, attaches dependencies and optional MCP servers, applies any LLM override from agent-LLM mapping if available, and initializes agent state if supported.
        
        Args:
            role_name: The name of the agent role to initialize.
            mcp_servers: Optional list of MCP server names to attach to the agent.
        
        Returns:
            An AgentWrapper instance representing the initialized agent.
        
        Raises:
            ValueError: If the specified agent role is not found.
        """
        # Find the role configuration
        role_config = next((r for r in self.agent_configs['agent_roles'] 
                            if r['name'] == role_name), None)
        
        if not role_config:
            raise ValueError(f"Agent role not found: {role_name}")
        
        # Create dependencies
        dependencies = AgentDependencies(
            tool_registry=self.tool_registry,
            bayesian_engine=self.bayesian_engine
        )
        
        # Prepare MCP servers if requested
        attached_mcp_servers = []
        if mcp_servers and MCP_AVAILABLE:
            # Import MCP client manager
            from core.tools.mcp_client import get_mcp_manager
            
            # Get MCP server instances
            manager = get_mcp_manager("mcp_config.json")
            for server_name in mcp_servers:
                server = manager.get_server_from_config(server_name)
                if server:
                    attached_mcp_servers.append(server)
                    logging.info(f"Attached MCP server '{server_name}' to agent with role '{role_name}'")
        
        # Check for LLM override from agent-LLM mapping
        model = role_config['model']
        try:
            # Import here to avoid circular imports
            from core.agents.agent_llm_mapping import agent_llm_manager
            llm_id = agent_llm_manager.get_agent_llm(role_name)
            if llm_id:
                # Override the model with the mapped LLM
                model = llm_id
                logging.info(f"Using LLM '{llm_id}' for agent with role '{role_name}' (from mapping)")
        except ImportError:
            # If the mapping module is not available, use default model
            pass
        
        # Create the agent instance
        agent = AgentWrapper[AgentDependencies, Dict[str, Any]](
            role=role_name,
            model=model,
            instructions=role_config['system_prompt'],
            dependencies=dependencies,
            mcp_servers=attached_mcp_servers
        )
        
        # Store the agent
        agent_id = id(agent)
        self.agents[agent_id] = agent
        
        # Initialize agent state if available
        try:
            from core.agents.agent_state import agent_state_manager
            agent_state_manager.get_agent_state(str(agent_id)).agent_name = role_name
        except ImportError:
            # If the state manager is not available, continue without it
            pass
        
        return agent
    
    def assign_tools_to_agent(self, agent_id: str, tool_names: List[str]) -> None:
        """
        Assigns a set of tools to an agent, automatically including any required tool dependencies.
        
        If a tool has dependencies specified in the tool dependency list, those dependencies are also assigned to the agent. Replaces the agent instance with a new one configured with the updated tool set.
        
        Args:
            agent_id: The identifier of the agent to update.
            tool_names: List of tool names to assign to the agent.
        
        Raises:
            ValueError: If the specified agent ID does not exist.
        """
        
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
        
        # Create a new agent with the assigned tools
        agent = self.agents[agent_id]
        role_config = next((r for r in self.agent_configs['agent_roles'] 
                            if r['name'] == agent.role), None)
        
        # Create a new agent with updated tools
        new_agent = AgentWrapper[AgentDependencies, Dict[str, Any]](
            role=agent.role,
            model=role_config['model'],
            instructions=role_config['system_prompt'],
            dependencies=agent.dependencies,
            tools=list(final_tool_names)
        )
        
        # Replace the agent in the registry
        self.agents[agent_id] = new_agent
        
        logging.info(f"Agent {agent_id} assigned tools: {new_agent.assigned_tools}")
    
    async def run_workflow(self, playbook_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a workflow defined in a playbook using the specified input data.
        
        Initializes agents, assigns tools, registers agent-LLM mappings if present, and sequentially executes workflow steps as defined in the playbook. Returns the final output produced by the workflow.
        
        Args:
            playbook_name: The name of the playbook to execute.
            input_data: Input data to be provided to the workflow.
        
        Returns:
            The output dictionary resulting from the workflow execution.
        
        Raises:
            ValueError: If the specified playbook is not found.
        """
        # Find the playbook
        playbook = next((p for p in self.playbook_configs['playbooks'] 
                         if p['name'] == playbook_name), None)
        
        if not playbook:
            raise ValueError(f"Playbook not found: {playbook_name}")
        
        # Validate the playbook configuration
        validate_playbook_configuration(playbook, self.tool_dependencies)
        
        # Create workflow context
        context = {"input": input_data, "output": {}, "state": {}}
        
        # Check for agent-LLM mappings in the playbook
        try:
            from core.agents.agent_llm_mapping import agent_llm_manager
            if 'agent_llms' in playbook:
                # Register the agent-LLM mappings from the playbook
                agent_llm_manager.add_mappings_from_playbook(playbook['agent_llms'], playbook_name)
                logging.info(f"Registered agent-LLM mappings from playbook {playbook_name}")
        except ImportError:
            logging.warning("Agent-LLM mapping module not available")
        
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
        """
                          Executes a workflow step according to its specified type.
                          
                          Dispatches the step to the appropriate handler based on its type, supporting standard, parallel, partner feedback loop, process, and handoff step types. Raises a ValueError if the step type is unrecognized.
                          
                          Args:
                              step: The workflow step definition.
                              context: The current workflow context.
                              workflow_agents: Mapping of agent names to agent instances.
                          
                          Returns:
                              The updated workflow context after executing the step.
                          
                          Raises:
                              ValueError: If the step type is unknown.
                          """
        step_type = step.get('type', 'standard')
        
        if step_type == 'standard':
            return await self._execute_standard_step(step, context, workflow_agents)
            
        elif step_type == 'work_in_parallel':
            return await self._execute_parallel_step(step, context, workflow_agents)
            
        elif step_type == 'partner_feedback_loop':
            return await self._execute_partner_loop(step, context, workflow_agents)
            
        elif step_type == 'process':
            return await self._execute_process_step(step, context, workflow_agents)
            
        elif step_type == 'handoff':
            return await self._execute_handoff_step(step, context, workflow_agents)
            
        else:
            raise ValueError(f"Unknown step type: {step_type}")
    
    async def _execute_standard_step(self, step: Dict[str, Any], 
                                   context: Dict[str, Any],
                                   workflow_agents: Dict[str, Agent]) -> Dict[str, Any]:
        """
                                   Executes a standard workflow step by invoking the specified agent's operation.
                                   
                                   Args:
                                       step: The workflow step definition containing the agent role and operation.
                                       context: The current workflow context passed to the agent.
                                       workflow_agents: Mapping of agent roles to agent instances.
                                   
                                   Returns:
                                       The result produced by the agent for this workflow step.
                                   """
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
        """
                                   Executes a parallel workflow step by running multiple agent operations concurrently.
                                   
                                   Each agent specified in the step is invoked with the provided context and operation. Results are aggregated according to the specified output aggregation strategy, or returned as a list by default.
                                   
                                   Args:
                                       step: The workflow step definition containing agent specifications and optional output aggregation strategy.
                                       context: The current workflow context shared among agents.
                                       workflow_agents: A mapping of agent role names to agent instances.
                                   
                                   Returns:
                                       A dictionary containing the aggregated results from all agents, either as a combined dictionary or a list, depending on the aggregation strategy.
                                   """
        tasks = []
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
            
            # Create task
            task = agent.process(agent_input)
            tasks.append(task)
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks)
        
        # Combine results according to the aggregation strategy
        if 'output_aggregation' in step:
            strategy = step['output_aggregation']['strategy']
            if strategy == 'combine_content':
                combined_results = {}
                for result in results:
                    combined_results.update(result)
                return combined_results
        
        # Default: return all results in a list
        return {"results": results}
    
    async def _execute_partner_loop(self, step: Dict[str, Any],
                                  context: Dict[str, Any],
                                  workflow_agents: Dict[str, Agent]) -> Dict[str, Any]:
        """
                                  Executes a partner feedback loop where multiple agents perform operations iteratively.
                                  
                                  Each iteration, agents execute their assigned operations in sequence, updating the shared state after each operation. The loop can terminate early if a specified condition is met.
                                  
                                  Args:
                                      step: The workflow step definition containing agents, operations, and optional termination condition.
                                      context: The initial context for the workflow step.
                                      workflow_agents: Mapping of agent identifiers to agent instances.
                                  
                                  Returns:
                                      A dictionary containing the results of each iteration and the final state after completion or early termination.
                                  """
        iterations = step.get('iterations', 3)
        agents = step['agents']
        operations = step['operations']
        
        results = []
        current_state = context.copy()
        
        for i in range(iterations):
            iteration_results = {}
            
            for operation in operations:
                role = operation['role']
                operation_name = operation['name']
                
                agent = workflow_agents[agents[role]]
                
                # Prepare input for this role
                role_input = {
                    "operation": operation_name,
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
                condition = step['termination_condition']
                if self._evaluate_condition(condition, current_state):
                    break
        
        return {
            "iterations": results,
            "final_state": current_state
        }
    
    async def _execute_process_step(self, step: Dict[str, Any],
                                  context: Dict[str, Any],
                                  workflow_agents: Dict[str, Agent]) -> Dict[str, Any]:
        """
                                  Executes a process step for an agent, performing a sequence of operations with optional conditional branching.
                                  
                                  Each operation in the process is executed in order if its condition (if present) evaluates to True. The result of each operation is stored and used to update the state for subsequent operations.
                                  
                                  Args:
                                      step: The workflow step definition containing the agent and process operations.
                                      context: The current workflow context.
                                      workflow_agents: Mapping of agent names to agent instances.
                                  
                                  Returns:
                                      A dictionary mapping operation names to their results.
                                  """
        agent = workflow_agents[step['agent']]
        process = step['process']
        
        results = {}
        current_state = context.copy()
        
        for operation in process:
            # Check condition if present
            if 'condition' in operation:
                if not self._evaluate_condition(operation['condition'], current_state):
                    continue
            
            # Execute operation
            operation_input = {
                "operation": operation['operation'],
                "context": current_state,
                "step": step
            }
            
            result = await agent.process(operation_input)
            results[operation['operation']] = result
            
            # Update state
            current_state = {**current_state, "previous_result": result}
        
        return results
    
    async def _execute_handoff_step(self, step: Dict[str, Any],
                                  context: Dict[str, Any],
                                  workflow_agents: Dict[str, Agent]) -> Dict[str, Any]:
        """
                                  Executes a handoff workflow step, running a primary agent operation and conditionally delegating follow-up operations to other agents.
                                  
                                  The method first executes the primary operation with the designated agent. It then evaluates each handoff condition; if a condition is met, it invokes the specified operation on the target agent using the updated context. If a completion action is defined, it is executed by the primary agent after all handoffs. Returns a dictionary containing results from the primary operation, any handoff operations, and the completion action if present.
                                  """
        primary_agent = workflow_agents[step['primary_agent']]
        
        # Execute primary operation
        primary_result = await primary_agent.process({
            "operation": step['operation'],
            "context": context,
            "step": step
        })
        
        results = {"primary": primary_result}
        
        # Check handoff conditions
        for handoff in step.get('handoff_conditions', []):
            if self._evaluate_condition(handoff['condition'], {**context, **primary_result}):
                target_agent = workflow_agents[handoff['target_agent']]
                
                # Execute handoff operation
                handoff_result = await target_agent.process({
                    "operation": handoff['operation'],
                    "context": {**context, **primary_result},
                    "step": step
                })
                
                results[handoff['target_agent']] = handoff_result
        
        # Execute completion action if specified
        if 'completion_action' in step:
            completion_result = await primary_agent.process({
                "operation": step['completion_action'],
                "context": {**context, **results},
                "step": step
            })
            results['completion'] = completion_result
        
        return results
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> update-mvp-implementation-plan
        """
        Safely evaluates a condition expression against a given context dictionary.
        
        Args:
            condition: A string representing a Python expression to evaluate.
            context: A dictionary providing variable bindings for the evaluation.
        
        Returns:
            True if the condition evaluates to a truthy value, False if evaluation fails or the result is falsy.
        """
        try:
            # Use the safer condition evaluator
            return evaluate_condition(condition, context)
        except Exception as e:
            logging.error(f"Error evaluating condition '{condition}': {e}")
            return False
