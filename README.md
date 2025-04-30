# Wrench AI

This repository contains the code for Wrench AI, an open-source agentic AI framework. The framework allows you to define and orchestrate intelligent agents to perform complex tasks by combining the power of Large Language Models (LLMs) with Bayesian reasoning, Model Context Protocol (MCP), and a flexible tool integration system.

## Architecture

```
┌───────────────┐    ┌────────────────┐    ┌─────────────────┐
│  Streamlit UI │────│ FastAPI Backend │────│ Agent Framework │
└───────────────┘    └────────────────┘    └─────────────────┘
                                                │       │
                            ┌─────────────────┐ │       │ ┌────────────────┐
                            │ Bayesian Engine  │─┘       └─│   Tool System  │
                            └─────────────────┘           └────────────────┘
```

## Key Features

- **Pydantic-AI Integration**: Fully compliant Pydantic-AI agents with proper dependency injection
- **PyMC Integration**: Bayesian reasoning and decision-making under uncertainty
- **YAML Configuration**: Easy-to-edit configuration for agents, tools, and workflows
- **Dynamic Tool Registry**: Plug-and-play tools with dependency resolution
- **FastAPI Backend**: Performant API with websocket support
- **Streamlit UI**: User-friendly interface for interacting with agents
- **Model Context Protocol**: Flexible context management across multiple backends
- **Streaming Support**: Built-in streaming for real-time agent responses
- **Type Safety**: Strong typing with generics for better code quality

## Agent Interaction Patterns

The framework supports various agent interaction patterns:

1. **Work-in-Parallel**: Multiple agents working concurrently
2. **Self-Feedback Loop**: Agent improves its output through iteration
3. **Partner-Feedback Loop**: Agents collaborate by iteratively refining each other's work
4. **Conditional Process**: Workflow with conditional branching
5. **Agent-versus-Agent**: Competitive agent interactions
6. **Handoff Pattern**: Sequential workflow with clear transitions

## Getting Started

1.  **Clone the Repository:**

    ```bash
    git clone https://github.com/wrenchchatrepo/wrenchai.git
    cd wrenchai
    ```

2.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    pip install -r streamlit_app/requirements.txt
    ```

3.  **Run the FastAPI Backend:**

    ```bash
    uvicorn core.api:app --reload
    ```

    This will start the backend API server.

4.  **Run the Streamlit App:**

    ```bash
    streamlit run streamlit_app/app.py
    ```

    This will open the application in your web browser. The UI will connect to the backend API.

## Project Structure

The repository is organized as follows:

```
wrenchai/
├── .gitignore          # Files and directories to ignore in Git
├── LICENSE             # Project license (MIT License)
├── README.md           # Project description and instructions
├── requirements.txt    # Python dependencies for the core framework
├── streamlit_app/      # Directory for the Streamlit UI
│   ├── app.py          # Main Streamlit application file
│   └── requirements.txt# Python dependencies for the Streamlit app
├── core/               # Core framework logic
│   ├── agents/         # Agent definitions
│   │   ├── super_agent.py      # Super agent class
│   │   ├── inspector_agent.py  # Inspector agent class
│   │   ├── journey_agent.py    # Base class for Journey agents
│   │   ├── github_journey_agent.py # GitHub specialized journey agent
│   │   └── __init__.py
│   ├── agent_system.py # Pydantic-AI agent management system
│   ├── api.py          # FastAPI backend implementation
│   ├── bayesian_engine.py # PyMC-based Bayesian reasoning engine
│   ├── config_loader.py  # Configuration loading and validation
│   ├── tool_system.py    # Tool registry and management
│   ├── configs/        # YAML configuration files
│   │   ├── agents.yaml   # Agent role definitions
│   │   ├── tools.yaml    # Tool definitions with dependencies
│   │   ├── playbooks.yaml # Workflow definitions
│   │   ├── super_agent_config.yaml
│   │   ├── inspector_agent_config.yaml
│   │   ├── journey_agent_template.yaml
│   │   ├── playbook_template.yaml
│   │   └── pricing_data.yaml
│   ├── playbooks/      # Playbook definitions (YAML)
│   │   └── example_playbook.yaml # Example playbook
│   ├── tools/          # Tool implementations
│   │   ├── web_search.py      # Example tool: Web search
│   │   ├── code_execution.py  # Example tool: Code execution
│   │   ├── github_tool.py     # GitHub integration tool
│   │   ├── mcp.py             # Model Context Protocol implementation
│   │   ├── bayesian_tools.py  # PyMC bridge for bayesian reasoning
│   │   ├── __init__.py
│   │   └── ...  # Other tools
│   ├── utils.py        # Utility functions (e.g., cost calculation, logging)
│   └── __init__.py
├── docker/            # Docker-related files (future)
│    └── ...
└── tests/              # Unit tests (future)
    └── ...
