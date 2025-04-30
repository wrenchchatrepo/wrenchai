"""Agent-LLM mapping system for WrenchAI.

This module manages the mapping between agents and their assigned LLMs,
allowing dynamic assignment based on playbook specifications.
"""

import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum

from .agent_definitions import Agent, LLMProvider, AGENTS

logger = logging.getLogger(__name__)

class AgentLLMMapping(BaseModel):
    """Model for agent-LLM mappings."""
    agent_name: str = Field(..., description="Name of the agent")
    llm_id: str = Field(..., description="ID of the LLM to use")
    fallback_llm_id: Optional[str] = Field(None, description="Fallback LLM if primary is unavailable")
    priority: int = Field(default=0, description="Priority of this mapping (higher overrides lower)")
    source: str = Field(default="default", description="Source of this mapping (default, playbook, etc.)")

class LLMAvailability(BaseModel):
    """Model for LLM availability status."""
    llm_id: str = Field(..., description="ID of the LLM")
    available: bool = Field(..., description="Whether the LLM is available")
    quota_remaining: Optional[float] = Field(None, description="Remaining quota (if applicable)")
    error: Optional[str] = Field(None, description="Error message if unavailable")

class AgentLLMManager:
    """Manager for agent-LLM mappings."""
    
    def __init__(self):
        """
        Initializes the AgentLLMManager with empty mappings and LLM availability, then loads default agent-to-LLM mappings.
        """
        self.mappings: Dict[str, List[AgentLLMMapping]] = {}
        self.llm_availability: Dict[str, LLMAvailability] = {}
        self._initialize_default_mappings()
        
    def _initialize_default_mappings(self):
        """
        Loads default agent-to-LLM mappings and marks their LLMs as available.
        
        Iterates through all predefined agents, assigning each its default LLM with base priority and setting the LLM's availability status to available.
        """
        for agent_name, agent in AGENTS.items():
            self.add_mapping(
                AgentLLMMapping(
                    agent_name=agent_name,
                    llm_id=agent.llm.value,
                    source="default",
                    priority=0
                )
            )
            
            # Add default availability status
            self.llm_availability[agent.llm.value] = LLMAvailability(
                llm_id=agent.llm.value,
                available=True
            )
    
    def add_mapping(self, mapping: AgentLLMMapping):
        """
        Adds or replaces an agent-to-LLM mapping, prioritizing by source and mapping priority.
        
        If a mapping with the same source exists for the agent, it is replaced; otherwise, the new mapping is added. Mappings for each agent are sorted in descending order of priority.
        """
        if mapping.agent_name not in self.mappings:
            self.mappings[mapping.agent_name] = []
        
        # Check if mapping with same source already exists
        for i, existing in enumerate(self.mappings[mapping.agent_name]):
            if existing.source == mapping.source:
                # Replace existing mapping
                self.mappings[mapping.agent_name][i] = mapping
                return
        
        # Add new mapping
        self.mappings[mapping.agent_name].append(mapping)
        
        # Sort by priority (highest first)
        self.mappings[mapping.agent_name].sort(key=lambda m: m.priority, reverse=True)
    
    def add_mappings_from_playbook(self, agent_llms: Dict[str, str], playbook_name: str):
        """
        Adds agent-to-LLM mappings from a playbook with elevated priority.
        
        Each mapping is tagged with the playbook name as its source and assigned a higher priority to override defaults.
        """
        for agent_name, llm_id in agent_llms.items():
            self.add_mapping(
                AgentLLMMapping(
                    agent_name=agent_name,
                    llm_id=llm_id,
                    source=f"playbook:{playbook_name}",
                    priority=10  # Playbook mappings have higher priority
                )
            )
    
    def get_agent_llm(self, agent_name: str) -> Optional[str]:
        """
        Returns the LLM ID assigned to an agent, considering mapping priority, availability, and fallbacks.
        
        If no mapping is found or no available LLM exists, returns the agent's default LLM if defined, or None otherwise.
        
        Args:
            agent_name: The name of the agent.
        
        Returns:
            The LLM ID to use for the agent, or None if no suitable LLM is found.
        """
        if agent_name not in self.mappings or not self.mappings[agent_name]:
            # No mapping found, use default if agent exists in AGENTS
            if agent_name in AGENTS:
                return AGENTS[agent_name].llm.value
            return None
        
        # Get highest priority mapping
        for mapping in self.mappings[agent_name]:
            llm_id = mapping.llm_id
            
            # Check if LLM is available
            if llm_id in self.llm_availability and self.llm_availability[llm_id].available:
                return llm_id
            
            # Check fallback
            if mapping.fallback_llm_id:
                fallback = mapping.fallback_llm_id
                if fallback in self.llm_availability and self.llm_availability[fallback].available:
                    logger.info(f"Using fallback LLM {fallback} for agent {agent_name}")
                    return fallback
        
        # If no mapping is available, use default
        if agent_name in AGENTS:
            return AGENTS[agent_name].llm.value
        
        return None
    
    def update_llm_availability(self, llm_id: str, available: bool, error: Optional[str] = None):
        """
        Updates the availability status and error message for a specified LLM.
        
        Args:
            llm_id: The unique identifier of the LLM.
            available: Indicates whether the LLM is currently available.
            error: Optional error message describing why the LLM is unavailable.
        """
        if llm_id not in self.llm_availability:
            self.llm_availability[llm_id] = LLMAvailability(
                llm_id=llm_id,
                available=available,
                error=error
            )
        else:
            self.llm_availability[llm_id].available = available
            self.llm_availability[llm_id].error = error
            
        if not available:
            logger.warning(f"LLM {llm_id} marked as unavailable: {error}")
    
    def check_llm_availability(self, llm_id: str) -> bool:
        """
        Returns True if the specified LLM is currently available, otherwise False.
        
        Args:
            llm_id: The identifier of the LLM to check.
        
        Returns:
            True if the LLM is available; False if unavailable or not tracked.
        """
        if llm_id not in self.llm_availability:
            return False
        return self.llm_availability[llm_id].available
    
    def get_all_mappings(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Returns all agent-to-LLM mappings as dictionaries.
        
        Each agent name is mapped to a list of its LLM mappings, with each mapping represented as a dictionary.
        """
        return {
            agent: [mapping.dict() for mapping in mappings] 
            for agent, mappings in self.mappings.items()
        }
    
    def get_all_availability(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns the availability status of all LLMs managed by the system.
        
        Returns:
            A dictionary mapping each LLM ID to its availability status as a dictionary.
        """
        return {
            llm_id: status.dict() 
            for llm_id, status in self.llm_availability.items()
        }
    
    def reset_to_defaults(self):
        """
        Resets all agent-LLM mappings to their default state.
        
        Clears any custom mappings and reloads the default mappings from the agent registry.
        """
        self.mappings.clear()
        self._initialize_default_mappings()

# Global instance
agent_llm_manager = AgentLLMManager()