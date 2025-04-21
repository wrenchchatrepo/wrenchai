"""
Tests for the graph workflow functionality.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock

# Try importing the graph components directly
try:
    from wrenchai.core.graph_workflow import (
        GraphWorkflow, WorkflowState, QueryAnalysisNode, 
        GRAPH_AVAILABLE
    )
    has_graph = True
except ImportError:
    has_graph = False

@pytest.mark.skipif(not has_graph, reason="Graph execution framework not available")
class TestGraphWorkflow:
    """Tests for the graph-based workflow system"""
    
    def test_graph_visualization(self):
        """Test that the graph can be visualized as Mermaid diagram"""
        if not GRAPH_AVAILABLE:
            pytest.skip("Graph execution not available")
            
        workflow = GraphWorkflow()
        mermaid = workflow.get_graph_visualization()
        
        # Check that we got a Mermaid string
        assert isinstance(mermaid, str)
        assert "graph" in mermaid.lower()
        assert "->" in mermaid  # Should have connections
    
    @pytest.mark.asyncio
    async def test_query_analysis_node(self):
        """Test the query analysis node function"""
        if not GRAPH_AVAILABLE:
            pytest.skip("Graph execution not available")
            
        # Create test components
        node = QueryAnalysisNode()
        
        # Mock context
        context = MagicMock()
        context.state = WorkflowState(user_query="Write a Python function to search for files")
        
        # Run the node
        skills = await node.run(context)
        
        # Verify results
        assert isinstance(skills, list)
        assert "coding" in skills
        assert "writing" in skills
        
    @pytest.mark.asyncio
    async def test_workflow_execution(self):
        """Test a complete workflow execution"""
        if not GRAPH_AVAILABLE:
            pytest.skip("Graph execution not available")
            
        # Create workflow
        workflow = GraphWorkflow()
        
        # Run a test workflow
        result = await workflow.run_workflow("Generate code to calculate Fibonacci sequence")
        
        # Check results structure
        assert "response" in result
        assert "status" in result
        assert "context" in result
        assert "agent_outputs" in result
        
        # Verify response contains code
        assert "code" in result["response"].lower() or "function" in result["response"].lower()
        
        # Verify status
        assert result["status"] == "complete"