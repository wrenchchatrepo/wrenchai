#!/usr/bin/env python3
# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import sys
import logging
import argparse
import subprocess
from typing import Optional, List, Dict, Any

# Check if Pydantic AI CLI is available
try:
    import pydantic_ai.cli
    CLI_AVAILABLE = True
except ImportError:
    CLI_AVAILABLE = False
    
def setup_environment():
    """Set up environment variables for the CLI"""
    # Check for API keys in environment
    api_keys = {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY"),
        "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY")
    }
    
    # Log which keys are available (but don't log the actual keys)
    for key_name, key_value in api_keys.items():
        if key_value:
            logging.info(f"{key_name} is set")
        else:
            logging.warning(f"{key_name} is not set")
    
    # Set Logfire configuration if available
    if "LOGFIRE_API_KEY" in os.environ:
        os.environ["PYDANTIC_AI_LOGFIRE"] = "true"
        logging.info("Logfire integration enabled")

def run_cli(args: Optional[List[str]] = None) -> int:
    """Run the Pydantic AI CLI with Wrenchai configuration
    
    Args:
        args: Command line arguments (defaults to sys.argv[1:])
        
    Returns:
        Exit code
    """
    if not CLI_AVAILABLE:
        logging.error("Pydantic AI CLI is not available. Install with 'pip install pydantic-ai[cli]'")
        return 1
    
    # Set up environment variables
    setup_environment()
    
    # Parse arguments for our wrapper
    parser = argparse.ArgumentParser(description="Wrenchai CLI powered by Pydantic AI")
    parser.add_argument("--model", default="anthropic:claude-3-5-sonnet-20240229",
                      help="Model to use (default: anthropic:claude-3-5-sonnet-20240229)")
    parser.add_argument("--markdown", action="store_true",
                      help="Display responses in markdown format")
    parser.add_argument("--multiline", action="store_true",
                      help="Start in multiline input mode")
    parser.add_argument("--timeout", type=int, default=60,
                      help="Request timeout in seconds")
    parser.add_argument("--debug", action="store_true",
                      help="Enable debug logging")
    parser.add_argument("prompt", nargs="?", help="Initial prompt (optional)")
    
    # Parse our arguments
    if args is None:
        args = sys.argv[1:]
    
    # Handle special case where args is empty or just help
    if not args or args[0] in ["-h", "--help"]:
        parsed_args = parser.parse_args(args)
    else:
        # Check if the first arg is a flag
        if args[0].startswith('-'):
            parsed_args = parser.parse_args(args)
        else:
            # If the first arg is a prompt, handle accordingly
            prompt_start = 0
            while prompt_start < len(args) and args[prompt_start].startswith('-'):
                prompt_start += 2  # Skip the flag and its value
            
            # Parse flags
            if prompt_start > 0:
                flag_args = args[:prompt_start]
                parsed_args = parser.parse_args(flag_args)
                parsed_args.prompt = " ".join(args[prompt_start:])
            else:
                parsed_args = parser.parse_args([])
                parsed_args.prompt = " ".join(args)
    
    # Set up logging
    if parsed_args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # Prepare Pydantic AI CLI arguments
    pai_args = ["pai"]
    
    # Add model
    pai_args.extend(["--model", parsed_args.model])
    
    # Add timeout
    pai_args.extend(["--timeout", str(parsed_args.timeout)])
    
    # Add markdown flag if requested
    if parsed_args.markdown:
        pai_args.append("--markdown")
        
    # Add multiline flag if requested
    if parsed_args.multiline:
        pai_args.append("--multiline")
        
    # Add prompt if provided
    if parsed_args.prompt:
        pai_args.append(parsed_args.prompt)
    
    # Execute the Pydantic AI CLI
    logging.debug(f"Running Pydantic AI CLI with args: {pai_args}")
    
    try:
        # Execute the pai command
        if "uvx" in sys.modules:
            # Use uvx if available for better CLI experience
            from uvx import run
            run(["--from", "pydantic-ai"] + pai_args)
            return 0
        else:
            # Fall back to normal execution
            result = subprocess.run(pai_args)
            return result.returncode
    except Exception as e:
        logging.error(f"Error running Pydantic AI CLI: {e}")
        return 1

def create_config(model: str, 
               output_dir: str = "~/.config/pydantic-ai", 
               overwrite: bool = False) -> bool:
    """Create a Pydantic AI CLI configuration file
    
    Args:
        model: Default model to use
        output_dir: Output directory for the configuration file
        overwrite: Whether to overwrite an existing configuration
        
    Returns:
        True if successful, False otherwise
    """
    if not CLI_AVAILABLE:
        logging.error("Pydantic AI CLI is not available. Install with 'pip install pydantic-ai[cli]'")
        return False
    
    # Expand user directory
    output_dir = os.path.expanduser(output_dir)
    config_path = os.path.join(output_dir, "config.json")
    
    # Check if the configuration file already exists
    if os.path.exists(config_path) and not overwrite:
        logging.warning(f"Configuration file already exists at {config_path}")
        return False
    
    # Create the directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create the configuration JSON
    import json
    config = {
        "default_model": model,
        "display_markdown": True,
        "timeout": 60
    }
    
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        
        logging.info(f"Created Pydantic AI CLI configuration at {config_path}")
        return True
    except Exception as e:
        logging.error(f"Error creating configuration file: {e}")
        return False

def main():
    """Main entry point for the CLI"""
    exitcode = run_cli()
    sys.exit(exitcode)

if __name__ == "__main__":
    main()