"""
Tests for MCP functionality.
"""
import pytest
import os
import asyncio
from unittest.mock import patch, MagicMock

# Try to import MCP components
try:
    from wrenchai.core.tools.mcp_client import (
        MCPServerManager, get_mcp_manager, with_mcp_servers,
        MCP_AVAILABLE
    )
    from wrenchai.core.tools.run_python import PythonCodeRunner
    has_mcp = True
except ImportError:
    has_mcp = False

@pytest.mark.skipif(not has_mcp, reason="MCP support not available")
class TestMCPClient:
    """Tests for the MCP client"""
    
    def test_mcp_manager_initialization(self):
        """Test MCP manager initialization"""
        manager = MCPServerManager()
        assert manager.servers == {}
        assert manager.server_instances == {}
        assert manager.running_servers == set()
    
    def test_get_mcp_manager_singleton(self):
        """Test MCP manager singleton pattern"""
        manager1 = get_mcp_manager()
        manager2 = get_mcp_manager()
        assert manager1 is manager2
        
    @patch('wrenchai.core.tools.mcp_client.MCPServerHTTP')
    def test_get_http_server(self, mock_http_server):
        """Test creating an HTTP server"""
        if not MCP_AVAILABLE:
            pytest.skip("MCP not available")
        
        # Mock the server instance
        mock_instance = MagicMock()
        mock_http_server.return_value = mock_instance
        
        # Create an HTTP server
        manager = MCPServerManager()
        server = manager.get_http_server("test-http", "http://localhost:8000")
        
        # Verify the server was created and stored
        assert server is mock_instance
        assert "test-http" in manager.server_instances
        mock_http_server.assert_called_with("http://localhost:8000")
        
    @patch('wrenchai.core.tools.mcp_client.MCPServerStdio')
    def test_get_stdio_server(self, mock_stdio_server):
        """Test creating a stdio server"""
        if not MCP_AVAILABLE:
            pytest.skip("MCP not available")
        
        # Mock the server instance
        mock_instance = MagicMock()
        mock_stdio_server.return_value = mock_instance
        
        # Create a stdio server
        manager = MCPServerManager()
        server = manager.get_stdio_server("test-stdio", "deno", ["run", "script.js"])
        
        # Verify the server was created and stored
        assert server is mock_instance
        assert "test-stdio" in manager.server_instances
        mock_stdio_server.assert_called_with("deno", ["run", "script.js"])

@pytest.mark.skipif(not has_mcp, reason="MCP support not available")
class TestRunPythonMCP:
    """Tests for the Run Python MCP server"""
    
    def test_python_code_runner_initialization(self):
        """Test Python code runner initialization"""
        with patch('wrenchai.core.tools.run_python._ensure_configured'):
            runner = PythonCodeRunner()
            assert runner is not None
    
    @patch('wrenchai.core.tools.run_python.with_mcp_servers')
    @pytest.mark.asyncio
    async def test_run_python_code(self, mock_with_mcp):
        """Test running Python code"""
        if not MCP_AVAILABLE:
            pytest.skip("MCP not available")
            
        # Mock the execution result
        mock_result = {
            "status": "success",
            "result": "Hello, World!",
            "stdout": "Hello, World!",
            "stderr": None,
            "return_value": None
        }
        mock_with_mcp.return_value = mock_result
        
        # Create a runner and execute some code
        with patch('wrenchai.core.tools.run_python._ensure_configured'):
            runner = PythonCodeRunner()
            mock_agent = MagicMock()
            
            # Run some code
            result = await runner.run_code(
                mock_agent, 
                "print('Hello, World!')",
                dependencies=["pytest"]
            )
            
            # Verify the execution
            assert result == mock_result
            mock_with_mcp.assert_called_once()
            
            # Check that the server name was correct
            assert mock_with_mcp.call_args[0][1] == ["run-python"]