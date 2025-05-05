#!/usr/bin/env python3
# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import json
import logging
from typing import Dict, List, Any, Optional

# Try to import MCP components
try:
    from pydantic_ai.mcp import MCPServerHTTP, MCPServerStdio
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Create stub classes for type checking
    class MCPServerHTTP:
        pass
    class MCPServerStdio:
        pass

logger = logging.getLogger("wrenchai.mcp_server")

class MCPServerManager:
    """Manager for MCP servers"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the MCP server manager
        
        Args:
            config_path: Optional path to a JSON configuration file
        """
        self.config = {}
        self.servers = {}
        
        if config_path and os.path.exists(config_path):
            self._load_config(config_path)
    
    def _load_config(self, config_path: str) -> None:
        """Load MCP server configuration from a file
        
        Args:
            config_path: Path to the configuration file
        """
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Loaded MCP server configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading MCP server configuration: {e}")
    
    def get_server_config(self, server_name: str) -> Dict[str, Any]:
        """Get configuration for a specific server
        
        Args:
            server_name: Name of the server
            
        Returns:
            Server configuration dictionary
        """
        if server_name in self.config:
            return self.config[server_name]
        return {}
    
    def get_server_from_config(self, server_name: str) -> Optional[Any]:
        """Get a server instance from configuration
        
        Args:
            server_name: Name of the server
            
        Returns:
            MCP server instance or None if not available
        """
        if not MCP_AVAILABLE:
            logger.warning("MCP server support not available")
            return None
            
        # Return existing server if already created
        if server_name in self.servers:
            return self.servers[server_name]
            
        # Get configuration for the server
        server_config = self.get_server_config(server_name)
        if not server_config:
            logger.warning(f"No configuration found for server '{server_name}'")
            return None
            
        # Create server based on type
        server_type = server_config.get("type", "")
        if server_type == "http":
            self.servers[server_name] = MCPServerHTTP(
                server_config.get("url", "http://localhost:8000"),
                headers=server_config.get("headers", {})
            )
            return self.servers[server_name]
        elif server_type == "stdio":
            # Get command and arguments
            command = server_config.get("command", [])
            if not command:
                logger.error(f"No command specified for stdio server '{server_name}'")
                return None
                
            self.servers[server_name] = MCPServerStdio(command)
            return self.servers[server_name]
        else:
            logger.warning(f"Unknown server type '{server_type}' for '{server_name}'")
            return None
    
    def get_all_server_names(self) -> List[str]:
        """Get names of all configured servers
        
        Returns:
            List of server names
        """
        return list(self.config.keys())

    def start_server(self, server_name: str) -> Optional[Any]:
        """Starts a configured MCP server.

        Args:
            server_name: Name of the server to start.

        Returns:
            The started MCP server instance or None if not available or could not start.
        """
        server = self.get_server_from_config(server_name)
        if server and hasattr(server, 'start'):
            try:
                server.start()
                logger.info(f"Started MCP server: {server_name}")
                return server
            except Exception as e:
                logger.error(f"Error starting MCP server {server_name}: {e}")
                return None
        elif server:
             logger.warning(f"Server {server_name} does not have a start method.")
             return server # Return the instance even if no start method
        return None

    def stop_server(self, server_name: str) -> None:
        """Stops a running MCP server.

        Args:
            server_name: Name of the server to stop.
        """
        server = self.servers.get(server_name)
        if server and hasattr(server, 'stop'):
            try:
                server.stop()
                logger.info(f"Stopped MCP server: {server_name}")
            except Exception as e:\n                logger.error(f"Error stopping MCP server {server_name}: {e}")
        elif server:
             logger.warning(f"Server {server_name} does not have a stop method.")

    def stop_all_servers(self) -> None:
        """Stops all currently managed MCP servers.
        """
        server_names = list(self.servers.keys())
        for server_name in server_names:
            self.stop_server(server_name)
        self.servers.clear() # Clear the dictionary of server instances

# Singleton instance of the MCP server manager
_manager_instance = None

def get_mcp_manager(config_path: Optional[str] = None) -> MCPServerManager:
    """Get the singleton MCP server manager instance
    
    Args:
        config_path: Optional path to a configuration file
        
    Returns:
        The MCPServerManager instance
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = MCPServerManager(config_path)
    return _manager_instance