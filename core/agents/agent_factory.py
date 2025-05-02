"""
Agent factory for creating specialized agent instances.

This module provides factory methods to create specialized agents based on the agent role,
ensuring proper integration with the agent framework.
"""

import logging
import os
from typing import Dict, Any, List, Optional, Union

from .agent_definitions import Agent, get_agent, LLMProvider
from .codifier_agent import CodifierAgent, Codifier
from .ux_designer_agent import UXDesignerAgent, UXDesigner
from .uat_agent import UAT
from .agent_llm_mapping import agent_llm_manager
from .agent_state import agent_state_manager

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating specialized agent instances."""

    @staticmethod
    def create_agent(
        agent_name: str,
        llm_client: Any,
        tools: List[str],
        playbook_path: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Union[CodifierAgent, UXDesignerAgent, UAT, Any]:
        """
        Create a specialized agent instance based on the agent name.

        Args:
            agent_name: Name of the agent (must match agent definition)
            llm_client: LLM client to use for the agent
            tools: List of tools available to the agent
            playbook_path: Path to the playbook file
            context: Optional context data

        Returns:
            An instance of the requested agent
        """
        # Get the agent definition
        agent_def = get_agent(agent_name)
        agent_role = agent_def.name
        context = context or {}

        # Check for LLM override from agent-LLM mapping
        llm_id = agent_llm_manager.get_agent_llm(agent_name)
        if llm_id:
            logger.info(f"Using mapped LLM {llm_id} for agent {agent_name}")

        # Create the appropriate agent based on the role
        if agent_role == "UXDesignerAgent":
            design_system = context.get("design_system")
            accessibility_standards = context.get("accessibility_standards")
            return UXDesigner(
                name=agent_name,
                llm=llm_client,
                tools=tools,
                playbook_path=playbook_path,
                design_system=design_system,
                accessibility_standards=accessibility_standards
            )
        elif agent_role == "CodifierAgent":
            doc_standards = context.get("doc_standards")
            templates = context.get("templates")
            return Codifier(
                name=agent_name,
                llm=llm_client,
                tools=tools,
                playbook_path=playbook_path,
                doc_standards=doc_standards,
                templates=templates
            )
        elif agent_role == "UAT":
            acceptance_criteria_template = context.get("acceptance_criteria_template")
            stakeholders = context.get("stakeholders")
            return UAT(
                name=agent_name,
                llm=llm_client,
                tools=tools,
                playbook_path=playbook_path,
                acceptance_criteria_template=acceptance_criteria_template,
                stakeholders=stakeholders
            )
        else:
            # Generic agent creation (fallback)
            logger.warning(f"No specialized factory method for {agent_role}, creating generic agent")
            
            # For now, we'll return None for generic agents
            # In a real implementation, you would create a generic agent instance
            return None

    @staticmethod
    def register_agent_state(agent_instance: Any) -> str:
        """
        Register an agent instance with the state manager.

        Args:
            agent_instance: The agent instance to register

        Returns:
            Agent ID (used for state lookup)
        """
        agent_id = str(id(agent_instance))
        state = agent_state_manager.get_agent_state(agent_id)
        state.agent_name = getattr(agent_instance, "name", agent_id)
        return agent_id