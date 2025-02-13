# Wrench AI

This repository contains the code for Wrench AI, an open-source agentic AI framework. The framework allows you to define and orchestrate intelligent agents to perform complex tasks by combining the power of Large Language Models (LLMs) with Bayesian reasoning and a flexible tool integration system.

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

3.  **Run the Streamlit App:**

    ```bash
    streamlit run streamlit_app/app.py
    ```

    This will open the application in your web browser.

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
│   │   └── __init__.py
│   ├── configs/        # YAML configuration files
│   │   ├── super_agent_config.yaml
│   │   ├── inspector_agent_config.yaml
│   │   ├── journey_agent_template.yaml
│   │   ├── playbook_template.yaml
│   │   └── pricing_data.yaml
│   ├── playbooks/      # Playbook definitions (YAML)
│   │   └── example_playbook.yaml # Example playbook
│   ├── tools/          # Tool implementations
│   │   ├── web_search.py       # Example tool: Web search
│   │   ├── code_execution.py    # Example tool: Code execution
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
*   **`core/agents/`**: Defines the `SuperAgent`, `InspectorAgent`, and `JourneyAgent` classes.
*   **`core/configs/`**: Stores YAML configuration files for agents, playbooks, and pricing data.
*   **`core/playbooks/`**: Contains example playbooks in YAML format.
*   **`core/tools/`**: Implements the tools that agents can use (e.g., web search, code execution).
*   **`core/utils.py`**: Provides utility functions like cost calculation and logging.
*   **`streamlit_app/`**: Contains the code for the Streamlit user interface.
*   **`docker/`**:  Will contain Dockerfiles and other Docker-related files for containerization (future).
*   **`tests/`**: Will contain unit tests for the framework (future).

## Roadmap

### Generation 1 (MVP)

*   Core agentic framework implementation:
    *   `SuperAgent`: Orchestrates the overall process, analyzes user requests, assigns roles and tools, and creates the execution plan.
    *   `InspectorAgent`: Monitors the progress of `Journey` agents, evaluates their outputs using Bayesian reasoning, and reports to the `SuperAgent`.
    *   `JourneyAgent`: Executes specific tasks according to assigned playbooks and utilizes allocated tools.
*   Bayesian reasoning for decision-making and evaluation within the `InspectorAgent`.
*   Basic tool integration (initial set: web search, code execution).
*   Streamlit UI for basic interaction:
    *   Simple user input for requests.
    *   Verbose output explaining agent actions and reasoning.
    *   Progress indicators.
    *   Cost tracking.
*   YAML-based configuration for agents and playbooks.
*   Cost tracking for LLM API usage and (basic) GCP resource usage.
*   Dockerization of agents for isolation and reproducibility.
*   GitHub integration for version control, collaboration, and CI/CD.

### Generation 2 (Post-MVP)

*   **Visual Workflow Editor (React-based):** Replace YAML playbooks with a drag-and-drop interface for creating and managing agent workflows, inspired by tools like Praison.ai's canvas.
*   **Expanded Tool Catalog:** Add more pre-built tools to the framework, covering a wider range of functionalities.
*   **Advanced Data Connection Management:** Implement a more robust and user-friendly system for managing connections to various data sources (databases, cloud storage, APIs).
*   **Multiple Trigger Mechanisms:** Support different trigger types for agent execution, including:
    *   Schedule triggers (e.g., run every hour).
    *   Webhook triggers (e.g., triggered by external events).
    *   Data change triggers (e.g., triggered by updates in a database).
*   **Enhanced Agent Communication:** Refine and expand the mechanisms for communication between agents, potentially using message queues or other asynchronous communication patterns.

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
