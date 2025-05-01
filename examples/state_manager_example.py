"""Example demonstrating how to use the StateManager with WrenchAI workflows.

This example shows how to:
1. Initialize the state manager
2. Define and register workflow-specific state variables
3. Access and modify state throughout the workflow execution
4. Use state to make workflow decisions
5. Integrate state management with existing WrenchAI components
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.state_manager import (
    StateManager,
    StateVariable,
    StateGroup,
    StateScope,
    StatePermission,
    state_manager  # Global instance
)

# Import the graph workflow components
from core.graph_workflow import (
    GraphWorkflow,
    WorkflowState,
    WorkflowStatus,
    register_node
)

# Import agent state management for compatibility
from core.agents.agent_state import AgentStateManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Create a custom workflow that uses the state manager
class StateAwareWorkflow(GraphWorkflow):
    """Workflow that uses the state manager for enhanced state management."""
    
    def __init__(self):
        """Initialize the state-aware workflow."""
        super().__init__()
        
        # Initialize workflow-specific state variables
        self._init_state_variables()
    
    def _init_state_variables(self):
        """Initialize state variables for this workflow."""
        # Create a group for this workflow's variables
        try:
            self.state_group = state_manager.create_group(
                name="workflow_state",
                description="State variables for workflow execution"
            )
        except ValueError:
            # Group already exists
            self.state_group = state_manager.get_group("workflow_state")
        
        # Define common workflow variables
        state_manager.create_variable(
            name="workflow_id",
            value=f"workflow_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            description="Unique identifier for this workflow execution",
            scope=StateScope.WORKFLOW,
            tags=["workflow", "identifier"]
        )
        
        state_manager.create_variable(
            name="status",
            value=WorkflowStatus.PENDING.value,
            description="Current status of the workflow",
            scope=StateScope.WORKFLOW,
            tags=["workflow", "status"]
        )
        
        state_manager.create_variable(
            name="start_time",
            value=datetime.utcnow().isoformat(),
            description="Time when the workflow was started",
            scope=StateScope.WORKFLOW,
            tags=["workflow", "timing"]
        )
        
        state_manager.create_variable(
            name="current_step",
            value="initialization",
            description="Current step in the workflow",
            scope=StateScope.WORKFLOW,
            tags=["workflow", "progress"]
        )
        
        state_manager.create_variable(
            name="user_query",
            value="",
            description="The original user query",
            scope=StateScope.WORKFLOW,
            tags=["workflow", "input"]
        )
        
        state_manager.create_variable(
            name="context",
            value={},
            description="Contextual information for the workflow",
            scope=StateScope.WORKFLOW,
            tags=["workflow", "context"]
        )
        
        state_manager.create_variable(
            name="agent_outputs",
            value={},
            description="Outputs from various agents",
            scope=StateScope.WORKFLOW,
            tags=["workflow", "output"]
        )
    
    async def run_workflow(self, user_query: str) -> Dict[str, Any]:
        """Run the workflow for a given user query.
        
        Args:
            user_query: The user's query string
            
        Returns:
            Dict containing the workflow result and execution info
        """
        # Update state variables
        state_manager.set_variable_value("user_query", user_query)
        state_manager.set_variable_value("status", WorkflowStatus.IN_PROGRESS.value)
        
        # Create traditional workflow state for compatibility
        workflow_state = WorkflowState(user_query=user_query)
        
        # Run the graph workflow
        logger.info(f"Starting workflow execution for query: {user_query}")
        result = await self.graph.run(workflow_state)
        
        # Update state with results from the traditional workflow state
        state_manager.set_variable_value("context", workflow_state.context)
        state_manager.set_variable_value("agent_outputs", workflow_state.agent_outputs)
        state_manager.set_variable_value("status", workflow_state.status.value)
        
        # Update end time
        state_manager.create_variable(
            name="end_time",
            value=datetime.utcnow().isoformat(),
            description="Time when the workflow was completed",
            scope=StateScope.WORKFLOW,
            tags=["workflow", "timing"]
        )
        
        # Log workflow completion
        logger.info(f"Workflow completed with status: {workflow_state.status.value}")
        
        # Combine results from both state systems
        return {
            "response": result,
            "status": workflow_state.status,
            "context": workflow_state.context,
            "agent_outputs": workflow_state.agent_outputs,
            "workflow_id": state_manager.get_variable_value("workflow_id"),
            "execution_time": {
                "start": state_manager.get_variable_value("start_time"),
                "end": state_manager.get_variable_value("end_time"),
            }
        }


# Create custom nodes that leverage the enhanced state management
@register_node
class EnhancedQueryAnalysisNode:
    """Node for analyzing the user query with enhanced state tracking."""
    
    async def run(self, ctx: Any) -> List[str]:
        """Analyze the user query and track analysis in state."""
        # Update workflow step
        state_manager.set_variable_value("current_step", "query_analysis")
        
        # Get the user query from either state system
        query = ctx.state.user_query.lower()
        state_manager.set_variable_value("user_query", query)
        
        # In real implementation, this would use a model to analyze the query
        required_skills = []
        
        if "code" in query or "program" in query or "function" in query:
            required_skills.append("coding")
        
        if "search" in query or "find information" in query or "research" in query:
            required_skills.append("research")
            
        if "write" in query or "document" in query or "explain" in query:
            required_skills.append("writing")
            
        if not required_skills:
            # Default to research if no specific skills detected
            required_skills.append("research")
        
        # Store analysis in both state systems
        ctx.state.context["required_skills"] = required_skills
        
        # Store in enhanced state system
        context = state_manager.get_variable_value("context", {})
        context["required_skills"] = required_skills
        context["analysis_timestamp"] = datetime.utcnow().isoformat()
        state_manager.set_variable_value("context", context)
        
        # Log skills identified
        logger.info(f"Query analysis identified skills: {required_skills}")
        
        return required_skills


# Example: Integrating with the agent state manager for backward compatibility
def integrate_with_agent_state():
    """Integrate the new state manager with the existing agent state."""
    # Get the global agent state manager
    from core.agents.agent_state import agent_state_manager
    
    # Sync state between systems
    def sync_state_to_agent(name, old_value, new_value, requestor):
        """Sync state changes to the agent state manager."""
        if name.startswith("agent_"):
            # Extract agent ID from variable name
            parts = name.split("_", 2)
            if len(parts) >= 3:
                agent_id = parts[1]
                key = parts[2]
                # Store in agent state
                agent_state_manager.set_state_entry(
                    agent_id=agent_id,
                    key=key,
                    value=new_value,
                    scope="workflow",
                    visibility="shared"
                )
    
    # Register the sync hook
    state_manager.add_hook("post_change", sync_state_to_agent)
    
    return True


# Example usage
async def main():
    """Run an example workflow using the state manager."""
    # Initialize the enhanced workflow
    workflow = StateAwareWorkflow()
    
    # Register the enhanced nodes
    # In a real application, you would modify the workflow construction
    
    # Run the workflow
    result = await workflow.run_workflow("Write a program to analyze data")
    
    # Display the result
    print(f"Workflow Result: {result['response']}")
    print(f"Status: {result['status']}")
    
    # Display state information
    print("\nState Variables:")
    for name, value in state_manager.export_state_to_dict().items():
        print(f"  {name}: {value}")
    
    # Show debug info
    print("\nState Manager Debug Info:")
    debug_info = state_manager.debug_info()
    print(f"  Variables: {debug_info['variable_count']}")
    print(f"  Groups: {debug_info['group_count']}")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())