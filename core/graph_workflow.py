# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import asyncio
import logging
import traceback
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, TypeVar, Generic, Union, cast
from enum import Enum

# Try to import graph execution components
try:
    from pydantic_ai.graph import Graph, GraphState, GraphRunContext, register_node
    GRAPH_AVAILABLE = True
except ImportError:
    GRAPH_AVAILABLE = False
    logging.warning("Graph execution not available. Install with 'pip install pydantic-ai[graph]'")
    
    # Create stub classes for type checking
    class Graph: pass
    class GraphState: pass
    class GraphRunContext: pass
    
    def register_node(cls): return cls

# Import recovery system
from .recovery_system import (
    RecoveryManager, RecoveryAction, with_recovery, ErrorCategory, 
    init_recovery_manager
)
from .state_manager import state_manager as global_state_manager

# Define state type
T = TypeVar('T')

class WorkflowStatus(str, Enum):
    """Status of the workflow execution"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"

@dataclass
class WorkflowState(GraphState):
    """State maintained throughout the workflow execution"""
    user_query: str
    context: Dict[str, Any] = field(default_factory=dict)
    agent_outputs: Dict[str, Any] = field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.PENDING
    error: Optional[str] = None

@register_node
@dataclass
class QueryAnalysisNode:
    """Node for analyzing the user query"""
    
    async def run(self, ctx: GraphRunContext[WorkflowState]) -> List[str]:
        """Analyze the user query and determine required skills"""
        ctx.state.status = WorkflowStatus.IN_PROGRESS
        
        # In real implementation, this would use a model to analyze the query
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

@register_node
@dataclass
class ResearchNode:
    """Node for performing research tasks"""
    
    async def run(self, ctx: GraphRunContext[WorkflowState]) -> Dict[str, Any]:
        """Perform research based on the user query"""
        # In real implementation, this would use research tools
        results = {
            "sources": ["example.com", "wikipedia.org"],
            "snippets": ["Relevant information 1", "Relevant information 2"],
            "summary": "Summary of research findings"
        }
        
        # Store results in state
        ctx.state.agent_outputs["research"] = results
        return results

@register_node
@dataclass
class CodingNode:
    """Node for generating code"""
    
    async def run(self, ctx: GraphRunContext[WorkflowState]) -> Dict[str, Any]:
        """Generate code based on the user query"""
        # In real implementation, this would use coding tools
        code_output = {
            "language": "python",
            "code": "def example():\n    return 'Hello, World!'",
            "explanation": "This is a simple example function"
        }
        
        # Store results in state
        ctx.state.agent_outputs["coding"] = code_output
        return code_output

@register_node
@dataclass
class WritingNode:
    """Node for writing content"""
    
    async def run(self, ctx: GraphRunContext[WorkflowState]) -> Dict[str, Any]:
        """Generate written content based on the user query"""
        # In real implementation, this would use writing tools
        writing_output = {
            "content": "Here is the written content responding to your query...",
            "format": "markdown"
        }
        
        # Store results in state
        ctx.state.agent_outputs["writing"] = writing_output
        return writing_output

@register_node
@dataclass
class ResponseSynthesisNode:
    """Node for synthesizing a final response"""
    
    async def run(self, ctx: GraphRunContext[WorkflowState]) -> str:
        """Synthesize a final response from all agent outputs"""
        outputs = ctx.state.agent_outputs
        
        # In a real implementation, this would use a model to generate a coherent response
        response_parts = []
        
        if "research" in outputs:
            response_parts.append("Based on my research: " + outputs["research"]["summary"])
            
        if "coding" in outputs:
            response_parts.append("Here's the code solution:\n\n```" + 
                               outputs["coding"]["language"] + "\n" + 
                               outputs["coding"]["code"] + "\n```")
            
        if "writing" in outputs:
            response_parts.append(outputs["writing"]["content"])
            
        # Combine all parts
        final_response = "\n\n".join(response_parts)
        
        # Update state
        ctx.state.status = WorkflowStatus.COMPLETE
        return final_response

class GraphWorkflow:
    """Workflow orchestrator using Pydantic AI Graph"""
    
    def __init__(self, recovery_manager=None):
        """Initialize the graph workflow
        
        Args:
            recovery_manager: Optional recovery manager instance. If not provided,
                              a global instance will be initialized.
        """
        if not GRAPH_AVAILABLE:
            raise ImportError("Graph execution not available. Install with 'pip install pydantic-ai[graph]'")
        
        # Set up recovery manager
        self.recovery_manager = recovery_manager
        if self.recovery_manager is None:
            self.recovery_manager = init_recovery_manager(global_state_manager)
            
        # Create the graph
        self.graph = Graph[WorkflowState]()
        
        # Create nodes
        query_analysis = QueryAnalysisNode()
        research = ResearchNode()
        coding = CodingNode()
        writing = WritingNode()
        response_synthesis = ResponseSynthesisNode()
        
        # Set up the graph flow
        self.graph.add_edge(query_analysis, research, lambda skills: "research" in skills)
        self.graph.add_edge(query_analysis, coding, lambda skills: "coding" in skills)
        self.graph.add_edge(query_analysis, writing, lambda skills: "writing" in skills)
        self.graph.add_edge(research, response_synthesis)
        self.graph.add_edge(coding, response_synthesis)
        self.graph.add_edge(writing, response_synthesis)
        
        # Set initial node
        self.graph.set_initial_node(query_analysis)
        
        # Set up workflow ID
        self.workflow_id = f"graph_workflow_{id(self)}"
        
    async def _run_node_with_recovery(self, node, ctx):
        """Run a node with error recovery
        
        Args:
            node: The node to run
            ctx: The graph run context
            
        Returns:
            Result of the node execution
        """
        step_id = node.__class__.__name__
        
        # Create checkpoint before running the node
        await self.recovery_manager.checkpoint_workflow(
            self.workflow_id, 
            step_id,
            metadata={"node_type": step_id}
        )
        
        try:
            # Try to run the node inside a transaction
            async with self.recovery_manager.step_transaction(self.workflow_id, step_id):
                return await node.run(ctx)
        except Exception as e:
            # Record the error in state
            if ctx.state.error is None:
                ctx.state.error = str(e)
            
            # Handle the error with recovery system
            action = await self.recovery_manager.handle_error(
                e, 
                self.workflow_id, 
                step_id,
                additional_info={
                    "node_type": step_id,
                    "state": {k: v for k, v in ctx.state.__dict__.items() 
                             if not k.startswith("_") and k != "agent_outputs"}
                }
            )
            
            # If recovery action is retry, abort, or alternate path, we need to propagate
            if action in (RecoveryAction.RETRY, RecoveryAction.ABORT):
                raise
                
            # For skip action, return a default value based on node type
            if action == RecoveryAction.SKIP:
                if isinstance(node, QueryAnalysisNode):
                    return ["research"]  # Default skill
                elif isinstance(node, ResearchNode):
                    return {"summary": "Research unavailable"}
                elif isinstance(node, CodingNode):
                    return {"code": "# Code generation failed", "language": "text"}
                elif isinstance(node, WritingNode):
                    return {"content": "Content generation unavailable"}
                elif isinstance(node, ResponseSynthesisNode):
                    return "The requested operation could not be completed."
                else:
                    return None
            
            # Re-raise for other actions
            raise
        
    async def run_workflow(self, user_query: str) -> Dict[str, Any]:
        """Run the workflow graph for a given user query
        
        Args:
            user_query: The user's query string
            
        Returns:
            Dict containing the workflow result and execution info
        """
        # Create initial state
        state = WorkflowState(user_query=user_query)
        
        # Patch the graph's _run_node method to use our recovery-wrapped version
        original_run_node = self.graph._run_node
        
        async def wrapped_run_node(node, ctx):
            return await self._run_node_with_recovery(node, ctx)
        
        try:
            # Replace the method
            self.graph._run_node = wrapped_run_node
            
            # Execute the graph with recovery
            async with self.recovery_manager.recovery_context(self.workflow_id, "workflow_execution"):
                result = await self.graph.run(state)
        except Exception as e:
            # Update state status
            state.status = WorkflowStatus.FAILED
            state.error = str(e)
            
            # Return partial results with error
            return {
                "response": "An error occurred during workflow execution: " + str(e),
                "status": state.status,
                "context": state.context,
                "agent_outputs": state.agent_outputs,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        finally:
            # Restore original method
            self.graph._run_node = original_run_node
        
        # Return results
        return {
            "response": result,
            "status": state.status,
            "context": state.context,
            "agent_outputs": state.agent_outputs
        }
        
    def get_graph_visualization(self) -> str:
        """Get a Mermaid diagram visualization of the graph"""
        return self.graph.to_mermaid()
    
    def get_recovery_history(self) -> List[Dict[str, Any]]:
        """Get recovery event history for this workflow.
        
        Returns:
            List of recovery event records
        """
        return self.recovery_manager.get_recovery_history(self.workflow_id)