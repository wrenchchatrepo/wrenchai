"""
GitHub MCP Tool for managing MCP server interactions.

This module provides functionality to:
- Initialize and manage MCP GitHub server
- Handle authentication and configuration
- Manage server lifecycle and health checks
"""

import logging
import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class MCPServerConfig(BaseModel):
    """Configuration for MCP GitHub server."""
    host: str = "localhost"
    port: int = 8000
    auth_token: Optional[str] = None
    github_token: Optional[str] = None
    log_level: str = "INFO"
    timeout: int = 30

class MCPServerStatus(BaseModel):
    """Status of MCP GitHub server."""
    is_running: bool
    pid: Optional[int] = None
    port: Optional[int] = None
    uptime: Optional[float] = None
    error: Optional[str] = None

class MCPServerMetrics(BaseModel):
    """Metrics for MCP GitHub server."""
    requests_total: int = 0
    requests_success: int = 0
    requests_failed: int = 0
    average_response_time: float = 0.0
    memory_usage_mb: float = 0.0

class GitHubMCPServer:
    """Manages MCP GitHub server operations."""
    
    def __init__(self, config: Optional[MCPServerConfig] = None):
        """
        Initializes the MCP GitHub server manager with the provided or default configuration.
        
        Args:
            config: Optional server configuration. If not provided, a default configuration is used.
        """
        self.config = config or MCPServerConfig()
        self._process = None
        self._metrics = MCPServerMetrics()
        
    async def start_server(self) -> Dict[str, Any]:
        """
        Asynchronously starts the MCP GitHub server process if it is not already running.
        
        Returns:
            A dictionary indicating whether the server was started successfully, including
            a message and the process ID if successful, or an error message if the operation fails.
        """
        try:
            import psutil
            import subprocess
            
            # Check if server is already running
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if 'mcp-server-github' in str(proc.info.get('cmdline', '')):
                    return {
                        "success": True,
                        "message": "Server already running",
                        "pid": proc.info['pid']
                    }
            
            # Start server process
            env = os.environ.copy()
            if self.config.github_token:
                env['GITHUB_TOKEN'] = self.config.github_token
            if self.config.auth_token:
                env['MCP_AUTH_TOKEN'] = self.config.auth_token
                
            cmd = [
                'npx',
                '@modelcontextprotocol/server-github',
                '--host', self.config.host,
                '--port', str(self.config.port),
                '--log-level', self.config.log_level
            ]
            
            self._process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            return {
                "success": True,
                "message": "Server started successfully",
                "pid": self._process.pid
            }
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def stop_server(self) -> Dict[str, Any]:
        """
        Stops the running MCP GitHub server process if found.
        
        Returns:
            A dictionary indicating whether the server was stopped successfully or if it was not found, including error details if applicable.
        """
        try:
            import psutil
            
            # Find and terminate server process
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if 'mcp-server-github' in str(proc.info.get('cmdline', '')):
                    process = psutil.Process(proc.info['pid'])
                    process.terminate()
                    process.wait(timeout=5)
                    return {
                        "success": True,
                        "message": "Server stopped successfully"
                    }
            
            return {
                "success": False,
                "error": "Server not found"
            }
            
        except Exception as e:
            logger.error(f"Failed to stop MCP server: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Retrieves the current status of the MCP GitHub server.
        
        Returns:
            A dictionary indicating whether the server is running, including process ID,
            port, and uptime if active, or an error message if not running or on failure.
        """
        try:
            import psutil
            import time
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                if 'mcp-server-github' in str(proc.info.get('cmdline', '')):
                    uptime = time.time() - proc.info['create_time']
                    return {
                        "success": True,
                        "status": {
                            "is_running": True,
                            "pid": proc.info['pid'],
                            "port": self.config.port,
                            "uptime": uptime
                        }
                    }
            
            return {
                "success": True,
                "status": {
                    "is_running": False,
                    "error": "Server not running"
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get server status: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Retrieves current metrics for the MCP GitHub server.
        
        Returns:
            A dictionary containing success status and server metrics, or error details if retrieval fails.
        """
        try:
            import psutil
            
            # Get process metrics if server is running
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if 'mcp-server-github' in str(proc.info.get('cmdline', '')):
                    process = psutil.Process(proc.info['pid'])
                    self._metrics.memory_usage_mb = process.memory_info().rss / 1024 / 1024
                    break
            
            return {
                "success": True,
                "metrics": self._metrics.dict()
            }
            
        except Exception as e:
            logger.error(f"Failed to get server metrics: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_config(self, config: MCPServerConfig) -> Dict[str, Any]:
        """
        Asynchronously updates the server configuration and restarts the server.
        
        Stops the server if it is running, applies the new configuration, and attempts to restart the server. Returns a dictionary indicating the success or failure of the operation.
        """
        try:
            # Stop server if running
            await self.stop_server()
            
            # Update config
            self.config = config
            
            # Restart server
            result = await self.start_server()
            if not result["success"]:
                return result
                
            return {
                "success": True,
                "message": "Configuration updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to update config: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def save_config(self, path: str) -> Dict[str, Any]:
        """
        Saves the current server configuration to a specified file in JSON format.
        
        Args:
            path: The file path where the configuration will be saved.
        
        Returns:
            A dictionary indicating whether the operation was successful, with a message or error details.
        """
        try:
            config_path = Path(path)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump(self.config.dict(), f, indent=2)
                
            return {
                "success": True,
                "message": f"Configuration saved to {path}"
            }
            
        except Exception as e:
            logger.error(f"Failed to save config: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def load_config(self, path: str) -> Dict[str, Any]:
        """
        Asynchronously loads the server configuration from a JSON file.
        
        Attempts to read and parse the configuration file at the specified path, updating the internal configuration state. Returns a dictionary indicating success or failure, along with relevant messages and the loaded configuration data on success.
        """
        try:
            with open(path, 'r') as f:
                config_data = json.load(f)
                
            self.config = MCPServerConfig(**config_data)
            
            return {
                "success": True,
                "message": f"Configuration loaded from {path}",
                "config": self.config.dict()
            }
            
        except Exception as e:
            logger.error(f"Failed to load config: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Performs an asynchronous health check on the MCP GitHub server.
        
        Sends an HTTP GET request to the server's `/health` endpoint and returns a dictionary indicating whether the server is healthy, unhealthy, or if an error occurred. Includes details from the server response or error messages as appropriate.
        
        Returns:
            A dictionary with keys such as 'success', 'status', 'details', or 'error' describing the health check result.
        """
        try:
            import aiohttp
            import asyncio
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f"http://{self.config.host}:{self.config.port}/health",
                        timeout=self.config.timeout
                    ) as response:
                        if response.status == 200:
                            return {
                                "success": True,
                                "status": "healthy",
                                "details": await response.json()
                            }
                        else:
                            return {
                                "success": False,
                                "status": "unhealthy",
                                "error": f"Health check failed with status {response.status}"
                            }
                except asyncio.TimeoutError:
                    return {
                        "success": False,
                        "status": "unhealthy",
                        "error": "Health check timed out"
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "status": "unhealthy",
                        "error": str(e)
                    }
                    
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_metrics(self, success: bool, response_time: float):
        """
        Updates internal metrics counters for request outcomes and recalculates average response time.
        
        Args:
            success: Indicates if the request was successful.
            response_time: The response time of the request in seconds.
        """
        self._metrics.requests_total += 1
        if success:
            self._metrics.requests_success += 1
        else:
            self._metrics.requests_failed += 1
            
        # Update average response time
        total = (self._metrics.average_response_time * 
                (self._metrics.requests_total - 1))
        self._metrics.average_response_time = (
            (total + response_time) / self._metrics.requests_total
        )

# Global server instance
github_mcp_server = GitHubMCPServer()

async def github_mcp_operation(operation: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Primary interface for GitHub MCP operations.
    
    This function is the main entry point for the tool system to interact with the
    GitHub MCP server. It maps operations to the appropriate server methods.
    
    Args:
        operation: Operation to perform (start_server, stop_server, get_status,
                  get_metrics, update_config, health_check)
        config: Optional configuration for the server
        
    Returns:
        Dictionary containing operation results
    """
    try:
        # Convert config dict to MCPServerConfig if provided
        server_config = None
        if config:
            server_config = MCPServerConfig(**config)
        
        # Map operations to server methods
        if operation == "start_server":
            return await github_mcp_server.start_server()
            
        elif operation == "stop_server":
            return await github_mcp_server.stop_server()
            
        elif operation == "get_status":
            return await github_mcp_server.get_status()
            
        elif operation == "get_metrics":
            return await github_mcp_server.get_metrics()
            
        elif operation == "update_config":
            if not server_config:
                return {
                    "success": False,
                    "error": "Configuration required for update_config operation"
                }
            return await github_mcp_server.update_config(server_config)
            
        elif operation == "health_check":
            return await github_mcp_server.health_check()
            
        else:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}"
            }
            
    except Exception as e:
        logger.error(f"GitHub MCP operation failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }