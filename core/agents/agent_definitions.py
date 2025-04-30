"""
Agent definitions and management for the Wrenchai framework.
Defines agent types, capabilities, and LLM assignments.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional

class AgentType(Enum):
    """Types of agents in the system."""
    ORCHESTRATOR = auto()
    SPECIALIST = auto()
    REVIEWER = auto()

class AgentCapability(Enum):
    """Capabilities that agents can possess."""
    # Orchestrator capabilities
    PROJECT_PLANNING = auto()
    TASK_COORDINATION = auto()
    RESOURCE_ALLOCATION = auto()
    
    # Repository management
    REPOSITORY_MANAGEMENT = auto()
    GITHUB_ACTIONS = auto()
    DEPLOYMENT = auto()
    
    # Code related
    CODE_GENERATION = auto()
    DOCUSAURUS_SETUP = auto()
    CONTENT_GENERATION = auto()
    CODE_STANDARDIZATION = auto()
    DOCUMENTATION = auto()
    CODE_REVIEW = auto()
    
    # UI/UX related
    UI_DESIGN = auto()
    USER_FLOW = auto()
    ACCESSIBILITY = auto()
    
    # Quality assurance
    QUALITY_ASSURANCE = auto()
    STANDARDS_COMPLIANCE = auto()
    
    # Testing
    TEST_PLANNING = auto()
    TEST_AUTOMATION = auto()
    USER_TESTING = auto()
    FEEDBACK_ANALYSIS = auto()
    ACCEPTANCE_CRITERIA = auto()
    
    # Database
    DATABASE_MANAGEMENT = auto()
    DATA_MODELING = auto()
    PERFORMANCE_OPTIMIZATION = auto()

class LLMProvider(Enum):
    """Available LLM providers."""
    CLAUDE = "claude-3.7-sonnet"
    GPT4 = "gpt-4o"
    GEMINI = "gemini-2.5-flash"

@dataclass
class Agent:
    """Base agent class with type, capabilities, and LLM assignment."""
    name: str
    type: AgentType
    capabilities: List[AgentCapability]
    llm: LLMProvider
    description: Optional[str] = None
    is_active: bool = True
    
    def __post_init__(self):
        """Validate agent configuration after initialization."""
        self.validate_capabilities()
    
    def validate_capabilities(self):
        """Ensure agent has appropriate capabilities for its type."""
        if self.type == AgentType.ORCHESTRATOR:
            required = {
                AgentCapability.PROJECT_PLANNING,
                AgentCapability.TASK_COORDINATION,
                AgentCapability.RESOURCE_ALLOCATION
            }
            if not all(cap in self.capabilities for cap in required):
                raise ValueError(f"{self.name}: Orchestrator must have all required capabilities: {required}")
        
        elif self.type == AgentType.REVIEWER:
            required = {
                AgentCapability.CODE_REVIEW,
                AgentCapability.QUALITY_ASSURANCE,
                AgentCapability.STANDARDS_COMPLIANCE
            }
            if not all(cap in self.capabilities for cap in required):
                raise ValueError(f"{self.name}: Reviewer must have all required capabilities: {required}")

# Define all agents
AGENTS = {
    "SuperAgent": Agent(
        name="SuperAgent",
        type=AgentType.ORCHESTRATOR,
        capabilities=[
            AgentCapability.PROJECT_PLANNING,
            AgentCapability.TASK_COORDINATION,
            AgentCapability.RESOURCE_ALLOCATION
        ],
        llm=LLMProvider.CLAUDE,
        description="Primary orchestrator agent for project planning and coordination"
    ),
    
    "GithubJourneyAgent": Agent(
        name="GithubJourneyAgent",
        type=AgentType.SPECIALIST,
        capabilities=[
            AgentCapability.REPOSITORY_MANAGEMENT,
            AgentCapability.GITHUB_ACTIONS,
            AgentCapability.DEPLOYMENT
        ],
        llm=LLMProvider.GPT4,
        description="Specialist for GitHub repository management and deployment"
    ),
    
    "CodeGeneratorAgent": Agent(
        name="CodeGeneratorAgent",
        type=AgentType.SPECIALIST,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.DOCUSAURUS_SETUP,
            AgentCapability.CONTENT_GENERATION
        ],
        llm=LLMProvider.CLAUDE,
        description="Specialist for code and content generation"
    ),
    
    "CodifierAgent": Agent(
        name="CodifierAgent",
        type=AgentType.SPECIALIST,
        capabilities=[
            AgentCapability.CODE_STANDARDIZATION,
            AgentCapability.DOCUMENTATION,
            AgentCapability.CODE_REVIEW
        ],
        llm=LLMProvider.CLAUDE,
        description="Specialist for code standardization and documentation"
    ),
    
    "UXDesignerAgent": Agent(
        name="UXDesignerAgent",
        type=AgentType.SPECIALIST,
        capabilities=[
            AgentCapability.UI_DESIGN,
            AgentCapability.USER_FLOW,
            AgentCapability.ACCESSIBILITY
        ],
        llm=LLMProvider.GPT4,
        description="Specialist for UI/UX design and accessibility"
    ),
    
    "InspectorAgent": Agent(
        name="InspectorAgent",
        type=AgentType.REVIEWER,
        capabilities=[
            AgentCapability.CODE_REVIEW,
            AgentCapability.QUALITY_ASSURANCE,
            AgentCapability.STANDARDS_COMPLIANCE
        ],
        llm=LLMProvider.CLAUDE,
        description="Code review and quality assurance specialist"
    ),
    
    "TestEngineerAgent": Agent(
        name="TestEngineerAgent",
        type=AgentType.SPECIALIST,
        capabilities=[
            AgentCapability.TEST_PLANNING,
            AgentCapability.TEST_AUTOMATION,
            AgentCapability.QUALITY_ASSURANCE
        ],
        llm=LLMProvider.CLAUDE,
        description="Specialist for test planning and automation"
    ),
    
    "UATAgent": Agent(
        name="UATAgent",
        type=AgentType.SPECIALIST,
        capabilities=[
            AgentCapability.USER_TESTING,
            AgentCapability.FEEDBACK_ANALYSIS,
            AgentCapability.ACCEPTANCE_CRITERIA
        ],
        llm=LLMProvider.GEMINI,
        description="User acceptance testing and feedback analysis"
    ),
    
    "DBA": Agent(
        name="DBA",
        type=AgentType.SPECIALIST,
        capabilities=[
            AgentCapability.DATABASE_MANAGEMENT,
            AgentCapability.DATA_MODELING,
            AgentCapability.PERFORMANCE_OPTIMIZATION
        ],
        llm=LLMProvider.CLAUDE,
        description="Database management and optimization specialist"
    )
}

def get_agent(name: str) -> Agent:
    """Retrieve an agent by name."""
    if name not in AGENTS:
        raise ValueError(f"Agent {name} not found")
    return AGENTS[name]

def get_agents_by_type(agent_type: AgentType) -> List[Agent]:
    """Get all agents of a specific type."""
    return [agent for agent in AGENTS.values() if agent.type == agent_type]

def get_agents_by_capability(capability: AgentCapability) -> List[Agent]:
    """Get all agents with a specific capability."""
    return [agent for agent in AGENTS.values() if capability in agent.capabilities]

def get_active_agents() -> List[Agent]:
    """Get all currently active agents."""
    return [agent for agent in AGENTS.values() if agent.is_active] 