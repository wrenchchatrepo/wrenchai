#!/usr/bin/env python3
# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import sys
import asyncio
import logging
import argparse
from typing import Dict, Any, List, Optional

# Try importing colorama for cross-platform colored output
try:
    from colorama import init, Fore, Style
    init()  # Initialize colorama
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False

# Try importing the examples module
try:
    from wrenchai.examples import (
        list_examples, get_example, check_dependencies,
        HAS_SQL_GENERATOR, HAS_RAG, HAS_STREAMING, HAS_CHAT_APP, HAS_QUESTION_GRAPH
    )
    HAS_EXAMPLES = True
except ImportError:
    HAS_EXAMPLES = False

def color_text(text: str, color: str, bold: bool = False) -> str:
    """Apply color to text if colorama is available
    
    Args:
        text: Text to color
        color: Color name (red, green, yellow, blue, magenta, cyan)
        bold: Whether to make the text bold
        
    Returns:
        Colored text if colorama is available, original text otherwise
    """
    if not HAS_COLORAMA:
        return text
        
    color_map = {
        'red': Fore.RED,
        'green': Fore.GREEN,
        'yellow': Fore.YELLOW,
        'blue': Fore.BLUE,
        'magenta': Fore.MAGENTA,
        'cyan': Fore.CYAN,
        'white': Fore.WHITE
    }
    
    color_code = color_map.get(color.lower(), Fore.WHITE)
    bold_code = Style.BRIGHT if bold else ""
    
    return f"{color_code}{bold_code}{text}{Style.RESET_ALL}"

def print_available_examples():
    """Print a list of available examples"""
    if not HAS_EXAMPLES:
        print(color_text("Error: Failed to import examples module", "red", True))
        print("Make sure the wrenchai package is installed correctly.")
        return
        
    examples = list_examples()
    
    print(color_text("Available Pydantic AI Examples:", "blue", True))
    print()
    
    for key, example in examples.items():
        status = color_text("Available", "green") if example["available"] else color_text("Missing dependencies", "red")
        print(f"{color_text(example['name'], 'cyan', True)} [{status}]")
        print(f"  Description: {example['description']}")
        print(f"  Command: {color_text(f'python wrenchai_examples.py {key}', 'yellow')}")
        
        # Show missing dependencies
        deps = check_dependencies(key)
        missing_deps = [dep for dep, available in deps.items() if not available]
        if missing_deps:
            print(f"  Missing dependencies: {', '.join(missing_deps)}")
        
        print()

def setup_sql_generator_cli(subparsers):
    """Set up CLI for SQL generator example
    
    Args:
        subparsers: Subparsers object from argparse
    """
    if not HAS_SQL_GENERATOR:
        return
        
    parser = subparsers.add_parser(
        "sql-generator", 
        help="Generate SQL queries from natural language"
    )
    parser.add_argument("query", nargs="?", help="Natural language query")
    parser.add_argument("--host", default="localhost", help="Database host")
    parser.add_argument("--port", type=int, default=54320, help="Database port")
    parser.add_argument("--name", default="logs", help="Database name")
    parser.add_argument("--user", default="postgres", help="Database user")
    parser.add_argument("--password", default="postgres", help="Database password")
    parser.add_argument("--model", default="openai:gpt-4-turbo", help="Model to use")

def setup_rag_cli(subparsers):
    """Set up CLI for RAG example
    
    Args:
        subparsers: Subparsers object from argparse
    """
    if not HAS_RAG:
        return
        
    parser = subparsers.add_parser(
        "rag", 
        help="Retrieval-Augmented Generation for answering questions"
    )
    parser.add_argument(
        "action", 
        choices=["build", "search"],
        help="Action to perform (build database or search)"
    )
    parser.add_argument("query", nargs="?", help="Search query (for search action)")
    parser.add_argument("--docs-dir", default="docs", help="Documentation directory (for build action)")
    parser.add_argument("--host", default="localhost", help="Database host")
    parser.add_argument("--port", type=int, default=5432, help="Database port")
    parser.add_argument("--name", default="wrenchai", help="Database name")
    parser.add_argument("--user", default="postgres", help="Database user")
    parser.add_argument("--password", default="postgres", help="Database password")
    parser.add_argument("--model", default="openai:gpt-4-turbo", help="Model to use")

def setup_streaming_cli(subparsers):
    """Set up CLI for streaming examples
    
    Args:
        subparsers: Subparsers object from argparse
    """
    if not HAS_STREAMING:
        return
        
    parser = subparsers.add_parser(
        "streaming", 
        help="Examples of streaming text and structured data"
    )
    parser.add_argument(
        "type",
        choices=["markdown", "structured"],
        help="Type of streaming example"
    )
    parser.add_argument("prompt", nargs="?", help="Prompt for markdown streaming")
    parser.add_argument("--model", default="openai:gpt-4-turbo", help="Model to use")

