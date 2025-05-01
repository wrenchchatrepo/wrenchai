"""Example demonstrating graph workflow with recovery integration.

This example shows how to use the GraphWorkflow with the integrated recovery system,
handling errors gracefully during workflow execution.
"""

import asyncio
import logging
import random
from typing import Dict, Any, List

from core.state_manager import state_manager
from core.graph_workflow import GraphWorkflow, WorkflowState, GraphRunContext, register_node
from core.recovery_system import RecoveryCallback, RecoveryContext, RecoveryAction
from dataclasses import dataclass


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("graph_recovery_example")


class WorkflowRecoveryCallback(RecoveryCallback):
    """Recovery callback for workflow events."""
    
    async def pre_recovery(self, context: RecoveryContext) -> None:
        """Called before recovery attempt."""
        logger.info(f"Workflow recovery: Handling error in step {context.step_id}: {str(context.error)[:100]}...")
        
    async def post_recovery(self, context: RecoveryContext, action: RecoveryAction, success: bool) -> None:
        """Called after recovery attempt."""
        logger.info(f"Workflow recovery: {action.value} completed with success={success}")
        
    async def on_abort(self, context: RecoveryContext) -> None:
        """Called when workflow is aborted."""
        logger.warning(f"Workflow aborted: {context.error}")


@register_node
@dataclass
class FailingNode:
    """Node that sometimes fails on purpose to demonstrate recovery."""
    
    fail_probability: float = 0.5
    
    async def run(self, ctx: GraphRunContext[WorkflowState]) -> Dict[str, Any]:
        """Perform an operation that may fail."""
        logger.info("Executing operation that may fail")
        
        # Simulate work
        await asyncio.sleep(0.2)
        
        # Potentially fail
        if random.random() < self.fail_probability:
            error_types = [
                ValueError("Invalid state encountered in workflow"),
                TimeoutError("Workflow operation timed out"),
                ConnectionError("Failed to connect to required service"),
                RuntimeError("Unexpected runtime error in workflow"),
            ]
            
            raise random.choice(error_types)
            
        return {
            "status": "success",
            "data": "Operation completed successfully"
        }


@register_node
@dataclass
class ProcessingNode:
    """Node that processes results from previous operations."""
    
    async def run(self, ctx: GraphRunContext[WorkflowState]) -> Dict[str, Any]:
        """Process results from previous nodes."""
        logger.info("Processing results")
        
        # Get previous results
        agent_outputs = ctx.state.agent_outputs
        
        # Generate a summary
        summary = "Processed data: "
        for key, value in agent_outputs.items():
            if isinstance(value, dict) and "data" in value:
                summary += f"{value['data']} | "
                
        return {
            "summary": summary,
            "timestamp": asyncio.get_running_loop().time()
        }


@register_node
@dataclass
class FailingQueryAnalysisNode:
    """Query analysis node that sometimes fails for demonstration."""
    
    fail_probability: float = 0.3
    
    async def run(self, ctx: GraphRunContext[WorkflowState]) -> List[str]:
        """Analyze the user query and sometimes fail."""
        logger.info("Analyzing query (might fail)")
        
        # Potentially fail
        if random.random() < self.fail_probability:
            raise ValueError("Failed to analyze query properly")
            
        # Success case
        query = ctx.state.user_query.lower()
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
            
        # Store the analysis in state
        ctx.state.context["required_skills"] = required_skills
        return required_skills


class RecoverableGraphWorkflow(GraphWorkflow):
    """A graph workflow with enhanced recovery capabilities."""
    
    def __init__(self):
        """Initialize the recoverable graph workflow."""
        super().__init__()
        
        # Re-create the graph with failing nodes for demonstration
        self.graph.clear()
        
        # Create nodes
        query_analysis = FailingQueryAnalysisNode(fail_probability=0.3)
        failing_node1 = FailingNode(fail_probability=0.5)
        failing_node2 = FailingNode(fail_probability=0.7)
        processing_node = ProcessingNode()
        
        # Set up the graph flow
        self.graph.add_edge(query_analysis, failing_node1, lambda skills: "research" in skills)
        self.graph.add_edge(query_analysis, failing_node2, lambda skills: "coding" in skills)
        self.graph.add_edge(failing_node1, processing_node)
        self.graph.add_edge(failing_node2, processing_node)
        
        # Set initial node
        self.graph.set_initial_node(query_analysis)
        
        # Register recovery callback
        self.recovery_manager.register_callback(WorkflowRecoveryCallback())
        
        # Set up alternate paths
        alternate_path_strategy = next(
            (s for s in self.recovery_manager._strategies if s.name == "alternate_path"), 
            None
        )
        if alternate_path_strategy:
            alternate_path_strategy.register_alternate_path(
                "FailingNode", 
                self._alternate_failing_node
            )
            alternate_path_strategy.register_alternate_path(
                "FailingQueryAnalysisNode", 
                self._alternate_query_analysis
            )
            
    async def _alternate_failing_node(self, context: RecoveryContext) -> None:
        """Alternate path for failing node.
        
        Args:
            context: Recovery context
        """
        logger.info(f"Executing alternate path for {context.step_id}")
        
        # Update workflow state with default data
        state_manager.set_variable_value(
            f"{context.workflow_id}_alternate_result",
            "Default result from alternate path",
            requestor=context.workflow_id
        )
        
    async def _alternate_query_analysis(self, context: RecoveryContext) -> None:
        """Alternate path for query analysis.
        
        Args:
            context: Recovery context
        """
        logger.info("Executing alternate query analysis")
        
        # Set default skills
        default_skills = ["research", "coding"]
        state_manager.set_variable_value(
            f"{context.workflow_id}_default_skills",
            default_skills,
            requestor=context.workflow_id
        )


async def main():
    """Run the recoverable graph workflow with different inputs."""
    workflow = RecoverableGraphWorkflow()
    
    queries = [
        "Find information about machine learning",
        "Write a Python function to sort a list",
        "Explain the difference between REST and GraphQL"
    ]
    
    results = []
    for query in queries:
        logger.info(f"Processing query: {query}")
        result = await workflow.run_workflow(query)
        results.append(result)
        
        # Show recovery history
        history = workflow.get_recovery_history()
        if history:
            logger.info(f"Recovery events: {len(history)}")
            for event in history[:2]:  # Show first two events
                logger.info(f"  - {event['error_category']}: {event['error'][:50]}...")
        else:
            logger.info("No recovery events recorded")
            
        logger.info("-" * 50)
    
    return results


if __name__ == "__main__":
    asyncio.run(main())