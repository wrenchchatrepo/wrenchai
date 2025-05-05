# Gen 2 Features

**Generation 2 Features (Post-MVP):**

These features are planned for development *after* the initial Minimum Viable Product (MVP) is complete and functional. The MVP will focus on the core agentic framework, Bayesian reasoning, basic tool integration, and the Streamlit UI.

1.  **Visual Workflow Editor (React-based):**

    *   **Description:** Replace the YAML-based playbook definition with a visual workflow editor, inspired by Praison.ai's canvas. This will allow users to create and manage agent workflows using a drag-and-drop interface.
    *   **Implementation Considerations:**
        *   **React Component Library:** Choose a suitable React component library for building the visual editor. Good candidates include:
            *   `react-flow`: A highly customizable library specifically designed for building node-based editors. [https://reactflow.dev/](https://reactflow.dev/)
            *   `rete.js`: Another powerful library for visual programming. [https://rete.js.org/#/](https://rete.js.org/#/)
            *   `nodered-react`: A React wrapper around Node-RED's visual editor. [https://flows.nodered.org/node/node-red-react](https://flows.nodered.org/node/node-red-react) (Node-RED itself might be too heavyweight, but this component could be useful).
        *   **Node Types:** Define the different types of nodes that will be available in the editor (e.g., LLM call, web search, code execution, data transformation, conditional logic). Each node type will correspond to a specific tool or operation.
        *   **Connection Logic:** Implement the logic for connecting nodes and defining the flow of data between them.
        *   **Serialization/Deserialization:** Develop a mechanism to serialize the visual workflow (created in the editor) into a format that can be executed by the framework (e.g., JSON or a custom format). This format will replace the YAML playbooks.  You'll also need to deserialize the format back into the visual representation for editing.
        *   **Integration with Backend:** Connect the visual editor to the backend (your core framework) to allow users to save, load, and execute workflows.
        *   **Version Control:** Consider how to integrate version control with the visual workflow editor.

2.  **Expanded Tool Catalog:**

    *   **Description:** Add more pre-built tools to the framework, inspired by Praison.ai's tool catalog and user needs.
    *   **Implementation Considerations:**
        *   **Prioritization:** Prioritize tools based on user demand and the overall goals of the framework.
        *   **API Integrations:** Implement robust API integrations for each new tool, handling authentication, error handling, and rate limiting.
        *   **Tool Abstraction:** Maintain a consistent interface for all tools, making it easier to add new tools in the future.
        *   **Documentation:** Provide clear documentation for each new tool, including its purpose, inputs, outputs, and configuration options.
        * **Community Contributions:** Consider a mechanism for allowing community contributions of new tools (with appropriate security and quality control).

3.  **Advanced Data Connection Management:**

    *   **Description:** Implement a more robust and user-friendly system for managing data connections, drawing inspiration from Praison.ai's approach.
    *   **Implementation Considerations:**
        *   **Connection Types:** Support various connection types (databases, cloud storage, APIs, etc.).
        *   **Credential Management:** Securely store and manage credentials for data connections.  Consider using a secrets management service (e.g., GCP Secret Manager, HashiCorp Vault).
        *   **UI for Connection Configuration:** Provide a user-friendly interface for configuring and testing data connections.
        *   **Connection Pooling:** Implement connection pooling to improve performance and efficiency.
        *   **Error Handling:** Handle connection errors gracefully and provide informative error messages.

4.  **Multiple Trigger Mechanisms:**

    *   **Description:** Add support for different trigger types beyond manual execution from the UI.
    *   **Implementation Considerations:**
        *   **Schedule Triggers:** Allow users to schedule agent execution at specific times or intervals (e.g., using a cron-like syntax).
        *   **Webhook Triggers:** Allow agents to be triggered by external events via webhooks. This enables integration with other systems.
        *   **Data Change Triggers:** Allow agents to be triggered when data in a connected data source changes (e.g., a new row is added to a database table).
        *   **Trigger Management UI:** Provide a UI for creating, managing, and monitoring triggers.
        *   **Scalability:** Design the trigger system to handle a large number of triggers and events.

5.  **Enhanced Agent Communication:**

    *   **Description:** Refine and expand the mechanisms for agent-to-agent communication, drawing inspiration from Praison.ai and other multi-agent frameworks.
    *   **Implementation Considerations:**
        *   **Communication Protocols:** Choose appropriate communication protocols (e.g., HTTP, gRPC, message queues) based on performance and scalability requirements.
        *   **Message Formats:** Define standardized message formats for inter-agent communication.
        *   **Discovery Service (Optional):** Consider implementing a discovery service to allow agents to find and communicate with each other dynamically.
        *   **Error Handling:** Handle communication errors gracefully and provide mechanisms for retries and failover.
        *   **Security:** Secure agent communication channels to prevent unauthorized access or modification of messages.

**Documenting Gen 2 Features:**

You should document these Gen 2 features in your project's `README.md` and/or in a separate `ROADMAP.md` file.  This provides a clear roadmap for future development and helps manage expectations.

**Example (in `README.md`):**

```markdown
## Roadmap

### Generation 1 (MVP)

*   Core agentic framework (Super, Inspector, Journey agents)
*   Bayesian reasoning for decision-making and evaluation
*   Basic tool integration (web search, code execution)
*   Streamlit UI for basic interaction
*   YAML-based configuration for agents and playbooks
*   Cost tracking
*  Dockerization
* Github integration

### Generation 2 (Post-MVP)

*   **Visual Workflow Editor (React-based):** Replace YAML playbooks with a drag-and-drop interface.
*   **Expanded Tool Catalog:** Add more pre-built tools.
*   **Advanced Data Connection Management:** Improve the system for managing data connections.
*   **Multiple Trigger Mechanisms:** Support schedule, webhook, and data change triggers.
*   **Enhanced Agent Communication:** Refine inter-agent communication.
```

