# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import logging
import json
import os
import subprocess
from typing import Dict, Any, Optional, List

class MCPClient:
    """
    Model Context Protocol (MCP) client for managing contexts.
    Supports both in-memory implementation and external MCP servers.
    """
    
    def __init__(self, default_embedding_model: str = "text-embedding-3-large", 
                mcp_config_path: Optional[str] = None):
        """Initialize the MCP client"""
        self.contexts = {}
        self.default_embedding_model = default_embedding_model
        self.mcp_servers = {}
        self.server_processes = {}
        
        # Load MCP server configurations if provided
        if mcp_config_path and os.path.exists(mcp_config_path):
            try:
                with open(mcp_config_path, 'r') as f:
                    config = json.load(f)
                self.mcp_servers = config.get('mcpServers', {})
                logging.info(f"Loaded MCP server configurations: {list(self.mcp_servers.keys())}")
            except Exception as e:
                logging.error(f"Error loading MCP configuration: {str(e)}")
        
        logging.info(f"Initialized MCP client with model: {default_embedding_model}")
    
    def start_server(self, server_name: str) -> bool:
        """Start an MCP server by name"""
        if server_name not in self.mcp_servers:
            logging.error(f"MCP server '{server_name}' not found in configuration")
            return False
            
        server_config = self.mcp_servers[server_name]
        command = server_config.get('command')
        args = server_config.get('args', [])
        
        if not command:
            logging.error(f"Invalid configuration for MCP server '{server_name}'")
            return False
            
        try:
            # Start the server process
            process = subprocess.Popen(
                [command] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.server_processes[server_name] = process
            logging.info(f"Started MCP server: {server_name}")
            return True
        except Exception as e:
            logging.error(f"Error starting MCP server '{server_name}': {str(e)}")
            return False
    
    def stop_server(self, server_name: str) -> bool:
        """Stop an MCP server by name"""
        if server_name not in self.server_processes:
            logging.error(f"MCP server '{server_name}' is not running")
            return False
            
        try:
            process = self.server_processes[server_name]
            process.terminate()
            process.wait(timeout=5)
            
            del self.server_processes[server_name]
            logging.info(f"Stopped MCP server: {server_name}")
            return True
        except Exception as e:
            logging.error(f"Error stopping MCP server '{server_name}': {str(e)}")
            return False
    
    def list_available_servers(self) -> List[str]:
        """List all available MCP servers"""
        return list(self.mcp_servers.keys())
    
    def list_running_servers(self) -> List[str]:
        """List all running MCP servers"""
        return list(self.server_processes.keys())
    
    async def store(self, context_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store data in a context"""
        if context_id not in self.contexts:
            self.contexts[context_id] = {
                "chunks": [],
                "metadata": {}
            }
        
        # In a real implementation, this would:
        # 1. Generate embeddings for text data
        # 2. Store data in a vector database
        # 3. Return a context object
        
        # For now, just append the data
        self.contexts[context_id]["chunks"].append(data)
        
        return {
            "id": context_id,
            "chunks_count": len(self.contexts[context_id]["chunks"])
        }
    
    async def retrieve(self, context_id: str) -> Dict[str, Any]:
        """Retrieve a context by ID"""
        if context_id not in self.contexts:
            raise ValueError(f"Context {context_id} not found")
        
        return {
            "id": context_id,
            "chunks": self.contexts[context_id]["chunks"],
            "metadata": self.contexts[context_id]["metadata"]
        }
    
    async def query(self, context_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Query a context using semantic search"""
        if context_id not in self.contexts:
            raise ValueError(f"Context {context_id} not found")
        
        # In a real implementation, this would:
        # 1. Generate embedding for the query
        # 2. Perform vector search against stored embeddings
        # 3. Return closest matching chunks
        
        # For now, just return all chunks (limited)
        chunks = self.contexts[context_id]["chunks"][:limit]
        
        return [
            {
                "chunk": chunk,
                "score": 1.0 - (i * 0.1)  # Fake similarity score
            }
            for i, chunk in enumerate(chunks)
        ]
    
    async def update(self, context_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a context with new data"""
        if context_id not in self.contexts:
            raise ValueError(f"Context {context_id} not found")
        
        # In a real implementation, this would update specific chunks or metadata
        # For now, just add the data as a new chunk
        self.contexts[context_id]["chunks"].append(data)
        
        return {
            "id": context_id,
            "chunks_count": len(self.contexts[context_id]["chunks"])
        }
    
    async def delete(self, context_id: str) -> Dict[str, Any]:
        """Delete a context"""
        if context_id not in self.contexts:
            raise ValueError(f"Context {context_id} not found")
        
        del self.contexts[context_id]
        
        return {
            "id": context_id,
            "status": "deleted"
        }

# Singleton client instances (keyed by config path)
_mcp_clients = {}

def get_client(mcp_config_path: Optional[str] = None) -> MCPClient:
    """Get the singleton MCP client instance"""
    global _mcp_clients
    
    # Use default key for clients with no config path
    key = mcp_config_path or "default"
    
    if key not in _mcp_clients:
        _mcp_clients[key] = MCPClient(mcp_config_path=mcp_config_path)
        
    return _mcp_clients[key]

async def standard_operations(operation: str, context_id: str, 
                          data: Optional[Dict[str, Any]] = None,
                          query: Optional[str] = None,
                          server: Optional[str] = None) -> Dict[str, Any]:
    """Standard MCP operations
    
    Args:
        operation: One of "store", "retrieve", "query", "update", "delete", "list_servers", "start_server", "stop_server"
        context_id: Identifier for the context (not used for server operations)
        data: Optional data to store or update
        query: Optional query string for semantic search
        server: Optional server name for server operations
        
    Returns:
        Operation result
    """
    client = get_client(mcp_config_path="mcp_config.json")
    
    # Server management operations
    if operation == "list_available_servers":
        servers = client.list_available_servers()
        return {"status": "success", "servers": servers}
        
    elif operation == "list_running_servers":
        servers = client.list_running_servers()
        return {"status": "success", "servers": servers}
        
    elif operation == "start_server":
        if not server:
            raise ValueError("Server name is required for start_server operation")
        success = client.start_server(server)
        return {"status": "success" if success else "error", "server": server}
        
    elif operation == "stop_server":
        if not server:
            raise ValueError("Server name is required for stop_server operation")
        success = client.stop_server(server)
        return {"status": "success" if success else "error", "server": server}
    
    # Context operations
    elif operation == "store":
        if not data:
            raise ValueError("Data is required for store operation")
        return await client.store(context_id, data)
    
    elif operation == "retrieve":
        return await client.retrieve(context_id)
    
    elif operation == "query":
        if not query:
            raise ValueError("Query is required for query operation")
        return await client.query(context_id, query)
    
    elif operation == "update":
        if not data:
            raise ValueError("Data is required for update operation")
        return await client.update(context_id, data)
    
    elif operation == "delete":
        return await client.delete(context_id)
    
    else:
        raise ValueError(f"Unknown operation: {operation}")