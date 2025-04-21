# Wrench AI CLI

The Wrench AI CLI provides a convenient command-line interface powered by Pydantic AI for interacting with AI models.

## Installation

To install the CLI, you can use the included installation script:

```bash
# Make the script executable
chmod +x install_cli.sh

# Run the installation script
./install_cli.sh
```

This will install the Pydantic AI CLI, create a symbolic link for the `wrenchai` command, and set up autocompletion if desired.

## Usage

Once installed, you can use the CLI with:

```bash
wrenchai "Your question or prompt here"
```

### Options

- `--model`: Specify the model to use (default: `anthropic:claude-3-5-sonnet-20240229`)
  ```bash
  wrenchai --model openai:gpt-4 "What's the capital of France?"
  ```

- `--markdown`: Display responses in markdown format
  ```bash
  wrenchai --markdown "Create a table of planet sizes"
  ```

- `--multiline`: Start in multiline input mode (useful for longer prompts)
  ```bash
  wrenchai --multiline
  ```

- `--timeout`: Set the request timeout in seconds (default: 60)
  ```bash
  wrenchai --timeout 120 "Complex question requiring more time"
  ```

- `--debug`: Enable debug logging
  ```bash
  wrenchai --debug "What's the weather like?"
  ```

### Interactive Commands

In interactive mode, you can use special commands:

- `/exit`: End the session
- `/markdown`: Toggle markdown display mode
- `/multiline`: Toggle multiline input mode

## Environment Variables

The CLI uses the following environment variables for API keys:

- `OPENAI_API_KEY`: For OpenAI models
- `ANTHROPIC_API_KEY`: For Anthropic models
- `GOOGLE_API_KEY`: For Google models
- `LOGFIRE_API_KEY`: For Logfire integration

You can set these in your shell profile or before running the command:

```bash
export ANTHROPIC_API_KEY=your_key_here
wrenchai "Hello"
```

## Configuration

The CLI creates a configuration file at `~/.config/pydantic-ai/config.json` with default settings. You can edit this file to change the default model, markdown display, and timeout settings.

## Direct Pydantic AI CLI Access

If you prefer to use the Pydantic AI CLI directly, you can use the `pai` command:

```bash
pai --model openai:gpt-4 "What's the capital of France?"
```

This provides the same functionality but without the Wrench AI-specific defaults and enhancements.