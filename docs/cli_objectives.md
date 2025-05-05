# WrenchAI CLI Objectives

## Purpose

Create a command-line interface (`wai` or `wrenchai`) that enables users to discover and execute WrenchAI playbooks through the SuperAgent, focusing on delivering valuable outcomes rather than exposing implementation details.

## Core Design Principles

1. **SuperAgent-Centered**: All playbook execution happens through the SuperAgent, providing a single point of interaction for users.

2. **Outcome-Focused**: The CLI emphasizes work products rather than implementation details (agents, tools, etc.).

3. **Progressive Discovery**: Users can explore available playbooks and understand their capabilities before execution.

4. **Minimal Configuration**: Most parameters are pre-configured, with the option to override when needed.

5. **Interactive When Necessary**: The SuperAgent can ask for additional information during execution but minimizes interruptions.

## Command Structure

```
CLI Command: wrenchai or wai

DISCOVERY COMMANDS:
wai list                   # List all available playbooks (id, title, & description)
wai select <id>            # Select and output a read-only playbook config file
wai describe <id>          # Verbose description of all parameters and current values

EXECUTION COMMAND:
wai run <id>               # Execute the selected playbook via the SuperAgent
    verbose (y/n)          # Prompt for verbose updates (every step + progress bar)
                           # vs. minimal updates (progress bar + SuperAgent interactions only)
```

## Technical Approach

1. **Pydantic AI Integration**: Directly leverage Pydantic AI's agent infrastructure for playbook execution, enabling standalone operation without requiring a running FastAPI service.

2. **MCP Server Integration**: Use Model Context Protocol servers (including Context7) to provide enhanced capabilities to the SuperAgent during execution.

3. **Progressive Enhancement**: Start with a minimal viable CLI and enhance with additional features as development progresses.

4. **Consistent Experience**: Ensure the CLI provides the same quality of results as the web UI.

## Implementation Focus

- Integrate with existing SuperAgent implementation
- Configure and manage MCP servers for document handling and specialized tools
- Provide robust error handling and recovery mechanisms
- Support interactive communication between SuperAgent and user
- Track and display execution progress

## Success Criteria

The CLI will be considered successful when users can:

1. Easily discover available playbooks
2. Execute complex playbooks with minimal configuration
3. Receive high-quality results comparable to the web UI
4. Interact with the SuperAgent when necessary to provide additional information
5. Track execution progress and understand what's happening

This focused CLI will empower users to leverage WrenchAI's powerful playbook execution capabilities directly from the command line, complementing the web UI and providing flexibility in how users interact with the system.