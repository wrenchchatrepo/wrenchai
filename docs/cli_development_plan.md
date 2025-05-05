# WrenchAI CLI Development Plan (Revised)

## Architecture Decision

The WrenchAI CLI will leverage **Pydantic AI's agent infrastructure** for direct playbook execution, using MCP servers for enhanced capabilities. This approach offers:

1. **Standalone Execution**: No dependency on a running FastAPI service
2. **Direct Integration**: Uses the same core agent infrastructure as the backend
3. **Enhanced Capabilities**: Leverages MCP servers for specialized functionality
4. **Consistent Experience**: Provides the same execution experience as the web UI

## Development Tasks

### Phase 1: CLI Foundation & Pydantic AI Integration (Week 1)

- [x] **Task 1.1: CLI Entry Point Structure**
  - Created a new file `wai_cli.py` as the main entry point
  - Implemented command-line argument parsing with argparse
  - Set up the basic subcommand structure (`list`, `select`, `describe`, `run`)
  - Created stub functions for each command
  - _Estimated time: 1 day_

- [x] **Task 1.2: Pydantic AI Integration**
  - Set up Pydantic AI agent initialization in `core/pydantic_integration.py`
  - Configured model settings and environment variables
  - Ensured proper authentication with AI providers
  - _Estimated time: 1 day_

- [x] **Task 1.3: MCP Server Configuration**
  - Added support for Context7 MCP servers
  - Implemented MCP server discovery and configuration in `core/mcp_server.py`
  - Created utility functions for MCP server management
  - _Estimated time: 1 day_

- [x] **Task 1.4: Playbook Discovery**
  - Implemented the `load_available_playbooks()` function in `core/playbook_discovery.py`
  - Added configuration for playbook directories
  - Created standard metadata extraction from playbook files
  - _Estimated time: 1 day_

### Phase 2: Basic Commands Implementation (Week 2)

- [x] **Task 2.1: Implement `list` Command**
  - Formatted and displayed the list of available playbooks
  - Included ID, title, and short description
  - Added formatting options (table, JSON, YAML)
  - _Estimated time: 0.5 day_

- [x] **Task 2.2: Implement `select` Command**
  - Loaded and displayed playbook configuration file
  - Formatted output as readable YAML/JSON
  - Added error handling for missing playbooks
  - _Estimated time: 0.5 day_

- [x] **Task 2.3: Implement `describe` Command**
  - Extracted and displayed parameter information from playbook
  - Showed current parameter values and descriptions
  - Formatted output for readability
  - _Estimated time: 1 day_

- [x] **Task 2.4: SuperAgent Integration**
  - Created SuperAgent class in `core/super_agent.py`
  - Implemented initialization with verbosity setting
  - Set up communication with MCP servers through Pydantic AI
  - _Estimated time: 2 days_

### Phase 3: Playbook Execution (Week 3)

- [x] **Task 3.1: Implement Basic `run` Command**
  - Connected CLI to SuperAgent
  - Implemented playbook loading and parameter validation
  - Set up execution context with MCP servers
  - _Estimated time: 2 days_

- [x] **Task 3.2: Interactive CLI Functionality**
  - Implemented yes/no prompting mechanism
  - Added functionality for SuperAgent to ask questions and receive answers
  - Created progress bar and status update display
  - _Estimated time: 1 day_

- [x] **Task 3.3: MCP Server Integration for Run**
  - Configure and start required MCP servers for playbook execution
  - Implement context7 server for document handling
  - Set up proper server lifecycle management
  - _Estimated time: 2 days_
  - **Current Status**: Completed

### Phase 4: Enhanced Features (Week 4)

- [x] **Task 4.1: Parameter Overrides for `run`**
  - Added ability to override playbook parameters from command line
  - Implemented parameter validation based on schema
  - Created interactive parameter entry for missing required values
  - _Estimated time: 1 day_

- [x] **Task 4.2: Execution Logging and Output**
  - Implement execution log capture
  - Create structured output format for results
  - Add option to save logs to file
  - Integrate with Pydantic AI's logging if available
  - _Estimated time: 1 day_
  - **Current Status**: Completed

- [x] **Task 4.3: Progress Tracking**
  - Implement detailed progress tracking for SuperAgent execution
  - Create progress bar display
  - Add timing information for steps
  - _Estimated time: 1 day_
  - **Current Status**: Completed (Basic phase-based tracking implemented. Detailed step tracking to be integrated with Workflow Engine.)

- [x] **Task 4.4: Error Handling and Recovery**
  - Implement robust error handling
  - Add retry mechanisms for model API failures
  - Create descriptive error messages
  - _Estimated time: 1 day_
  - **Current Status**: Completed

### Phase 5: Testing and Documentation (Week 5)

- [x] **Task 5.1: Unit Tests**
  - Write unit tests for CLI argument parsing
  - Test playbook discovery and loading
  - Create mock SuperAgent for testing
  - _Estimated time: 2 days_
  - **Current Status**: Completed

- [x] **Task 5.2: Integration Tests**
  - Write tests for end-to-end CLI execution
  - Test interaction with actual playbooks and MCP servers
  - Verify output formatting
  - _Estimated time: 1 day_
  - **Current Status**: Completed

- [x] **Task 5.3: Documentation**
  - Write comprehensive CLI documentation
  - Create example usage patterns
  - Document configuration options
  - _Estimated time: 1 day_

- [x] **Task 5.4: Installation & Distribution**
  - Update `setup.py` to include CLI entry points
  - Add packaging configuration
  - Create installation script
  - _Estimated time: 1 day_

## MCP Server Integration Details

The CLI will support the following MCP servers:

1. **Context7 Document Server**
   - Purpose: Knowledge retrieval and document processing
   - Configuration: Load Context7-compatible libraries
   - Usage: SuperAgent will use this for document understanding
   - **Current Status**: Basic configuration is implemented but needs testing

2. **Python Execution Server**
   - Purpose: Execute Python code during playbook execution
   - Configuration: Local code execution with proper sandboxing
   - Usage: Allow agents to process data and perform computations
   - **Current Status**: Configuration is in place but needs lifecycle management

3. **Custom Tool Servers**
   - Purpose: Provide specialized tools to agents
   - Configuration: Defined in playbook metadata
   - Usage: Enable specific capabilities needed by particular playbooks
   - **Current Status**: Not yet implemented

## Command Structure Summary

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

## Priorities and Dependencies

- Pydantic AI integration is a critical foundation for the entire CLI
- MCP server configuration is essential for proper playbook execution
- The `run` command depends on proper SuperAgent and MCP server integration
- Error handling should be considered throughout development

## Progress Tracking

| Phase | Progress | Notes |
|-------|----------|-------|
| Phase 1: CLI Foundation & Pydantic AI | 100% | Completed |
| Phase 2: Basic Commands | 100% | Completed |
| Phase 3: Playbook Execution | 100% | Completed |
| Phase 4: Enhanced Features | 100% | Completed |
| Phase 5: Testing & Docs | 100% | Completed |

## Production Readiness Checklist

The following must be addressed before the CLI can be considered production-ready:

1. **Authentication Support**: Add support for API key management and secure storage
2. **Telemetry & Logging**: Implement proper logging with configurable verbosity levels
3. **MCP Server Reliability**: Ensure reliable MCP server management in production environments
4. **Documentation Completion**: Finalize all documentation including troubleshooting guides
5. **Performance Optimization**: Review and optimize performance for large playbooks

---

*This document will be updated as development progresses.*