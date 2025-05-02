# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import logging
from typing import Dict, Any, Callable, Optional, List
import asyncio

# Try to import MCP components
try:
    from mcp.server.fastmcp import FastMCP
    # Import Pydantic AI Agent for integration with MCP server
    # Reference: https://ai.pydantic.dev/agents/
    from pydantic_ai import Agent
    MCP_SERVER_AVAILABLE = True
except ImportError:
    MCP_SERVER_AVAILABLE = False
    logging.warning("MCP server components not available. Install with 'pip install pydantic-ai[mcp]'")
    
    # Create stub classes for type checking
    class FastMCP:
        def __init__(self, *args, **kwargs): pass
        
        def tool(self): 
            def decorator(func): return func
            return decorator

class WrenchAIMCPServer:
    """MCP server for Wrench AI tools"""
    
    def __init__(self, name: str = "WrenchAI Server", model: str = "anthropic:claude-3-5-sonnet-20240229"):
        """Initialize the MCP server
        
        Args:
            name: Name of the server
            model: Model to use for agent tools
        """
        if not MCP_SERVER_AVAILABLE:
            raise ImportError("MCP server components not available. Install with 'pip install pydantic-ai[mcp]'")
            
        self.name = name
        self.model = model
        
        # Create the FastMCP server
        self.server = FastMCP(name)
        
        # Create a standard agent for tools
        self.agent = Agent(model, system_prompt="""
        You are an AI assistant that helps with various tasks.
        When you receive a task, analyze it carefully and provide a helpful response.
        Always use clear, concise language and focus on providing accurate information.
        """)
        
        # Register tools
        self._register_tools()
        
    def _register_tools(self):
        """Register tools with the server"""
        
        @self.server.tool()
        async def summarize(text: str) -> str:
            """Summarize a piece of text
            
            Args:
                text: The text to summarize
                
            Returns:
                A concise summary of the text
            """
            result = await self.agent.run(f"Summarize this text concisely:\n\n{text}")
            return result.output
        
        @self.server.tool()
        async def generate_code(language: str, task: str) -> str:
            """Generate code in a specific language
            
            Args:
                language: The programming language to use
                task: The task description
                
            Returns:
                Generated code snippet
            """
            result = await self.agent.run(
                f"Generate {language} code for the following task:\n\n{task}\n\n"
                f"Provide only the code without explanation."
            )
            return result.output
        
        @self.server.tool()
        async def analyze_sentiment(text: str) -> Dict[str, float]:
            """Analyze the sentiment of a text
            
            Args:
                text: The text to analyze
                
            Returns:
                Dictionary with sentiment scores
            """
            result = await self.agent.run(
                f"Analyze the sentiment of this text: {text}\n\n"
                f"Express the sentiment as scores from 0.0 to 1.0 for positive, negative, and neutral. "
                f"Return only a JSON object with these three keys."
            )
            
            # In a real implementation, we would parse the JSON
            # For this example, return a fixed structure
            return {
                "positive": 0.7,
                "negative": 0.1,
                "neutral": 0.2
            }
        
        @self.server.tool()
        async def answer_question(question: str, context: Optional[str] = None) -> str:
            """Answer a question based on optional context
            
            Args:
                question: The question to answer
                context: Optional context to use for answering
                
            Returns:
                Answer to the question
            """
            prompt = f"Question: {question}\n\n"
            if context:
                prompt += f"Context:\n{context}\n\n"
            prompt += "Please answer the question concisely."
            
            result = await self.agent.run(prompt)
            return result.output
    
    def run(self, port: int = 8000):
        """Run the MCP server on the specified port
        
        Args:
            port: Port to run the server on
        """
        # In a real implementation, this would start the server
        # For now, just log a message
        logging.info(f"MCP server '{self.name}' would start on port {port}")
        
    def stop(self):
        """Stop the MCP server"""
        # In a real implementation, this would stop the server
        # For now, just log a message
        logging.info(f"MCP server '{self.name}' would stop")

# Singleton server instance
_server_instance = None

def get_mcp_server(name: str = "WrenchAI Server", 
                model: str = "anthropic:claude-3-5-sonnet-20240229") -> Optional[WrenchAIMCPServer]:
    """Get the singleton MCP server instance
    
    Args:
        name: Name of the server
        model: Model to use for agent tools
        
    Returns:
        MCP server instance or None if not available
    """
    global _server_instance
    
    if not MCP_SERVER_AVAILABLE:
        logging.warning("MCP server components not available")
        return None
    
    if _server_instance is None:
        try:
            _server_instance = WrenchAIMCPServer(name, model)
        except Exception as e:
            logging.error(f"Error creating MCP server: {e}")
            return None
    
    return _server_instance