def setup_chat_app_cli(subparsers):
    """Set up CLI for chat app example
    
    Args:
        subparsers: Subparsers object from argparse
    """
    if not HAS_CHAT_APP:
        return
        
    parser = subparsers.add_parser(
        "chat-app", 
        help="Web-based chat application"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    parser.add_argument("--model", default="openai:gpt-4-turbo", help="Model to use")
    parser.add_argument("--db-path", default="chat_messages.db", help="Path to the SQLite database file")

def setup_question_graph_cli(subparsers):
    """Set up CLI for question graph example
    
    Args:
        subparsers: Subparsers object from argparse
    """
    if not HAS_QUESTION_GRAPH:
        return
        
    parser = subparsers.add_parser(
        "question-graph", 
        help="Graph-based question generation and evaluation"
    )
    parser.add_argument("--topic", default="Python programming", help="Topic for questions")
    parser.add_argument("--max-attempts", type=int, default=3, help="Maximum number of attempts")

async def run_sql_generator(args):
    """Run SQL generator example
    
    Args:
        args: Command line arguments
    """
    from wrenchai.examples.sql_generator import run_example
    
    query = args.query or "Find all error logs from the last 7 days"
    
    db_config = {
        "db_host": args.host,
        "db_port": args.port,
        "db_name": args.name,
        "db_user": args.user,
        "db_password": args.password,
        "model": args.model
    }
    
    await run_example(query, db_config)

async def run_rag(args):
    """Run RAG example
    
    Args:
        args: Command line arguments
    """
    from wrenchai.examples.rag import RAGSystem, build_database, search_and_answer
    
    rag_system = RAGSystem(
        db_host=args.host,
        db_port=args.port,
        db_name=args.name,
        db_user=args.user,
        db_password=args.password,
        model=args.model
    )
    
    if args.action == "build":
        await build_database(args.docs_dir, rag_system)
    elif args.action == "search":
        if not args.query:
            print("Error: Search query is required for search action")
            return
        await search_and_answer(args.query, rag_system)

async def run_streaming(args):
    """Run streaming example
    
    Args:
        args: Command line arguments
    """
    from wrenchai.examples.streaming import MarkdownStreaming, StructuredDataStreaming
    
    if args.type == "markdown":
        example = MarkdownStreaming(args.model)
        prompt = args.prompt or "Explain how to use Python decorators with examples"
        await example.run(prompt)
    else:  # structured
        example = StructuredDataStreaming(args.model)
        await example.run()

def run_chat_app(args):
    """Run chat app example
    
    Args:
        args: Command line arguments
    """
    from wrenchai.examples.chat_app import ChatApp
    
    app = ChatApp(
        model=args.model,
        host=args.host,
        port=args.port,
        db_path=args.db_path
    )
    
    app.run()

async def run_question_graph(args):
    """Run question graph example
    
    Args:
        args: Command line arguments
    """
    from wrenchai.examples.question_graph import QuestionGraph
    
    graph = QuestionGraph(topic=args.topic, max_attempts=args.max_attempts)
    await graph.run()

async def main_async():
    """Async main function"""
    parser = argparse.ArgumentParser(
        description="Wrenchai Examples - Pydantic AI Integration Examples"
    )
    subparsers = parser.add_subparsers(dest="example", help="Example to run")
    
    # Set up subparsers for each example
    setup_sql_generator_cli(subparsers)
    setup_rag_cli(subparsers)
    setup_streaming_cli(subparsers)
    setup_chat_app_cli(subparsers)
    setup_question_graph_cli(subparsers)
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no example specified, show list of examples
    if not args.example:
        print_available_examples()
        return
    
    # Run the specified example
    if args.example == "sql-generator" and HAS_SQL_GENERATOR:
        await run_sql_generator(args)
    elif args.example == "rag" and HAS_RAG:
        await run_rag(args)
    elif args.example == "streaming" and HAS_STREAMING:
        await run_streaming(args)
    elif args.example == "chat-app" and HAS_CHAT_APP:
        run_chat_app(args)
    elif args.example == "question-graph" and HAS_QUESTION_GRAPH:
        await run_question_graph(args)
    else:
        print(color_text(f"Error: Example '{args.example}' is not available", "red", True))
        print("Make sure all required dependencies are installed.")
        print_available_examples()

def main():
    """Main entry point"""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nExamples runner interrupted by user")
    except Exception as e:
        print(color_text(f"Error running example: {e}", "red", True))

if __name__ == "__main__":
    main()