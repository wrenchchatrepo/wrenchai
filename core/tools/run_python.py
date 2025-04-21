# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import logging
import asyncio
import json
from typing import Dict, List, Any, Optional, Union, Callable

from wrenchai.core.tools.mcp_client import get_mcp_manager, with_mcp_servers, MCP_AVAILABLE

# MCP Run Python server configuration
RUN_PYTHON_SERVER = {
    "name": "run-python",
    "command": "deno",
    "args": [
        "run",
        "-N",
        "-R=node_modules",
        "-W=node_modules",
        "--node-modules-dir=auto",
        "jsr:@pydantic/mcp-run-python",
        "stdio"
    ]
}

class PythonCodeRunner:
    """Helper class for running Python code through MCP"""
    
    def __init__(self):
        """Initialize the Python code runner"""
        # Ensure the Run Python server is configured
        self._ensure_configured()
    
    def _ensure_configured(self):
        """Ensure the Run Python MCP server is configured"""
        if not MCP_AVAILABLE:
            logging.warning("MCP not available. Python code execution will not work.")
            return

        # Load existing configuration
        manager = get_mcp_manager("mcp_config.json")
        
        # Check if run-python is already configured
        if "run-python" in manager.servers:
            logging.info("Run Python MCP server already configured")
            return
            
        # Add the server configuration to the file
        if os.path.exists("mcp_config.json"):
            try:
                with open("mcp_config.json", 'r') as f:
                    config = json.load(f)
                    
                # Add the Run Python server configuration
                config.setdefault("mcpServers", {})["run-python"] = {
                    "command": RUN_PYTHON_SERVER["command"],
                    "args": RUN_PYTHON_SERVER["args"]
                }
                
                # Write the updated configuration
                with open("mcp_config.json", 'w') as f:
                    json.dump(config, f, indent=2)
                    
                # Update the manager's configuration
                manager.servers["run-python"] = {
                    "command": RUN_PYTHON_SERVER["command"],
                    "args": RUN_PYTHON_SERVER["args"]
                }
                
                logging.info("Run Python MCP server configuration added")
            except Exception as e:
                logging.error(f"Error updating MCP configuration: {str(e)}")
        else:
            logging.warning("mcp_config.json not found. Cannot configure Run Python server.")
    
    async def run_code(self, agent, code: str, dependencies: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run Python code through MCP
        
        Args:
            agent: Pydantic AI agent to use for code execution
            code: Python code to execute
            dependencies: Optional list of dependencies to install
            
        Returns:
            Dictionary with execution results
        """
        if not MCP_AVAILABLE:
            return {
                "status": "error",
                "message": "MCP not available. Install with 'pip install pydantic-ai[mcp]'"
            }
            
        # Prepare the code with dependencies if provided
        if dependencies:
            code = f"# /// script\n# dependencies = {json.dumps(dependencies)}\n# ///\n\n{code}"
        
        # Create a task to execute with MCP
        async def execute_task():
            try:
                # Use the run_python_code tool
                result = await agent.run(f"""
                    Please run this Python code and show all output:
                    ```python
                    {code}
                    ```
                """)
                
                return {
                    "status": "success",
                    "result": result,
                    "stdout": None,  # In real implementation, this would be extracted from result
                    "stderr": None,  # In real implementation, this would be extracted from result
                    "return_value": None  # In real implementation, this would be extracted from result
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": str(e)
                }
        
        # Run with the MCP server
        return await with_mcp_servers(agent, ["run-python"], execute_task)

# Singleton instance
_runner = None

def get_runner() -> PythonCodeRunner:
    """Get the singleton Python code runner instance"""
    global _runner
    
    if _runner is None:
        _runner = PythonCodeRunner()
        
    return _runner

async def run_python_code(agent, code: str, dependencies: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run Python code through MCP
    
    Args:
        agent: Pydantic AI agent to use for code execution
        code: Python code to execute
        dependencies: Optional list of dependencies to install
        
    Returns:
        Dictionary with execution results
    """
    runner = get_runner()
    return await runner.run_code(agent, code, dependencies)