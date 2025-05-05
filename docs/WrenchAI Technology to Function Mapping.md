# WrenchAI Technology to Function Mapping

## Technology Components

### 1. Pydantic/Pydantic-AI
- **Agents**: Core agent definitions in `/core/agents/` - used for data validation and LLM integration
- **API**: Schema definitions in `/fastapi/app/schemas/` for API request/response validation
- **Tools**: Parameter validation for tool inputs in `/core/tools/`

### 2. FastAPI
- **Web API**: Main application entry at `/fastapi/app/main.py`
- **Endpoints**: Agent, playbook, and task management in `/fastapi/app/api/v1/endpoints/`
- **WebSockets**: Real-time communication in `/fastapi/app/api/v1/endpoints/websocket.py`

### 3. Streamlit
- **UI**: Main application interface in `/streamlit_app/app.py`
- **Pages**: Agent manager, playbook executor, and metrics dashboard in `/streamlit_app/pages/`
- **Components**: Reusable UI elements and error handling

### 4. PyMC
- **Bayesian Engine**: Probabilistic reasoning in `/core/bayesian_engine.py`
- **Bayesian Tools**: Inference operations in `/core/tools/bayesian_tools.py`
- **Examples**: Notebooks in `/pymc/` demonstrating capabilities

### 5. SQLAlchemy
- **Database Models**: Data structure definitions in `/core/db/models.py`
- **Repositories**: Data access patterns in `/core/db/repositories.py`
- **Migrations**: Schema updates in `/alembic/versions/`

## Functional Areas & Their Component Relationships

### Agent System
- **Core**: `/core/agent_system.py` - Manages agents via Pydantic-AI
- **Dependencies**: Relies on ToolRegistry for capabilities and BayesianEngine for reasoning
- **Data Flow**: Config → AgentManager → AgentWrapper → LLM API → Results

### Tool System
- **Core**: `/core/tool_system.py` - Plugin architecture for agent tools
- **Components**: Web search, GitHub integration, code execution, database access
- **Data Flow**: Config → ToolRegistry → Tool Functions → Results to Agent

### Playbook System
- **Core**: Configured workflows in `/core/playbooks/` and `/core/configs/`
- **Execution**: Agent orchestration via `AgentManager.run_workflow()`
- **Status**: Core functionality complete, specific playbooks partially implemented

### MCP Components
- **Core**: Model Context Protocol in `/core/tools/mcp_*.py`
- **Status**: Basic implementation exists, advanced features in development
- **Function**: Enhances LLM context management for agents

## Implementation Status

The codebase shows varying levels of implementation completeness:

**Well Implemented**:
- Core agent and tool registry systems
- Basic FastAPI structure and endpoints
- Database models and SQLAlchemy integration
- Bayesian reasoning engine

**Partially Implemented**:
- Streamlit UI components
- MCP integration
- Specialized agent types
- Advanced workflows

**Planned Features** (from documentation):
- Advanced UI with chat interface
- Enhanced Bayesian features
- Specialized agent implementations
- Advanced tool integrations

## Cross-Component Relationships

- **Agent System ↔ Tool System**: Agents use tools via the registry
- **Agent System ↔ Bayesian Engine**: Probabilistic reasoning for agent decisions
- **Playbook System ↔ Agent System**: Playbooks orchestrate agent workflows
- **API Layer ↔ Agent System**: API exposes agent functionality to clients
- **Streamlit UI ↔ API Layer**: UI interacts with backend via API
- **MCP Components ↔ Agent System**: Enhance agent context handling
- **WebSocket Manager ↔ API ↔ UI**: Real-time updates between components

## Data Flow Overview

1. **Configuration**: YAML files define agents, tools, and playbooks
2. **Initialization**: System loads configurations and initializes components
3. **Task Execution**: 
   - User input → Streamlit → API → Agent Manager
   - Agent Manager → Tool Registry → External Services
   - Results → Agent Manager → API → Streamlit → User
4. **Persistence**:
   - Task data → Database Models → Database
   - Retrieve → Database → Models → API → UI

The system architecture demonstrates a well-structured foundation with clear component boundaries, though many advanced features mentioned in the implementation plans are still in development.