# Wrenchai Examples

This document describes the Pydantic AI example integrations available in Wrenchai.

## Overview

Wrenchai includes implementations of several Pydantic AI example applications:

1. **SQL Generator** - Generate SQL queries from natural language descriptions
2. **RAG System** - Retrieval-Augmented Generation for answering questions from documents
3. **Streaming Examples** - Streaming markdown and structured data from AI models
4. **Chat Application** - Web-based chat interface with persistent storage
5. **Question Graph** - Graph-based question generation and evaluation

## Requirements

Each example has specific dependencies which can be installed from the updated `requirements.txt` file:

```bash
pip install -r requirements.txt
```

For database-based examples (SQL Generator and RAG), you'll need PostgreSQL:

```bash
# For SQL Generator (port 54320 to avoid conflicts)
docker run -d --name postgres-sql-gen -p 54320:5432 -e POSTGRES_PASSWORD=postgres postgres

# For RAG (with pgvector)
docker run -d --name postgres-rag -p 5432:5432 -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg17
```

## Running Examples

You can run the examples using the provided command-line tool:

```bash
# List available examples
python wrenchai_examples.py

# Run a specific example
python wrenchai_examples.py <example-name> [arguments]
```

## Example Details

### SQL Generator

Generates SQL queries from natural language descriptions using Pydantic AI.

```bash
# Run with default settings
python wrenchai_examples.py sql-generator "Find all error logs from last week"

# Run with custom database settings
python wrenchai_examples.py sql-generator "Count users by country" --host localhost --port 54320
```

### RAG System

Retrieval-Augmented Generation system for answering questions based on document content.

```bash
# Build the search database from documentation
python wrenchai_examples.py rag build --docs-dir ./docs

# Search and get answers
python wrenchai_examples.py rag search "How do I configure the chat application?"
```

### Streaming Examples

Demonstrates streaming responses from AI models, both in markdown format and as structured data.

```bash
# Stream markdown content
python wrenchai_examples.py streaming markdown "Explain Python async/await"

# Stream structured whale data
python wrenchai_examples.py streaming structured
```

### Chat Application

Web-based chat interface that supports conversation history and persistent storage.

```bash
# Start the chat application
python wrenchai_examples.py chat-app

# Use custom host and port
python wrenchai_examples.py chat-app --host 0.0.0.0 --port 8080
```

After starting, open your browser to [http://127.0.0.1:8000](http://127.0.0.1:8000) (or your custom host/port).

### Question Graph

Graph-based system for generating questions, evaluating answers, and providing feedback.

```bash
# Run with default settings (Python programming questions)
python wrenchai_examples.py question-graph

# Run with a custom topic
python wrenchai_examples.py question-graph --topic "Machine Learning" --max-attempts 5
```

## Implementation Notes

All examples are designed to be modular and can be imported and used programmatically:

```python
from wrenchai.examples import SQLGenerator, RAGSystem, MarkdownStreaming

# Use SQL Generator
generator = SQLGenerator()
results = await generator.generate_sql("Find all users who logged in yesterday")

# Use RAG
rag_system = RAGSystem()
answer = await rag_system.answer_question("How do I configure logging?")
```

Each example follows the Pydantic AI patterns and best practices for their respective categories.

## Troubleshooting

- **Missing Dependencies**: Check error messages for missing dependencies and install them.
- **Database Connectivity**: Ensure PostgreSQL is running and accessible.
- **API Keys**: Set environment variables for required API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.).
- **Model Availability**: If a model is unavailable, try a different one using the `--model` flag.