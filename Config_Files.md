# Config Files

*   `super_agent_config.yaml`: Configuration for the Super agent.
*   `inspector_agent_config.yaml`: Configuration for the Inspector agent.
*   `journey_agent_template.yaml`: A template for Journey agents, which can be customized for specific roles.
*   `playbook_template.yaml`: A template for playbooks.
*   `pricing_data.yaml`: A file to store pricing information (LLMs, GCP, etc.).

We'll also discuss how these files interact and how they can be used to instantiate agents and manage the framework.

**1. `super_agent_config.yaml`**

```yaml
# super_agent_config.yaml
role: Super
name: DefaultSuper
description: Default configuration for the Super agent.
llm: "gemini-1.5-flash"  # Default LLM for the Super agent
tools:
  - web_search
  - rag
  - memory
  - code_generation # Limited use for agent management tasks
default_uncertainty_threshold: 0.8  # Ask for clarification if uncertainty is above 80%
cost_estimation_enabled: true # Enable cost estimation before task execution
max_cost_per_task: 1.00 # USD.  Maximum cost allowed per task (optional).
```

**2. `inspector_agent_config.yaml`**

```yaml
# inspector_agent_config.yaml
role: Inspector
name: DefaultInspector
description: Default configuration for the Inspector agent.
llm: "gemini-1.5-flash" # Can be a different LLM if specialized for QC.
tools:
  - memory
  - data_analysis # Limited use for progress analysis
  - specialized_llm # Placeholder for QC-specific LLMs
acceptance_threshold: 0.9  # Reject work if probability of being acceptable is below 90%
qc_llms: # List of specialized LLMs for quality control
  code_quality: "code_review_llm_v2"
  content_quality: "content_quality_llm_v1"
  redaction_accuracy: "redaction_llm_v3"
  # Add other QC LLMs as needed
cost_monitoring_enabled: true  # Enable cost monitoring during task execution
```

**3. `journey_agent_template.yaml`**

```yaml
# journey_agent_template.yaml
role: Journey
name: "REPLACE_WITH_AGENT_NAME"  # e.g., WebResearcher, CodeGenerator
description: "REPLACE_WITH_AGENT_DESCRIPTION"
llm: "REPLACE_WITH_LLM"  # e.g., claude-3.5-sonnet, deepseek-coder, gemini-1.5-flash
tools:
  # List of tools (up to 5) - choose from the defined tool list
  - "REPLACE_WITH_TOOL_1" 
  - "REPLACE_WITH_TOOL_2"
  # - ...
playbook: "REPLACE_WITH_PLAYBOOK_FILE.yaml" # e.g., web_research_playbook.yaml
```

**4. `playbook_template.yaml`**

```yaml
# playbook_template.yaml
name: "REPLACE_WITH_PLAYBOOK_NAME"  # e.g., Web Research Playbook
description: "REPLACE_WITH_PLAYBOOK_DESCRIPTION"
steps:
  - step_id: 1
    description: "REPLACE_WITH_STEP_DESCRIPTION"
    action: "REPLACE_WITH_ACTION" # e.g., web_search, generate_code, call_api
    input: "REPLACE_WITH_INPUT_DESCRIPTION" # e.g., user_query, previous_step_output
    expected_output: "REPLACE_WITH_OUTPUT_DESCRIPTION" # Used by Inspector for QC
    error_handling:  # Optional: Define how to handle errors
      type: "retry"  # Options: retry, alternative_action, escalate (to Super)
      max_retries: 3 # if retry
      alternative_action: "REPLACE_WITH_ALTERNATIVE_ACTION" # If applicable
    # Add more steps as needed
```

**5. `pricing_data.yaml`**

