# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import logging
from typing import Dict, Any, Optional, List

class MCPClient:
    """
    Model Context Protocol (MCP) client for managing contexts.
    This is a simple in-memory implementation for demonstration.
    """
    
    def __init__(self, default_embedding_model: str = "text-embedding-3-large"):
        """Initialize the MCP client"""
        self.contexts = {}
        self.default_embedding_model = default_embedding_model
        logging.info(f"Initialized MCP client with model: {default_embedding_model}")
    
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

# Singleton client instance
_mcp_client = None

def get_client() -> MCPClient:
    """Get the singleton MCP client instance"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client

async def standard_operations(operation: str, context_id: str, 
                          data: Optional[Dict[str, Any]] = None,
                          query: Optional[str] = None) -> Dict[str, Any]:
    """Standard MCP operations
    
    Args:
        operation: One of "store", "retrieve", "query", "update", "delete"
        context_id: Identifier for the context
        data: Optional data to store or update
        query: Optional query string for semantic search
        
    Returns:
        Operation result
    """
    client = get_client()
    
    if operation == "store":
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