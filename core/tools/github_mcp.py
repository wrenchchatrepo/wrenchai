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
        Initializes the MCP GitHub server manager with the specified configuration.
        
        If no configuration is provided, a default configuration is used.
        """
        self.config = config or MCPServerConfig()
        self._process = None
        self._metrics = MCPServerMetrics()
        
    async def start_server(self) -> Dict[str, Any]:
        """
        Asynchronously starts the MCP GitHub server process if it is not already running.
        
        Returns:
            A dictionary indicating success status, process ID if started or already running,
            or error details if startup fails.
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
        Stops the running MCP GitHub server process if it is active.
        
        Returns:
            A dictionary indicating whether the server was stopped successfully or if it was not found or an error occurred.
        """
        try:
            import psutil
            
            # Find and terminate server process
            for proc in psutil.process_iteritems(['pid', 'name', 'cmdline']):
                if 'mcp-server-github' in str(proc.info.get('cmdline', '')):
                    proc.terminate()
                    proc.wait(timeout=5)
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
        
        If the server process is running, updates memory usage in the metrics. Returns a dictionary with success status and metrics data, or error details if retrieval fails.
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
        Updates the server configuration and restarts the MCP GitHub server.
        
        Stops the server if it is running, applies the new configuration, and attempts to restart the server with the updated settings.
        
        Args:
            config: The new configuration to apply to the server.
        
        Returns:
            A dictionary indicating success or failure, with an error message if the update fails.
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
            A dictionary indicating success or failure, with a message or error details.
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
        Loads the server configuration from a JSON file and updates the internal state.
        
        Args:
            path: The file path to load the configuration from.
        
        Returns:
            A dictionary indicating success or failure, with details and the loaded configuration on success.
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
        
        Sends an HTTP GET request to the server's `/health` endpoint and returns the health status, including details if the server is healthy or error information if the check fails or times out.
        
        Returns:
            A dictionary with keys indicating success, status, and either health details or error information.
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
        Updates internal server metrics based on the outcome and response time of a request.
        
        Increments total, success, or failure counters and recalculates the average response time.
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