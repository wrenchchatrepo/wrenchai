"""Playbook Service for the WrenchAI Streamlit application.

This module provides a service for interacting with playbook-related
endpoints of the WrenchAI API.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union, TypeVar, cast
from datetime import datetime

from streamlit_app.services.api_client import ApiClient, ResourceClient, ApiError
from streamlit_app.models.playbook_config import PlaybookConfig, PlaybookMetadata
from streamlit_app.models.playbook_utils import convert_to_core_format

logger = logging.getLogger(__name__)


class PlaybookService:
    """Service for playbook-related operations."""
    
    def __init__(self, api_client: ApiClient):
        """Initialize the playbook service.
        
        Args:
            api_client: API client for making requests
        """
        self.api_client = api_client
        self.resource_client = ResourceClient(
            api_client=api_client,
            resource_path="api/playbooks",
            response_model=self._parse_playbook
        )
    
    def _parse_playbook(self, data: Dict[str, Any]) -> PlaybookConfig:
        """Parse a playbook from API response data.
        
        Args:
            data: API response data
            
        Returns:
            Parsed PlaybookConfig
        """
        try:
            # Try to parse as PlaybookConfig
            return PlaybookConfig.model_validate(data)
        except Exception as e:
            logger.warning(f"Error parsing playbook, falling back to minimal parsing: {e}")
            # Fall back to minimal parsing
            return PlaybookConfig(
                id=data.get("id", ""),
                metadata=PlaybookMetadata(
                    name=data.get("name", "Unknown Playbook"),
                    description=data.get("description", "No description available"),
                    version=data.get("version", "1.0.0"),
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                ),
                steps=data.get("steps", []),
            )
    
    async def list_playbooks(self, category: Optional[str] = None) -> List[PlaybookConfig]:
        """List available playbooks.
        
        Args:
            category: Optional category to filter by
            
        Returns:
            List of available playbooks
            
        Raises:
            ApiError: If the request fails
        """
        params = {}
        if category:
            params["category"] = category
        
        try:
            return await self.resource_client.list(params=params)
        except ApiError as e:
            logger.error(f"Error listing playbooks: {e}")
            raise
    
    async def get_playbook(self, playbook_id: str) -> PlaybookConfig:
        """Get a specific playbook by ID.
        
        Args:
            playbook_id: Playbook ID
            
        Returns:
            Playbook configuration
            
        Raises:
            ApiError: If the request fails
        """
        try:
            return await self.resource_client.get(playbook_id)
        except ApiError as e:
            logger.error(f"Error getting playbook {playbook_id}: {e}")
            raise
    
    async def create_playbook(self, playbook: PlaybookConfig) -> PlaybookConfig:
        """Create a new playbook.
        
        Args:
            playbook: Playbook configuration
            
        Returns:
            Created playbook configuration
            
        Raises:
            ApiError: If the request fails
        """
        try:
            # Convert to dictionary
            playbook_data = playbook.model_dump(exclude_none=True)
            return await self.resource_client.create(playbook_data)
        except ApiError as e:
            logger.error(f"Error creating playbook: {e}")
            raise
    
    async def update_playbook(self, playbook_id: str, playbook: PlaybookConfig) -> PlaybookConfig:
        """Update an existing playbook.
        
        Args:
            playbook_id: Playbook ID
            playbook: Updated playbook configuration
            
        Returns:
            Updated playbook configuration
            
        Raises:
            ApiError: If the request fails
        """
        try:
            # Convert to dictionary
            playbook_data = playbook.model_dump(exclude_none=True)
            return await self.resource_client.update(playbook_id, playbook_data)
        except ApiError as e:
            logger.error(f"Error updating playbook {playbook_id}: {e}")
            raise
    
    async def delete_playbook(self, playbook_id: str) -> bool:
        """Delete a playbook.
        
        Args:
            playbook_id: Playbook ID
            
        Returns:
            True if deleted successfully
            
        Raises:
            ApiError: If the request fails
        """
        try:
            return await self.resource_client.delete(playbook_id)
        except ApiError as e:
            logger.error(f"Error deleting playbook {playbook_id}: {e}")
            raise
    
    async def execute_playbook(self, playbook_id: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a playbook.
        
        Args:
            playbook_id: Playbook ID
            parameters: Optional parameters for execution
            
        Returns:
            Execution response with execution ID
            
        Raises:
            ApiError: If the request fails
        """
        try:
            # Prepare execution data
            execution_data = {
                "playbook_id": playbook_id,
                "parameters": parameters or {}
            }
            
            # Send execution request
            response = await self.api_client.post(
                endpoint=f"api/playbooks/{playbook_id}/execute",
                json_data=execution_data
            )
            
            return response.json()
        except ApiError as e:
            logger.error(f"Error executing playbook {playbook_id}: {e}")
            raise
    
    async def execute_playbook_from_config(self, playbook: PlaybookConfig, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a playbook from a configuration object.
        
        Args:
            playbook: Playbook configuration
            parameters: Optional parameters for execution
            
        Returns:
            Execution response with execution ID
            
        Raises:
            ApiError: If the request fails
        """
        try:
            # Convert to core format
            core_format = convert_to_core_format(playbook)
            
            # Add parameters if provided
            if parameters:
                core_format["parameters"] = parameters
            
            # Send execution request
            response = await self.api_client.post(
                endpoint="api/playbooks/execute",
                json_data=core_format
            )
            
            return response.json()
        except Exception as e:
            logger.error(f"Error executing playbook from config: {e}")
            raise ApiError(f"Error executing playbook: {str(e)}")
    
    async def get_available_categories(self) -> List[str]:
        """Get available playbook categories.
        
        Returns:
            List of available categories
            
        Raises:
            ApiError: If the request fails
        """
        try:
            response = await self.api_client.get(
                endpoint="api/playbooks/categories"
            )
            
            data = response.json()
            return data.get("categories", [])
        except ApiError as e:
            logger.error(f"Error getting playbook categories: {e}")
            # Return empty list instead of raising
            return []