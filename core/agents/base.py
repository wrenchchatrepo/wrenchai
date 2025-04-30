"""Base agent class for the Wrenchai framework."""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from .agent_definitions import Agent, AgentType, AgentCapability, LLMProvider
from ..tools.message_queue import MessageQueue
from ..tools.tool_registry import ToolRegistry

class BaseAgent(Agent):
    """Base agent class with core functionality."""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        capabilities: List[AgentCapability],
        message_queue: MessageQueue,
        tool_registry: ToolRegistry,
        session: AsyncSession,
        agent_type: AgentType = AgentType.SPECIALIST,
        llm: LLMProvider = LLMProvider.CLAUDE,
    ):
        """
        Initializes a BaseAgent with core attributes and resources.
        
        Args:
            agent_id: Unique identifier for the agent.
            name: The agent's display name.
            description: A brief description of the agent's purpose or role.
            capabilities: List of capabilities assigned to the agent.
            agent_type: The type of agent, defaults to AgentType.SPECIALIST.
            llm: The LLM provider used by the agent, defaults to LLMProvider.CLAUDE.
        
        The agent is initialized with a message queue, tool registry, and asynchronous database session for managing communication, tool usage, and persistent resources.
        """
        super().__init__(
            name=name,
            type=agent_type,
            capabilities=capabilities,
            llm=llm,
            description=description
        )
        self.agent_id = agent_id
        self.message_queue = message_queue
        self.tool_registry = tool_registry
        self.session = session
    
    async def cleanup(self):
        """
        Asynchronously releases agent resources by clearing the message queue, tool registry, and closing the database session.
        """
        await self.message_queue.clear()
        await self.tool_registry.clear()
        await self.session.close()
    
    async def send_message(self, recipient: str, content: str, message_type: str = "text"):
        """
        Asynchronously sends a message to a specified recipient agent.
        
        Args:
            recipient: The name or identifier of the recipient agent.
            content: The message content to send.
            message_type: The type of the message (default is "text").
        """
        await self.message_queue.put({
            "sender": self.name,
            "recipient": recipient,
            "content": content,
            "type": message_type
        })
    
    async def receive_message(self) -> Optional[dict]:
        """
        Retrieves the next available message from the message queue.
        
        Returns:
            A dictionary representing the message if available, or None if the queue is empty.
        """
        return await self.message_queue.get()
    
    async def register_tool(self, tool_name: str, tool_function: callable):
        """
        Registers a tool with the agent's tool registry.
        
        Args:
            tool_name: The name to associate with the tool.
            tool_function: The callable implementing the tool's functionality.
        """
        await self.tool_registry.register(tool_name, tool_function)
    
    async def use_tool(self, tool_name: str, **kwargs):
        """
        Invokes a registered tool asynchronously by name with the provided arguments.
        
        Args:
            tool_name: The name of the tool to invoke.
            **kwargs: Arguments to pass to the tool function.
        
        Returns:
            The result returned by the tool function.
        
        Raises:
            ValueError: If the specified tool is not found in the registry.
        """
        tool = await self.tool_registry.get(tool_name)
        if tool:
            return await tool(**kwargs)
        raise ValueError(f"Tool {tool_name} not found") 