```

*   **`core/`**: Contains the core logic of the agentic framework, including agent definitions, configuration files, playbooks, and tools.
*   **`core/agents/`**: Defines the agent classes (`SuperAgent`, `InspectorAgent`, `JourneyAgent`, etc.)
*   **`core/agent_system.py`**: Implements the Pydantic-AI based agent system
*   **`core/api.py`**: Provides the FastAPI backend endpoints
*   **`core/bayesian_engine.py`**: Implements the PyMC-based Bayesian reasoning engine
*   **`core/config_loader.py`**: Handles configuration loading and validation
*   **`core/tool_system.py`**: Manages the tool registry and dependencies
*   **`core/configs/`**: Stores YAML configuration files for agents, playbooks, and tools
*   **`core/playbooks/`**: Contains example playbooks in YAML format
*   **`core/tools/`**: Implements tools that agents can use (web search, MCP, Bayesian reasoning, etc.)
*   **`core/utils.py`**: Provides utility functions
*   **`streamlit_app/`**: Contains the Streamlit user interface
*   **`docker/`**:  Contains Docker-related files (future)
*   **`tests/`**: Contains unit tests (future)

## Roadmap

### MVP Implementation

1. **Core Framework Components**
   - Base Agent Structure ✅
   - Agent Communication System 🚧
   - Tool Registry ✅
   - Message Queue ✅
   - Database Integration 🚧
   - Logging System ✅
   - Error Handling 🚧
   - Security Layer 🚧

2. **MVP Agents**
   - SuperAgent (In Progress 🚧)
     - Orchestration and task delegation
     - Progress monitoring
     - Result aggregation
   - InspectorAgent (In Progress 🚧)
     - Code analysis and quality assurance
     - Standards checking
     - Improvement suggestions
   - JourneyAgent (Planned 📋)
     - User interaction management
     - Context tracking
     - Conversation management
   - DBAAgent (Planned 📋)
     - Database operations
     - Query optimization
     - Schema management
   - TestEngineerAgent (Planned 📋)
     - Test suite design
     - Coverage analysis
     - Result reporting

3. **FastAPI Backend Implementation**
   - Basic API structure with versioning ✅
   - Core endpoints with validation ✅
   - Database integration with SQLAlchemy ✅
   - Query optimization ✅
   - WebSocket support ✅
   - Basic authentication ✅
   - Error handling ✅
   - Rate limiting ✅
   - CORS configuration ✅
   - Health check endpoints ✅

4. **Streamlit Implementation**
   - Basic UI components ✅
   - State management ✅
   - Session handling ✅
   - Authentication flow ✅
   - WebSocket integration ✅

5. **Documentation**
   - Basic API documentation ✅
   - Code documentation ✅
   - Type hints ✅
   - OpenAPI schema ✅
   - Architecture documentation ✅

### Post-MVP Implementation

1. **Enhanced Content Generation**
   - GitHub Projects Auto-Sync
   - Technical Articles Pipeline
   - Code Examples Enhancement

2. **Advanced UI/UX Features**
   - Dynamic Visualizations
   - Enhanced Navigation
   - Accessibility Improvements

3. **Performance Optimizations**
   - Code Splitting
   - Asset Optimization
   - Caching Strategy

4. **Analytics and Monitoring**
   - User Behavior Analytics
   - Performance Monitoring
   - Automated Reports

5. **Security Enhancements**
   - Content Security
   - Access Control
   - Audit Logging

6. **Post-MVP Agents**
   - DevOpsAgent
     - CI/CD pipeline optimization
     - Infrastructure management
   - InfoSecAgent
     - Security audits
     - Compliance checking
   - UXDesignerAgent
     - Interface design
     - User flow optimization
   - ZeroKProofAgent
     - Protocol selection
     - Proof generation
   - DataScientistAgent
     - Data preprocessing
     - Model training
   - ParalegalAgent
     - Legal compliance
     - Document analysis
   - ComptrollerAgent
     - Resource tracking
     - Cost optimization
   - GCPArchitectAgent
     - Cloud optimization
     - Architecture design
   - CodeGeneratorAgent
     - Template generation
     - Code scaffolding
   - WebResearcherAgent
     - Information gathering
     - Data synthesis

For detailed implementation plans and timelines, see:
- [MVP Implementation Plan](MVP_IMPLEMENTATION_PLAN.md)
- [Post-MVP Implementation Plan](POST_MVP_IMPLEMENTATION_PLAN.md)

## Contributing

We welcome contributions to Wrench AI!  If you'd like to contribute, please follow these guidelines:

1.  **Fork the repository:** Create a fork of the repository on your own GitHub account.
2.  **Create a branch:** Create a new branch for your feature or bug fix.  Use a descriptive name (e.g., `feature/add-web-search-tool`, `bugfix/fix-cost-calculation`).
3.  **Make your changes:** Implement your feature or fix the bug.
4.  **Write tests:**  Write unit tests to ensure that your code works as expected and doesn't break existing functionality. (We're working on setting up the testing framework).
5.  **Commit your changes:** Commit your changes with clear and concise commit messages.
6.  **Push your branch:** Push your branch to your forked repository.
7.  **Create a pull request:** Create a pull request from your branch to the `main` branch of the `wrenchchatrepo/wrenchai` repository.
8. **Code Review**: Wait for a code review.

Please make sure your code adheres to the following guidelines:

*   Follow the existing code style.
*   Write clear and concise code.
*   Comment your code where necessary.
*   Write unit tests.
*   Keep your pull requests focused on a single feature or bug fix.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