```yaml
# pricing_data.yaml
llm_pricing:
  claude-3.5-sonnet:
    input: 0.003  # USD per 1k tokens
    output: 0.015 # USD per 1k tokens
  gemini-1.5-flash:
    input: 0.001
    output: 0.002
  deepseek-coder:
    input: 0.0005
    output: 0.001
  # Add other LLMs as needed

gcp_pricing: # Simplified example - needs to be much more detailed in practice
  compute_engine:
    n1-standard-1: 0.0475  # USD per hour (example - varies by region and commitment)
  cloud_storage:
    standard: 0.020 # USD per GB per month (example)
  # Add other GCP services and pricing details

other_services:
  serpapi: # Example - if using a search API
    basic_plan: 50 # USD per month for X searches
  # Add other services as needed
```

**How These Files Interact**

1.  **Initialization:** When the framework starts, it loads `super_agent_config.yaml` and `inspector_agent_config.yaml` to create the Super and Inspector agents. It also loads `pricing_data.yaml`.

2.  **User Request:** The user submits a request to the Super agent.

3.  **Plan Generation:** The Super agent analyzes the request, determines the required `Journey` agents, and selects appropriate `journey_agent_*.yaml` files. For each required `Journey` agent, the Super:
    *   Loads the corresponding `journey_agent_template.yaml` file.
    *   Fills in the placeholders (e.g., `REPLACE_WITH_AGENT_NAME`, `REPLACE_WITH_LLM`, `REPLACE_WITH_TOOL_1`, `REPLACE_WITH_PLAYBOOK_FILE.yaml`).
    *   Creates an instance of the `Journey` agent with the specified configuration.
    *   Loads the specified `playbook_*.yaml` file for each `Journey` agent.

4.  **Task Execution:** The Super agent orchestrates the execution of the plan, assigning tasks to the `Journey` agents. Each `Journey` agent follows its assigned playbook.

5.  **Monitoring and Evaluation:** The Inspector agent monitors the progress of the `Journey` agents, evaluates their outputs based on the `expected_output` in the playbooks and the `acceptance_threshold` in its configuration, and reports to the Super agent.

6.  **Cost Tracking:** Throughout the process, all agents log their resource usage (LLM tokens, compute time, etc.). The cost calculation module uses this data and the `pricing_data.yaml` file to track costs.

**Example: Creating a `Journey` Agent**

Let's say the Super agent determines that a "WebResearcher" agent is needed. It would:

1.  Load `journey_agent_template.yaml`.
2.  Create a new file (or in-memory representation) like this:

    ```yaml
    # journey_agent_web_researcher.yaml (Generated by Super)
    role: Journey
    name: WebResearcher
    description: An agent specialized in web research.
    llm: "claude-3.5-sonnet" # Or gemini, depending on the task
    tools:
      - web_search
      - rag
    playbook: "web_research_playbook.yaml"
    ```

3.  Load `web_research_playbook.yaml`:

    ```yaml
    # web_research_playbook.yaml
    name: Web Research Playbook
    description: A playbook for conducting web research.
    steps:
      - step_id: 1
        description: "Perform a web search based on the user query."
        action: "web_search"
        input: "user_query"
        expected_output: "A list of relevant search results."
        error_handling:
          type: "retry"
          max_retries: 3
      - step_id: 2
        description: "Extract information from the top search results using RAG."
        action: "rag"
        input: "top_search_results"
        expected_output: "A concise summary of the relevant information."
        error_handling:
          type: "escalate" # If RAG fails, escalate to Super
    ```

4.  Instantiate the `WebResearcher` agent with this configuration.

This structured approach using YAML configuration files allows for:

*   **Flexibility:** Easily create and modify agent configurations.
*   **Reusability:**  Define reusable `Journey` agent templates and playbooks.
*   **Modularity:**  Swap out LLMs, tools, or playbooks without changing the core framework code.
*   **Readability:** YAML is a human-readable format, making it easy to understand and manage agent configurations.
*   **Maintainability:** Changes to pricing or agent configurations can be made in the YAML files without requiring code changes.

This comprehensive set of YAML templates and the explanation of their interaction provides a solid foundation for building and managing your agentic framework. You can extend this by adding more specific fields to the YAML files as needed (e.g., timeouts, specific API keys for tools, more detailed error handling logic).
