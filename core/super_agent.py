#!/usr/bin/env python3
# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import logging
from typing import Dict, List, Any, Optional, Callable, Awaitable

from core.pydantic_integration import PydanticAIIntegration
from core.mcp_server import get_mcp_manager

logger = logging.getLogger("wrenchai.super_agent")

class SuperAgent:
    """The SuperAgent for executing playbooks"""
    
    def __init__(
        self, 
        verbose: bool = False,
        model: Optional[str] = None,
        mcp_config_path: Optional[str] = None
    ):
        """Initialize the SuperAgent
        
        Args:
            verbose: Whether to enable verbose output
            model: Optional LLM model to use
            mcp_config_path: Optional path to MCP server configuration
        """
        self.verbose = verbose
        self.model = model or "anthropic:claude-3.5-sonnet-20240229"
        self.mcp_config_path = mcp_config_path or "mcp_config.json"
        
        # Initialize Pydantic AI integration
        self.pydantic_ai = PydanticAIIntegration(model=self.model)
        self.pydantic_ai.setup_environment()
        
        # Initialize MCP server manager
        self.mcp_manager = get_mcp_manager(self.mcp_config_path)
        
        # Message callback for interactive communication
        self.message_callback: Optional[Callable[[str], Awaitable[str]]] = None
        
        # Progress callback for updating progress
        self.progress_callback: Optional[Callable[[float, str], None]] = None
    
    def set_message_callback(
        self, 
        callback: Callable[[str], Awaitable[str]]
    ) -> None:
        """Set a callback for interactive messaging
        
        Args:
            callback: Async function that takes a message and returns a response
        """
        self.message_callback = callback
    
    def set_progress_callback(
        self, 
        callback: Callable[[float, str], None]
    ) -> None:
        """Set a callback for progress updates
        
        Args:
            callback: Function that takes a progress percentage and message
        """
        self.progress_callback = callback
    
    async def ask_user(self, message: str) -> str:
        """Ask the user a question and get a response
        
        Args:
            message: The message to display to the user
            
        Returns:
            The user's response
        """
        if self.message_callback:
            return await self.message_callback(message)
        
        # Default implementation for CLI
        print(f"\n{message}")
        return input("Your answer: ")
    
    def update_progress(self, percentage: float, message: str) -> None:
        """Update execution progress
        
        Args:
            percentage: Progress percentage (0-100)
            message: Progress message
        """
        if self.progress_callback:
            self.progress_callback(percentage, message)
        elif self.verbose:
            print(f"[{percentage:.1f}%] {message}")
    
    def _get_playbook_system_prompt(self, playbook: Dict[str, Any]) -> str:
        """Generate a system prompt for the playbook
        
        Args:
            playbook: Playbook configuration
            
        Returns:
            System prompt for the SuperAgent
        """
        return f"""
        You are the WrenchAI SuperAgent, responsible for executing the '{playbook.get('title', 'Unnamed')}' playbook.
        
        PLAYBOOK DESCRIPTION:
        {playbook.get('description', 'No description provided')}
        
        YOUR GOAL:
        Execute this playbook step by step, gathering information when needed, and producing the expected outputs.
        
        IMPORTANT GUIDELINES:
        1. Follow the playbook steps in order
        2. Request any necessary information from the user when required
        3. Provide clear explanations of what you're doing
        4. Regularly report progress
        5. Clearly indicate when the execution is complete
        
        Always aim to deliver the highest quality results possible.
        """
    
    async def execute_playbook(
        self, 
        playbook: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a playbook
        
        Args:
            playbook: Playbook configuration
            parameters: Optional parameter overrides
            
        Returns:
            Results of the playbook execution
        """
        # Prepare the agent
        system_prompt = self._get_playbook_system_prompt(playbook)
        agent = self.pydantic_ai.create_agent(
            name="SuperAgent",
            instructions=system_prompt,
            model=self.model
        )
        
        # Configure MCP servers if specified in the playbook
        mcp_servers = []
        if "mcp_servers" in playbook:
            for server_name in playbook["mcp_servers"]:
                server = self.mcp_manager.get_server_from_config(server_name)
                if server:
                    mcp_servers.append(server)
                    logger.info(f"Added MCP server: {server_name}")
        
        # Prepare input data for the agent
        input_data = {
            "playbook": {
                "id": playbook.get("id", ""),
                "title": playbook.get("title", "Unnamed"),
                "description": playbook.get("description", "No description"),
                "steps": playbook.get("steps", []),
            },
            "parameters": parameters or {}
        }
        
        # Execute the agent
        try:
            self.update_progress(0, "Starting playbook execution")
            
            # Stream response if verbose
            if self.verbose:
                complete_response = ""
                async for chunk in self.pydantic_ai.run_agent_stream(
                    agent, input_data, mcp_servers
                ):
                    print(chunk, end="", flush=True)
                    complete_response += chunk
                    
                return {"result": complete_response, "success": True}
            else:
                # Execute without streaming
                response = await self.pydantic_ai.run_agent(
                    agent, input_data, mcp_servers
                )
                return {"result": response, "success": True}
                
        except Exception as e:
            logger.error(f"Error executing playbook: {e}")
            return {"error": str(e), "success": False}