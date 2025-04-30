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
        """Initialize the MCP GitHub server manager.
        
        Args:
            config: Server configuration
        """
        self.config = config or MCPServerConfig()
        self._process = None
        self._metrics = MCPServerMetrics()
        
    async def start_server(self) -> Dict[str, Any]:
        """Start the MCP GitHub server.
        
        Returns:
            Dict containing operation status
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
        """Stop the MCP GitHub server.
        
        Returns:
            Dict containing operation status
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
        """Get current server status.
        
        Returns:
            Dict containing server status
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
        """Get server metrics.
        
        Returns:
            Dict containing server metrics
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
        """Update server configuration.
        
        Args:
            config: New server configuration
            
        Returns:
            Dict containing operation status
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
        """Save current configuration to file.
        
        Args:
            path: Path to save config file
            
        Returns:
            Dict containing operation status
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
        """Load configuration from file.
        
        Args:
            path: Path to config file
            
        Returns:
            Dict containing operation status
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
        """Check server health.
        
        Returns:
            Dict containing health status
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
        """Update server metrics.
        
        Args:
            success: Whether request was successful
            response_time: Request response time
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