# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import logging
import asyncio
import json
from typing import Dict, List, Any, Optional, Union, Callable

# Try to import Pydantic AI MCP components
try:
    # Import Pydantic AI's MCP server components for multi-component processing
    # Reference: https://ai.pydantic.dev/agents/#model-run-settings  
    from pydantic_ai.mcp import MCPServerHTTP, MCPServerStdio
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("Pydantic AI MCP is not available. Install with 'pip install pydantic-ai[mcp]'")
    
    # Create stub classes for type checking
    class MCPServerHTTP:
        def __init__(self, *args, **kwargs): pass
        
    class MCPServerStdio:
        def __init__(self, *args, **kwargs): pass

class MCPServerManager:
    """Manager for MCP server connections"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the MCP server manager
        
        Args:
            config_path: Path to the MCP configuration file (optional)
        """
        self.config_path = config_path
        self.servers = {}
        self.server_instances = {}
        self.running_servers = set()
        
        # Load configuration if available
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                self.servers = config.get('mcpServers', {})
                logging.info(f"Loaded MCP server config with {len(self.servers)} servers")
            except Exception as e:
                logging.error(f"Error loading MCP configuration: {str(e)}")
        
    def get_http_server(self, server_name: str, base_url: str) -> Optional[MCPServerHTTP]:
        """Get an HTTP-based MCP server
        
        Args:
            server_name: Name to identify the server
            base_url: Base URL of the MCP server
            
        Returns:
            MCPServerHTTP instance or None if not available
        """
        if not MCP_AVAILABLE:
            logging.error("Cannot create MCP server: Pydantic AI MCP is not available")
            return None
            
        # Create and store the server instance
        try:
            server = MCPServerHTTP(base_url)
            self.server_instances[server_name] = server
            logging.info(f"Created HTTP MCP server '{server_name}' at {base_url}")
            return server
        except Exception as e:
            logging.error(f"Error creating HTTP MCP server: {str(e)}")
            return None
    
    def get_stdio_server(self, server_name: str, command: str, args: List[str] = None) -> Optional[MCPServerStdio]:
        """Get a stdio-based MCP server
        
        Args:
            server_name: Name to identify the server
            command: Command to start the MCP server
            args: Command arguments (optional)
            
        Returns:
            MCPServerStdio instance or None if not available
        """
        if not MCP_AVAILABLE:
            logging.error("Cannot create MCP server: Pydantic AI MCP is not available")
            return None
            
        # Create and store the server instance
        try:
            server = MCPServerStdio(command, args or [])
            self.server_instances[server_name] = server
            logging.info(f"Created stdio MCP server '{server_name}'")
            return server
        except Exception as e:
            logging.error(f"Error creating stdio MCP server: {str(e)}")
            return None
    
    def get_server_from_config(self, server_name: str) -> Optional[Union[MCPServerHTTP, MCPServerStdio]]:
        """Get an MCP server from the configuration
        
        Args:
            server_name: Name of the server in the configuration
            
        Returns:
            MCPServer instance or None if not available
        """
        if not self.servers or server_name not in self.servers:
            logging.error(f"MCP server '{server_name}' not found in configuration")
            return None
            
        if not MCP_AVAILABLE:
            logging.error("Cannot create MCP server: Pydantic AI MCP is not available")
            return None
            
        # If server instance already exists, return it
        if server_name in self.server_instances:
            return self.server_instances[server_name]
            
        # Create a new server instance from config
        server_config = self.servers[server_name]
        command = server_config.get('command')
        args = server_config.get('args', [])
        
        if not command:
            logging.error(f"Invalid configuration for MCP server '{server_name}'")
            return None
            
        return self.get_stdio_server(server_name, command, args)
    
    async def start_server(self, server_name: str) -> bool:
        """Start a server by name
        
        Args:
            server_name: Name of the server to start
            
        Returns:
            True if server started successfully, False otherwise
        """
        server = self.get_server_from_config(server_name)
        if not server:
            return False
            
        # Mark the server as running
        self.running_servers.add(server_name)
        return True
    
    async def stop_server(self, server_name: str) -> bool:
        """Stop a server by name
        
        Args:
            server_name: Name of the server to stop
            
        Returns:
            True if server stopped successfully, False otherwise
        """
        if server_name not in self.server_instances:
            logging.error(f"MCP server '{server_name}' is not running")
            return False
            
        # Remove from running servers
        if server_name in self.running_servers:
            self.running_servers.remove(server_name)
            
        # Server will be closed when the Agent context manager exits
        return True
    
    def list_available_servers(self) -> List[str]:
        """List all available MCP servers"""
        return list(self.servers.keys())
    
    def list_running_servers(self) -> List[str]:
        """List all running MCP servers"""
        return list(self.running_servers)

# Singleton manager instance
_mcp_manager: Optional[MCPServerManager] = None

def get_mcp_manager(config_path: Optional[str] = None) -> MCPServerManager:
    """Get the singleton MCP server manager instance
    
    Args:
        config_path: Optional path to MCP configuration file
        
    Returns:
        MCPServerManager instance
    """
    global _mcp_manager
    
    if _mcp_manager is None:
        _mcp_manager = MCPServerManager(config_path)
        
    return _mcp_manager

# Utility function to create MCP server context manager
async def with_mcp_servers(agent, servers: List[str], task: Callable):
    """Run a task with specified MCP servers
    
    Args:
        agent: Pydantic AI agent to attach servers to
        servers: List of server names to use
        task: Async function to execute with servers available
        
    Returns:
        Result of the task function
    """
    if not MCP_AVAILABLE:
        logging.error("Cannot use MCP servers: Pydantic AI MCP is not available")
        return None
        
    manager = get_mcp_manager("mcp_config.json")
    
    # Start all requested servers
    server_instances = []
    for server_name in servers:
        server = manager.get_server_from_config(server_name)
        if server:
            server_instances.append(server)
            
    # Run the agent with MCP servers
    async with agent.run_mcp_servers(*server_instances):
        # Execute the provided task
        return await task()