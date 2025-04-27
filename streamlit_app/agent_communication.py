"""
Agent Communication Module

This module handles communication with the WrenchAI backend agents through FastAPI endpoints.
It implements async communication patterns and proper error handling.
"""

from typing import Dict, List, Optional, Any
import logging
from httpx import AsyncClient, HTTPError, TimeoutException

logger = logging.getLogger(__name__)

class AgentCommunicationError(Exception):
    """Custom exception for agent communication errors."""
    pass

class AgentCommunication:
    """Handles communication with WrenchAI agents."""
    
    def __init__(self, client: AsyncClient):
        """
        Initialize agent communication handler.
        
        Args:
            client: Configured AsyncClient instance
        """
        self.client = client
    
    async def send_message(
        self,
        message: str,
        agent_id: Optional[str] = None,
        playbook: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Send a message to an agent and get the response.
        
        Args:
            message: User message to send
            agent_id: Optional ID of specific agent to communicate with
            playbook: Optional playbook name to use
            attachments: Optional list of file attachments
            
        Returns:
            Dict containing agent response and any additional data
            
        Raises:
            AgentCommunicationError: If communication with agent fails
        """
        try:
            # Prepare request data
            data = {
                "message": message,
                "agent_id": agent_id,
                "playbook": playbook,
                "attachments": attachments or []
            }
            
            # Send request to chat endpoint
            response = await self.client.post("/api/chat", json=data)
            response.raise_for_status()
            
            return response.json()
            
        except TimeoutException:
            error_msg = "Request to agent timed out"
            logger.error(error_msg)
            raise AgentCommunicationError(error_msg)
            
        except HTTPError as e:
            error_msg = f"HTTP error communicating with agent: {str(e)}"
            logger.error(error_msg)
            raise AgentCommunicationError(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error in agent communication: {str(e)}"
            logger.error(error_msg)
            raise AgentCommunicationError(error_msg)
    
    async def create_agent(
        self,
        role: str,
        playbook: Optional[str] = None
    ) -> str:
        """
        Create a new agent instance.
        
        Args:
            role: Type of agent to create
            playbook: Optional playbook to associate with agent
            
        Returns:
            Newly created agent ID
            
        Raises:
            AgentCommunicationError: If agent creation fails
        """
        try:
            data = {
                "role": role,
                "playbook": playbook
            }
            
            response = await self.client.post("/api/agents/create", json=data)
            response.raise_for_status()
            
            result = response.json()
            return result["agent_id"]
            
        except Exception as e:
            error_msg = f"Failed to create agent: {str(e)}"
            logger.error(error_msg)
            raise AgentCommunicationError(error_msg)
    
    async def check_health(self) -> bool:
        """
        Check if the agent system is healthy and available.
        
        Returns:
            True if system is healthy, False otherwise
        """
        try:
            response = await self.client.get("/api/health")
            response.raise_for_status()
            
            result = response.json()
            return result.get("status") == "ok"
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
    
    async def list_agents(self) -> List[Dict[str, Any]]:
        """
        Get list of available agent types.
        
        Returns:
            List of agent definitions with capabilities
            
        Raises:
            AgentCommunicationError: If request fails
        """
        try:
            response = await self.client.get("/api/agents")
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            error_msg = f"Failed to list agents: {str(e)}"
            logger.error(error_msg)
            raise AgentCommunicationError(error_msg)
    
    async def list_playbooks(self) -> List[Dict[str, Any]]:
        """
        Get list of available playbooks.
        
        Returns:
            List of playbook definitions
            
        Raises:
            AgentCommunicationError: If request fails
        """
        try:
            response = await self.client.get("/api/playbooks")
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            error_msg = f"Failed to list playbooks: {str(e)}"
            logger.error(error_msg)
            raise AgentCommunicationError(error_msg) 