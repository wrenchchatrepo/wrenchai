# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import asyncio
import logging
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
    
    def __init__(self):
        """Initialize the graph workflow"""
        if not GRAPH_AVAILABLE:
            raise ImportError("Graph execution not available. Install with 'pip install pydantic-ai[graph]'")
            
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
        
    async def run_workflow(self, user_query: str) -> Dict[str, Any]:
        """Run the workflow graph for a given user query
        
        Args:
            user_query: The user's query string
            
        Returns:
            Dict containing the workflow result and execution info
        """
        # Create initial state
        state = WorkflowState(user_query=user_query)
        
        # Execute the graph
        result = await self.graph.run(state)
        
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