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
        """Initialize base agent."""
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
        """Clean up agent resources."""
        await self.message_queue.clear()
        await self.tool_registry.clear()
        await self.session.close()
    
    async def send_message(self, recipient: str, content: str, message_type: str = "text"):
        """Send a message to another agent."""
        await self.message_queue.put({
            "sender": self.name,
            "recipient": recipient,
            "content": content,
            "type": message_type
        })
    
    async def receive_message(self) -> Optional[dict]:
        """Receive a message from the queue."""
        return await self.message_queue.get()
    
    async def register_tool(self, tool_name: str, tool_function: callable):
        """Register a tool with the tool registry."""
        await self.tool_registry.register(tool_name, tool_function)
    
    async def use_tool(self, tool_name: str, **kwargs):
        """Use a registered tool."""
        tool = await self.tool_registry.get(tool_name)
        if tool:
            return await tool(**kwargs)
        raise ValueError(f"Tool {tool_name} not found") 