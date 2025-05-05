#!/usr/bin/env python3
# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import sys
import asyncio
import logging
import argparse
import yaml
from typing import Optional, List, Dict, Any

# Check if Pydantic AI is available
try:
    import pydantic_ai
    PYDANTIC_AI_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_AVAILABLE = False

class WrenchAICliApp:
    """Main WrenchAI CLI application"""
    
    def __init__(self):
        """Initialize the CLI application"""
        self.logger = self._setup_logger()
        self.parser = self._setup_argument_parser()
        
    def _setup_logger(self) -> logging.Logger:
        """Set up logging for the CLI"""
        logger = logging.getLogger("wrenchai-cli")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
    
    def _setup_argument_parser(self) -> argparse.ArgumentParser:
        """Set up command-line argument parsing"""
        parser = argparse.ArgumentParser(
            description="WrenchAI CLI for discovering and executing playbooks",
            prog="wai"
        )
        
        # Add global options
        parser.add_argument(
            "--verbose", 
            action="store_true", 
            help="Enable verbose output"
        )
        
        # Create subparsers for different commands
        subparsers = parser.add_subparsers(dest="command", help="Command to execute")
        
        # 'list' command
        list_parser = subparsers.add_parser(
            "list", 
            help="List all available playbooks"
        )
        list_parser.add_argument(
            "--format",
            choices=["table", "json", "yaml"],
            default="table",
            help="Output format (default: table)"
        )
        
        # 'select' command
        select_parser = subparsers.add_parser(
            "select", 
            help="Select and output a playbook config file"
        )
        select_parser.add_argument(
            "id", 
            help="Playbook ID to select"
        )
        select_parser.add_argument(
            "--format",
            choices=["yaml", "json"],
            default="yaml",
            help="Output format (default: yaml)"
        )
        
        # 'describe' command
        describe_parser = subparsers.add_parser(
            "describe", 
            help="Describe parameters for a playbook"
        )
        describe_parser.add_argument(
            "id", 
            help="Playbook ID to describe"
        )
        describe_parser.add_argument(
            "--format",
            choices=["table", "json", "yaml"],
            default="table",
            help="Output format (default: table)"
        )
        
        # 'run' command
        run_parser = subparsers.add_parser(
            "run", 
            help="Execute a playbook"
        )
        run_parser.add_argument(
            "id", 
            help="Playbook ID to run"
        )
        run_parser.add_argument(
            "--param", 
            action="append", 
            dest="params",
            help="Override playbook parameters in the format name=value"
        )
        run_parser.add_argument(
            "--model",
            help="LLM model to use"
        )
        run_parser.add_argument(
            "--mcp-config",
            help="Path to MCP server configuration"
        )
        run_parser.add_argument(
            "--log-file",
            help="Path to a file to save execution logs"
        )
        
        return parser
    
    def _check_pydantic_ai(self) -> bool:
        """Check if Pydantic AI is available"""
        if not PYDANTIC_AI_AVAILABLE:
            self.logger.error(
                "Pydantic AI is required but not installed. "
                "Please install it with 'pip install pydantic-ai'"
            )
            return False
        return True
    
    def _load_available_playbooks(self) -> List[Dict[str, Any]]:
        """Load available playbooks"""
        # Import here to avoid circular imports
        from core.playbook_discovery import get_playbook_manager
        
        # Get the playbook manager and return the playbook summary
        manager = get_playbook_manager()
        return manager.get_playbook_summary()
    
    def cmd_list(self, args: argparse.Namespace) -> int:
        """List all available playbooks"""
        playbooks = self._load_available_playbooks()
        
        if not playbooks:
            self.logger.info("No playbooks found")
            return 0
            
        # Output according to format
        if args.format == "json":
            import json
            print(json.dumps(playbooks, indent=2))
        elif args.format == "yaml":
            import yaml
            print(yaml.dump(playbooks, sort_keys=False))
        else:  # table format
            print("\nAvailable Playbooks:\n")
            print(f"{'ID':<15} {'Title':<30} {'Description':<50}")
            print("-" * 95)
            
            for playbook in playbooks:
                print(
                    f"{playbook['id']:<15} {playbook['title']:<30} {playbook['description']:<50}"
                )
            
            print("\nUse 'wai describe <id>' to see details for a specific playbook")
            
        return 0
    
    def cmd_select(self, args: argparse.Namespace) -> int:
        """Select and output a playbook configuration"""
        playbook_id = args.id
        self.logger.info(f"Selecting playbook with ID: {playbook_id}")
        
        # Import here to avoid circular imports
        from core.playbook_discovery import get_playbook_manager
        
        # Get the playbook manager and retrieve the playbook
        manager = get_playbook_manager()
        playbook = manager.get_playbook(playbook_id)
        
        if not playbook:
            self.logger.error(f"Playbook not found: {playbook_id}")
            return 1
            
        # Remove source_path from output (internal detail)
        if "source_path" in playbook:
            del playbook["source_path"]
            
        # Output according to format
        if args.format == "json":
            import json
            print(json.dumps(playbook, indent=2))
        else:  # yaml format
            import yaml
            print(yaml.dump(playbook, sort_keys=False))
            
        return 0
    
    def cmd_describe(self, args: argparse.Namespace) -> int:
        """Describe parameters for a playbook"""
        playbook_id = args.id
        self.logger.info(f"Describing playbook with ID: {playbook_id}")
        
        # Import here to avoid circular imports
        from core.playbook_discovery import get_playbook_manager
        
        # Get the playbook manager
        manager = get_playbook_manager()
        playbook = manager.get_playbook(playbook_id)
        
        if not playbook:
            self.logger.error(f"Playbook not found: {playbook_id}")
            return 1
            
        # Get parameters for the playbook
        parameters = manager.get_playbook_parameters(playbook_id)
        
        if not parameters:
            print(f"\nPlaybook '{playbook_id}' has no parameters.")
            return 0
            
        # Output according to format
        if args.format == "json":
            import json
            print(json.dumps(parameters, indent=2))
        elif args.format == "yaml":
            import yaml
            print(yaml.dump(parameters, sort_keys=False))
        else:  # table format
            print(f"\nParameters for playbook '{playbook_id}':\n")
            print(f"{'Name':<20} {'Type':<10} {'Required':<10} {'Default':<15} {'Description':<40}")
            print("-" * 95)
            
            for param in parameters:
                name = param.get("name", "")
                param_type = param.get("type", "string")
                required = "Yes" if param.get("required", False) else "No"
                default = str(param.get("default", "")) if "default" in param else ""
                description = param.get("description", "")
                
                print(
                    f"{name:<20} {param_type:<10} {required:<10} {default:<15} {description:<40}"
                )
                
        return 0
    
    async def _execute_run_command(self, args: argparse.Namespace) -> int:
        """Execute the run command asynchronously"""
        if not self._check_pydantic_ai():
            return 1
            
        playbook_id = args.id
        params = {} if not args.params else dict(
            param.split('=', 1) for param in args.params
        )
        
        self.logger.info(f"Running playbook with ID: {playbook_id}")
        if params:
            self.logger.info(f"With parameters: {params}")
        
        # Import here to avoid circular imports
        from core.playbook_discovery import get_playbook_manager
        from core.super_agent import SuperAgent
        
        # Get the playbook manager and retrieve the playbook
        manager = get_playbook_manager()
        playbook = manager.get_playbook(playbook_id)
        
        if not playbook:
            self.logger.error(f"Playbook not found: {playbook_id}")
            return 1
            
        # Create the SuperAgent
        super_agent = SuperAgent(
            verbose=args.verbose,
            model=args.model,
            mcp_config_path=args.mcp_config
        )
        
        # Set up an interactive message callback
        async def message_callback(message: str) -> str:
            print(f"\n{message}")
            return input("Your answer: ")
        
        super_agent.set_message_callback(message_callback)
        
        # Set up a progress callback
        def progress_callback(percentage: float, message: str) -> None:
            # Create a simple progress bar
            bar_width = 40
            filled_width = int(bar_width * percentage / 100)
            bar = "#" * filled_width + "-" * (bar_width - filled_width)
            print(f"\r[{bar}] {percentage:.1f}% {message}", end="", flush=True)
        
        super_agent.set_progress_callback(progress_callback)
        
        try:
            # Execute the playbook
            result = await super_agent.execute_playbook(playbook, params)
            
            if not result.get("success", False):
                self.logger.error(f"Playbook execution failed: {result.get('error', 'Unknown error')}")
                return 1
                
            # Display completion message and result
            print("\n\nPlaybook execution completed successfully!")
            final_result = result.get('result')
            if final_result is not None:
                print("\n--- Playbook Result ---")
                if isinstance(final_result, (dict, list)):
                    try:
                        import json
                        print(json.dumps(final_result, indent=2))
                    except ImportError:
                        print(final_result)
                else:
                    print(final_result)
                print("-----------------------")

            # Inform user about log file if saved
            if args.log_file:
                self.logger.info(f"Full execution log saved to: {args.log_file}")

            return 0
            
        except Exception as e:
            self.logger.error(f"Error executing playbook: {e}")
            return 1
    
    def cmd_run(self, args: argparse.Namespace) -> int:
        """Execute a playbook"""
        # Run the async function in the event loop
        return asyncio.run(self._execute_run_command(args))
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """Run the CLI application with the provided arguments"""
        args = self.parser.parse_args(args)
        
        # Set log level based on verbosity
        log_level = logging.INFO
        if args.verbose:
            log_level = logging.DEBUG
            self.logger.debug("Verbose mode enabled") # Log this using the instance logger

        # Set the level for the CLI logger and root logger (to capture logs from other modules like super_agent)
        self.logger.setLevel(log_level)
        logging.root.setLevel(log_level)

        # Configure file logging if --log-file is provided for the run command
        if args.command == "run" and args.log_file:
            try:
                file_handler = logging.FileHandler(args.log_file)
                formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
                file_handler.setFormatter(formatter)
                logging.root.addHandler(file_handler)
                self.logger.info(f"Logging execution details to {args.log_file}")
            except Exception as e:
                self.logger.error(f"Could not set up log file {args.log_file}: {e}")

        # Execute the appropriate command
        if args.command == "list":
            return self.cmd_list(args)
        elif args.command == "select":
            return self.cmd_select(args)
        elif args.command == "describe":
            return self.cmd_describe(args)
        elif args.command == "run":
            return self.cmd_run(args)
        else:
            self.parser.print_help()
            return 0

def main():
    """Main entry point for the CLI"""
    app = WrenchAICliApp()
    sys.exit(app.run())

if __name__ == "__main__":
    main()