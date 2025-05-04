#!/usr/bin/env python3
# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional

# Check if Pydantic AI is available
try:
    import pydantic_ai
    from pydantic_ai import Agent, RunContext
    PYDANTIC_AI_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_AVAILABLE = False

# Try to import MCP components
try:
    from pydantic_ai.mcp import MCPServerHTTP, MCPServerStdio
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

logger = logging.getLogger("wrenchai.pydantic_integration")

class PydanticAIIntegration:
    """Integration with Pydantic AI for playbook execution"""
    
    def __init__(self, model: str = "anthropic:claude-3.5-sonnet-20240229"):
        """Initialize the Pydantic AI integration
        
        Args:
            model: The default LLM model to use
        """
        if not PYDANTIC_AI_AVAILABLE:
            raise ImportError(
                "Pydantic AI is required but not installed. "
                "Please install it with 'pip install pydantic-ai'"
            )
            
        self.model = model
        self.logger = logging.getLogger("wrenchai.pydantic_integration")
    
    def setup_environment(self) -> None:
        """Set up environment variables for Pydantic AI"""
        # Check for API keys in environment
        api_keys = {
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
            "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY"),
            "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY")
        }
        
        # Log which keys are available (but don't log the actual keys)
        for key_name, key_value in api_keys.items():
            if key_value:
                self.logger.info(f"{key_name} is set")
            else:
                self.logger.warning(f"{key_name} is not set")
        
        # Set Logfire configuration if available
        if "LOGFIRE_API_KEY" in os.environ:
            os.environ["PYDANTIC_AI_LOGFIRE"] = "true"
            self.logger.info("Logfire integration enabled")
    
    def create_agent(
        self, 
        name: str, 
        instructions: str, 
        model: Optional[str] = None
    ) -> Any:
        """Create a Pydantic AI agent
        
        Args:
            name: The agent's name
            instructions: The agent's instructions/system prompt
            model: Optional model override
            
        Returns:
            A Pydantic AI Agent instance
        """
        model = model or self.model
        
        self.logger.info(f"Creating agent '{name}' with model {model}")
        return Agent(
            name=name,
            instructions=instructions,
            model=model
        )
    
    def load_mcp_config(self, config_path: str) -> Dict[str, Any]:
        """Load MCP server configuration from a file
        
        Args:
            config_path: Path to the MCP configuration file
            
        Returns:
            Dictionary containing MCP server configuration
        """
        if not os.path.exists(config_path):
            self.logger.warning(f"MCP config file not found: {config_path}")
            return {}
            
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading MCP config: {e}")
            return {}
    
    def configure_mcp_server(
        self, 
        server_type: str,
        config: Dict[str, Any]
    ) -> Optional[Any]:
        """Configure an MCP server from a configuration
        
        Args:
            server_type: The type of server (http, stdio, etc.)
            config: Server configuration dictionary
            
        Returns:
            Configured MCP server instance or None if not available
        """
        if not MCP_AVAILABLE:
            self.logger.warning("MCP server support not available. Install with 'pip install pydantic-ai[mcp]'")
            return None
            
        if server_type == "http":
            return MCPServerHTTP(**config)
        elif server_type == "stdio":
            return MCPServerStdio(**config)
        else:
            self.logger.warning(f"Unknown MCP server type: {server_type}")
            return None
    
    async def run_agent(
        self, 
        agent: Any, 
        input_data: Any,
        mcp_servers: Optional[List[Any]] = None
    ) -> Any:
        """Run a Pydantic AI agent with optional MCP servers
        
        Args:
            agent: The Pydantic AI agent to run
            input_data: Input data for the agent
            mcp_servers: Optional list of MCP servers to use
            
        Returns:
            The agent's response
        """
        if mcp_servers and MCP_AVAILABLE:
            # Run with MCP servers
            async with agent.run_mcp_servers(*mcp_servers):
                return await agent.run(input_data)
        else:
            # Run without MCP servers
            return await agent.run(input_data)
    
    async def run_agent_stream(
        self, 
        agent: Any, 
        input_data: Any,
        mcp_servers: Optional[List[Any]] = None
    ) -> Any:
        """Run a Pydantic AI agent with streaming and optional MCP servers
        
        Args:
            agent: The Pydantic AI agent to run
            input_data: Input data for the agent
            mcp_servers: Optional list of MCP servers to use
            
        Returns:
            An async generator yielding response chunks
        """
        if mcp_servers and MCP_AVAILABLE:
            # Stream with MCP servers
            async with agent.run_mcp_servers(*mcp_servers):
                async for chunk in agent.run_stream(input_data):
                    yield chunk
        else:
            # Stream without MCP servers
            async for chunk in agent.run_stream(input_data):
                yield chunk