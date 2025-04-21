# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import logging
from typing import Dict, Callable, Any

# Try to import all examples
try:
    from wrenchai.examples.sql_generator import SQLGenerator, run_example as run_sql_example
    HAS_SQL_GENERATOR = True
except ImportError:
    HAS_SQL_GENERATOR = False
    logging.warning("SQL Generator example is not available")

try:
    from wrenchai.examples.rag import RAGSystem, build_database, search_and_answer
    HAS_RAG = True
except ImportError:
    HAS_RAG = False
    logging.warning("RAG example is not available")

try:
    from wrenchai.examples.streaming import MarkdownStreaming, StructuredDataStreaming
    HAS_STREAMING = True
except ImportError:
    HAS_STREAMING = False
    logging.warning("Streaming examples are not available")

try:
    from wrenchai.examples.chat_app import ChatApp
    HAS_CHAT_APP = True
except ImportError:
    HAS_CHAT_APP = False
    logging.warning("Chat App example is not available")

try:
    from wrenchai.examples.question_graph import QuestionGraph
    HAS_QUESTION_GRAPH = True
except ImportError:
    HAS_QUESTION_GRAPH = False
    logging.warning("Question Graph example is not available")

# Export all available examples
__all__ = []

if HAS_SQL_GENERATOR:
    __all__.extend(['SQLGenerator', 'run_sql_example'])

if HAS_RAG:
    __all__.extend(['RAGSystem', 'build_database', 'search_and_answer'])

if HAS_STREAMING:
    __all__.extend(['MarkdownStreaming', 'StructuredDataStreaming'])

if HAS_CHAT_APP:
    __all__.extend(['ChatApp'])

if HAS_QUESTION_GRAPH:
    __all__.extend(['QuestionGraph'])

# Create a registry of available examples
examples_registry: Dict[str, Dict[str, Any]] = {
    "sql-generator": {
        "name": "SQL Generator",
        "description": "Generate SQL queries from natural language",
        "available": HAS_SQL_GENERATOR,
        "main_class": SQLGenerator if HAS_SQL_GENERATOR else None,
        "dependencies": ["pydantic-ai", "psycopg"]
    },
    "rag": {
        "name": "Retrieval-Augmented Generation",
        "description": "RAG system for answering questions from documents",
        "available": HAS_RAG,
        "main_class": RAGSystem if HAS_RAG else None,
        "dependencies": ["pydantic-ai", "psycopg", "openai"]
    },
    "streaming": {
        "name": "Streaming Examples",
        "description": "Examples of streaming text and structured data",
        "available": HAS_STREAMING,
        "classes": {
            "markdown": MarkdownStreaming if HAS_STREAMING else None,
            "structured": StructuredDataStreaming if HAS_STREAMING else None
        },
        "dependencies": ["pydantic-ai", "rich"]
    },
    "chat-app": {
        "name": "Chat Application",
        "description": "Web-based chat application with persistent storage",
        "available": HAS_CHAT_APP,
        "main_class": ChatApp if HAS_CHAT_APP else None,
        "dependencies": ["pydantic-ai", "fastapi", "uvicorn", "aiosqlite"]
    },
    "question-graph": {
        "name": "Question Graph",
        "description": "Graph-based question generation and evaluation",
        "available": HAS_QUESTION_GRAPH,
        "main_class": QuestionGraph if HAS_QUESTION_GRAPH else None,
        "dependencies": ["pydantic-ai", "pydantic-ai[graph]", "rich"]
    }
}

def list_examples() -> Dict[str, Dict[str, Any]]:
    """List all available examples
    
    Returns:
        Dictionary of examples with their details
    """
    return examples_registry

def get_example(name: str) -> Dict[str, Any]:
    """Get an example by name
    
    Args:
        name: Name of the example
        
    Returns:
        Example details or None if not found
    """
    return examples_registry.get(name)

def check_dependencies(example_name: str) -> Dict[str, bool]:
    """Check if dependencies for an example are satisfied
    
    Args:
        example_name: Name of the example
        
    Returns:
        Dictionary mapping dependencies to availability status
    """
    example = examples_registry.get(example_name)
    if not example:
        return {}
        
    dependencies = example.get("dependencies", [])
    result = {}
    
    for dependency in dependencies:
        try:
            __import__(dependency.split('[')[0])  # Handle optional extras like pydantic-ai[graph]
            result[dependency] = True
        except ImportError:
            result[dependency] = False
            
    return result