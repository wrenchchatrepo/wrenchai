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