#!/usr/bin/env python3
# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import logging
import asyncio # Import asyncio for sleep
from typing import Dict, List, Any, Optional, Callable, Awaitable

from core.pydantic_integration import PydanticAIIntegration
from core.mcp_server import get_mcp_manager

logger = logging.getLogger("wrenchai.super_agent")

# Retry configuration constants
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5

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

        # Also log progress updates
        logger.debug(f"Progress: {percentage:.1f}% - {message}")

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

        logger.info(f"Starting execution of playbook: {playbook.get('title', 'Unnamed')}")

        # List to hold names of servers we successfully started and need to stop
        servers_to_stop = []
        mcp_server_instances_for_pydantic_ai = []

        try:
            # Configure and start MCP servers if specified in the playbook
            if "mcp_servers" in playbook:
                logger.info("Configuring and starting required MCP servers...")
                self.update_progress(5, "Configuring MCP servers")
                for server_name in playbook["mcp_servers"]:
                    try:
                        started_server = self.mcp_manager.start_server(server_name)
                        if started_server:
                            servers_to_stop.append(server_name)
                            mcp_server_instances_for_pydantic_ai.append(started_server)
                            logger.info(f"Successfully started MCP server: {server_name}")
                        else:
                            logger.warning(f"MCP server '{server_name}' could not be started or is not configured.")
                    except Exception as e:
                        logger.error(f"Error starting MCP server {server_name}: {e}")
                        # Decide if a single failed server stops execution or if we continue
                        # For now, we'll log and continue, but this might need refinement
                        pass # Continue with other servers

                if mcp_server_instances_for_pydantic_ai:
                    self.update_progress(10, "Required MCP servers configured and started")
                else:
                    logger.warning("No required MCP servers were successfully started.")
                    self.update_progress(10, "No MCP servers started")


            self.update_progress(20, "Preparing input data")
            logger.info("Preparing input data for the agent...")
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
            logger.debug(f"Input data: {input_data}")
            self.update_progress(30, "Input data prepared")

            # Execute the agent with retry logic
            logger.info("Executing the agent...")
            self.update_progress(40, "Executing agent")

            attempts = 0
            success = False
            last_error = None
            response_result = None

            while attempts < MAX_RETRIES and not success:
                attempts += 1
                if attempts > 1:
                    logger.info(f"Retrying agent execution (Attempt {attempts}/{MAX_RETRIES})...")
                    self.update_progress(40 + (attempts - 1) * 10, f"Retrying agent (Attempt {attempts})")
                else:
                     logger.info(f"Starting agent execution (Attempt {attempts}/{MAX_RETRIES})...")

                try:
                    if self.verbose:
                        logger.debug("Streaming output enabled.")
                        complete_response = ""
                        async for chunk in self.pydantic_ai.run_agent_stream(
                            agent, input_data, mcp_server_instances_for_pydantic_ai
                        ):
                            print(chunk, end="", flush=True)
                            complete_response += chunk

                        logger.info("Agent execution completed successfully (streaming).")
                        logger.debug(f"Complete response: {complete_response}")
                        response_result = {"result": complete_response, "success": True}
                        success = True
                    else:
                        logger.debug("Streaming output disabled.")
                        response = await self.pydantic_ai.run_agent(
                            agent, input_data, mcp_server_instances_for_pydantic_ai
                        )
                        logger.info("Agent execution completed successfully.")
                        logger.debug(f"Response: {response}")
                        response_result = {"result": response, "success": True}
                        success = True

                except Exception as e:
                    last_error = e
                    logger.warning(f"Agent execution attempt {attempts} failed: {e}")
                    if attempts < MAX_RETRIES:
                        logger.info(f"Waiting {RETRY_DELAY_SECONDS} seconds before retrying...")
                        await asyncio.sleep(RETRY_DELAY_SECONDS)
                    else:
                        logger.error(f"Agent execution failed after {MAX_RETRIES} attempts.")

            if success:
                self.update_progress(90, "Agent execution completed")
                return response_result
            else:
                # Handle final failure after retries
                error_message = f"Failed to execute agent after {MAX_RETRIES} attempts. Last error: {last_error}"
                logger.error(error_message)
                self.update_progress(100, f"Execution failed: {last_error}")
                return {"error": error_message, "success": False}

        except Exception as e:
            # Catch any unexpected errors outside the retry loop
            logger.error(f"An unexpected error occurred during playbook execution: {e}")
            self.update_progress(100, f"Execution failed due to unexpected error: {e}")
            return {"error": f"Unexpected execution error: {e}", "success": False}
        finally:
            # Ensure all started servers are stopped
            if servers_to_stop:
                logger.info("Stopping MCP servers...")
                self.update_progress(95, "Stopping MCP servers")
                for server_name in servers_to_stop:
                    try:
                        self.mcp_manager.stop_server(server_name)
                    except Exception as e:
                        logger.error(f"Error stopping MCP server {server_name}: {e}")
                        # Continue stopping other servers even if one fails
                        pass
                logger.info("All started MCP servers stopped.")
                self.update_progress(100, "MCP servers stopped")