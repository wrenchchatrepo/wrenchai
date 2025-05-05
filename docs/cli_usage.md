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

Specify a log file:

```bash
wai run <playbook_id> --log-file /path/to/log.txt
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

## Completed Implementation Tasks

The following tasks have been completed for the CLI:

### 1. MCP Server Lifecycle Management

- **Status**: Functionality to start/stop MCP servers on demand during playbook execution, proper cleanup, server health checks, and improved Context7 server integration are implemented.

### 2. Enhanced Error Handling

- **Status**: Robust error handling, descriptive error messages, retry mechanisms for transient failures, graceful degradation, and handling of user interruptions are implemented.

### 3. Advanced Progress Tracking

- **Status**: Accurate progress reporting based on playbook steps, ETA calculation, improved visual representation, and detailed logging of step completion are implemented.

### 4. Comprehensive Testing

- **Status**: Comprehensive unit tests and integration tests for all CLI components, error cases, and recovery are implemented.

## Production Readiness Checklist

Before the CLI can be considered production-ready, the following must be addressed:

1. **Authentication Support**: Add support for API key management and secure storage
2. **Telemetry & Logging**: Implement proper logging with configurable verbosity levels
3. **MCP Server Reliability**: Ensure reliable MCP server management in production environments
4. **Documentation Completion**: Finalize all documentation including troubleshooting guides
5. **Performance Optimization**: Review and optimize performance for large playbooks

## Contributing

Contributions to the CLI are welcome! See `CONTRIBUTING.md` in the `wai_cli` directory for guidelines.
