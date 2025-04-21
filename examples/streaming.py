# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import sys
import logging
import asyncio
from typing import Optional, List, Dict, Any, Union, TypedDict, Annotated
import argparse
from enum import Enum

# Check for Pydantic AI
try:
    from pydantic_ai import Agent
    HAS_PYDANTIC_AI = True
except ImportError:
    HAS_PYDANTIC_AI = False
    logging.warning("pydantic-ai is not installed. Streaming will not work.")

# Check for rich (required for terminal output)
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.live import Live
    from rich.table import Table
    from rich.panel import Panel
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    logging.warning("rich is not installed. Pretty output will not be available.")

# Define types for structured data example
class Whale(TypedDict):
    """Information about a whale species"""
    name: str
    length: float
    weight: Optional[float]
    ocean: Optional[str]
    description: Optional[str]

# Define streaming examples
class StreamingExample:
    """Base class for streaming examples"""
    
    def __init__(self, model: str = "openai:gpt-4-turbo"):
        """Initialize the streaming example
        
        Args:
            model: AI model to use
        """
        self.model = model
        self._check_requirements()
    
    def _check_requirements(self):
        """Check if all required dependencies are installed"""
        if not HAS_PYDANTIC_AI:
            logging.error("pydantic-ai is required for streaming examples")
            raise ImportError("pydantic-ai is required for streaming examples")
            
        if not HAS_RICH:
            logging.warning("rich is required for pretty terminal output")
    
    async def run(self, prompt: str):
        """Run the example (to be implemented by subclasses)
        
        Args:
            prompt: Prompt to use
        """
        raise NotImplementedError("Subclasses must implement run")

class MarkdownStreaming(StreamingExample):
    """Example that streams markdown content"""
    
    async def run(self, prompt: str):
        """Run the markdown streaming example
        
        Args:
            prompt: Prompt to use
        """
        if not HAS_RICH:
            print("Error: rich is required for markdown streaming")
            return
            
        # Create agent
        agent = Agent(
            self.model,
            instructions="""
            You are a helpful assistant that provides detailed, markdown-formatted responses.
            Use headings, lists, tables, and code blocks appropriately to structure your answers.
            Keep your responses concise but informative.
            """
        )
        
        # Begin streaming
        print(f"Streaming response for: {prompt}\n")
        
        # Initialize markdown content
        md_content = ""
        
        # Stream response with live rendering
        with Live(Markdown(md_content), refresh_per_second=10) as live:
            try:
                async for chunk in agent.run_stream(prompt):
                    md_content += chunk.delta
                    # Update the live display with the current markdown
                    live.update(Markdown(md_content))
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}")
        
        # Final rendered output
        console.print("\n[bold green]Final response:[/bold green]")
        console.print(Markdown(md_content))

class StructuredDataStreaming(StreamingExample):
    """Example that streams structured data (whale facts)"""
    
    async def run(self, prompt: str = None):
        """Run the structured data streaming example
        
        Args:
            prompt: Optional prompt (ignored - uses fixed prompt)
        """
        if not HAS_RICH:
            print("Error: rich is required for structured data streaming")
            return
            
        # Create agent with Whale output type
        agent = Agent[None, List[Whale]](
            self.model,
            output_type=List[Whale],
            instructions="""
            You are a marine biology expert that provides information about whale species.
            Generate a list of 5 interesting whale species with accurate facts.
            For each whale, provide its name, length (in meters), weight (in metric tons),
            the ocean where it's commonly found, and a brief description.
            """
        )
        
        # Create a table for displaying the data
        table = Table(title="Whale Species")
        table.add_column("Name", style="cyan")
        table.add_column("Length (m)", style="green", justify="right")
        table.add_column("Weight (t)", style="blue", justify="right")
        table.add_column("Ocean", style="magenta")
        table.add_column("Description", style="yellow", no_wrap=False)
        
        # Initialize whales data
        whales_data = []
        
        # Show starting message
        console.print("[bold]Generating information about whale species...[/bold]")
        
        # Stream structured data with live table updates
        with Live(table, refresh_per_second=4) as live:
            async for partial_whales in agent.run_stream():
                # Update the whales data with the latest information
                whales_data = partial_whales
                
                # Clear and rebuild the table
                table.rows = []
                for whale in whales_data:
                    # Get values with fallbacks for optional fields
                    name = whale.get("name", "Unknown")
                    length = str(whale.get("length", "?"))
                    weight = str(whale.get("weight", "?")) if whale.get("weight") is not None else "?"
                    ocean = whale.get("ocean", "Unknown") if whale.get("ocean") is not None else "Unknown"
                    description = whale.get("description", "") if whale.get("description") is not None else ""
                    
                    # Add row to table
                    table.add_row(name, length, weight, ocean, description)
        
        # Final table
        console.print("\n[bold green]Final whale species data:[/bold green]")
        console.print(table)

def main():
    """Main entry point"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Pydantic AI Streaming Examples")
    parser.add_argument("example", choices=["markdown", "structured"], help="Example to run")
    parser.add_argument("--model", default="openai:gpt-4-turbo", help="Model to use")
    parser.add_argument("prompt", nargs="?", help="Prompt for the example (optional)")
    
    args = parser.parse_args()
    
    # Create example
    if args.example == "markdown":
        example = MarkdownStreaming(args.model)
        prompt = args.prompt or "Explain how to use Python decorators with examples"
    else:  # structured
        example = StructuredDataStreaming(args.model)
        prompt = None  # Uses fixed prompt
    
    # Run example
    asyncio.run(example.run(prompt))

if __name__ == "__main__":
    main()