# WrenchAI CLI

This is the command-line interface for WrenchAI, enabling users to discover and execute WrenchAI playbooks through the SuperAgent.

## Installation

```bash
# Clone the repository
git clone https://github.com/wrench-ai/wrenchai.git
cd wrenchai

# Install the CLI
./install_wai_cli.sh
```

## Usage

### List Available Playbooks

```bash
wai list
```

Optionally, you can specify the output format:

```bash
wai list --format json
wai list --format yaml
```

### Display Playbook Configuration

```bash
wai select <playbook_id>
```

Optionally, you can specify the output format:

```bash
wai select <playbook_id> --format json
```

### Display Playbook Parameters

```bash
wai describe <playbook_id>
```

Optionally, you can specify the output format:

```bash
wai describe <playbook_id> --format json
wai describe <playbook_id> --format yaml
```

### Execute a Playbook

```bash
wai run <playbook_id>
```

With parameter overrides:

```bash
wai run <playbook_id> --param name=value --param another=value
```

Specify a different LLM model:

```bash
wai run <playbook_id> --model "anthropic:claude-3.5-sonnet-20240229"
```

Enable verbose output:

```bash
wai run <playbook_id> --verbose
```

## Development

### Running Tests

```bash
python -m unittest discover tests
```

### Project Structure

- `wai_cli.py`: Main CLI entry point
- `core/pydantic_integration.py`: Integration with Pydantic AI
- `core/mcp_server.py`: MCP server configuration
- `core/playbook_discovery.py`: Playbook discovery and loading
- `core/super_agent.py`: SuperAgent implementation for executing playbooks

## Configuration

### Playbooks

Playbooks are stored in `core/configs/playbooks/` and can also be placed in `~/.wrenchai/playbooks/`.

### MCP Servers

MCP server configuration is stored in `mcp_config.json`.

## Remaining Implementation Tasks

The following tasks still need to be completed for the CLI to be fully functional:

### 1. MCP Server Lifecycle Management

- **Current Status**: Basic MCP server configuration is in place, but lifecycle management needs improvement
- **Required Changes**:
  - Add functionality to start/stop MCP servers on demand during playbook execution
  - Implement proper cleanup of server processes when execution completes or encounters errors
  - Add support for checking server health before execution
  - Improve Context7 server integration for document handling

### 2. Enhanced Error Handling

- **Current Status**: Basic error handling is implemented but needs to be more robust
- **Required Changes**:
  - Add more descriptive error messages for common failure scenarios
  - Implement retry mechanisms for transient failures (API rate limits, network issues)
  - Add graceful degradation when specific MCP servers are unavailable
  - Implement proper handling of user interruptions (Ctrl+C)

### 3. Advanced Progress Tracking

- **Current Status**: Simple progress tracking is in place
- **Required Changes**:
  - Implement more accurate progress reporting based on actual playbook steps
  - Add ETA calculation for long-running executions
  - Improve visual representation of progress (more detailed progress bar)
  - Add detailed logging of step completion with timing information

### 4. Comprehensive Testing

- **Current Status**: Basic unit tests are implemented
- **Required Changes**:
  - Add more comprehensive unit tests for all CLI components
  - Implement integration tests with actual playbooks
  - Add tests for error cases and recovery
  - Implement mocks for LLM APIs to enable reproducible testing

## Production Readiness Checklist

Before the CLI can be considered production-ready, the following must be addressed:

1. **Authentication Support**: Add support for API key management and secure storage
2. **Telemetry & Logging**: Implement proper logging with configurable verbosity levels
3. **MCP Server Reliability**: Ensure reliable MCP server management in production environments
4. **Documentation Completion**: Finalize all documentation including troubleshooting guides
5. **Performance Optimization**: Review and optimize performance for large playbooks

## Contributing

Contributions to the CLI are welcome! Please follow the guidelines in the main README.md file for contributing to the project.