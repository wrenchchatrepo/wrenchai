# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import sys
import logging
import asyncio
import json
from typing import Optional, List, Dict, Any, Union, Tuple
from pathlib import Path
import argparse

# Try to import RAG dependencies
try:
    import psycopg
    from psycopg.rows import dict_row
    HAS_PSYCOPG = True
except ImportError:
    HAS_PSYCOPG = False
    logging.warning("psycopg is not installed. RAG functionality will be limited.")

# Check for OpenAI (required for embeddings)
try:
    import openai
    from openai import OpenAI, AsyncOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    logging.warning("openai is not installed. RAG functionality will be limited.")

# Check for Pydantic AI
try:
    from pydantic_ai import Agent
    HAS_PYDANTIC_AI = True
except ImportError:
    HAS_PYDANTIC_AI = False
    logging.warning("pydantic-ai is not installed. RAG functionality will not work.")

# Check for rich (optional - for better output formatting)
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    logging.warning("rich is not installed. Output will use standard formatting.")

class RAGSystem:
    """Retrieval-Augmented Generation system"""
    
    def __init__(self, 
                db_host: str = "localhost", 
                db_port: int = 5432,
                db_name: str = "wrenchai",
                db_user: str = "postgres",
                db_password: str = "postgres",
                model: str = "openai:gpt-4-turbo",
                embedding_model: str = "text-embedding-3-small"):
        """Initialize the RAG system
        
        Args:
            db_host: PostgreSQL host
            db_port: PostgreSQL port
            db_name: Database name
            db_user: Database user
            db_password: Database password
            model: AI model to use
            embedding_model: OpenAI embedding model to use
        """
        self.db_config = {
            "host": db_host,
            "port": db_port,
            "dbname": db_name,
            "user": db_user,
            "password": db_password
        }
        
        self.model = model
        self.embedding_model = embedding_model
        self.conn = None
        self.openai_client = None
        self._check_requirements()
    
    def _check_requirements(self):
        """Check if all required dependencies are installed"""
        if not HAS_PYDANTIC_AI:
            logging.error("pydantic-ai is required for RAG")
            raise ImportError("pydantic-ai is required for RAG")
            
        if not HAS_PSYCOPG:
            logging.warning("psycopg is not installed. Database functionality will be disabled.")
            
        if not HAS_OPENAI:
            logging.warning("openai is not installed. Embedding functionality will be disabled.")
    
    async def connect(self) -> bool:
        """Connect to the PostgreSQL database
        
        Returns:
            True if connection successful, False otherwise
        """
        if not HAS_PSYCOPG:
            logging.warning("psycopg is not installed. Database functionality will be disabled.")
            return False
            
        try:
            # Connect to database
            self.conn = await psycopg.AsyncConnection.connect(
                **self.db_config, 
                autocommit=True,
                row_factory=dict_row
            )
            
            # Initialize OpenAI client
            if HAS_OPENAI:
                self.openai_client = AsyncOpenAI()
            
            logging.info("Connected to PostgreSQL database")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to PostgreSQL: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the PostgreSQL database"""
        if self.conn:
            await self.conn.close()
            self.conn = None
            logging.info("Disconnected from PostgreSQL database")
    
    async def setup_database(self) -> bool:
        """Set up the database schema
        
        Returns:
            True if successful, False otherwise
        """
        if not self.conn:
            logging.warning("Not connected to database.")
            return False
            
        try:
            async with self.conn.cursor() as cur:
                # Check if pgvector extension exists
                await cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector';")
                result = await cur.fetchone()
                
                if not result:
                    # Create vector extension
                    await cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                # Create document table
                await cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    section TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding VECTOR(1536)
                );
                """)
                
                # Create index on embedding
                await cur.execute("""
                CREATE INDEX IF NOT EXISTS documents_embedding_idx 
                ON documents USING ivfflat (embedding vector_l2_ops)
                WITH (lists = 100);
                """)
                
            logging.info("Database schema set up successfully")
            return True
        except Exception as e:
            logging.error(f"Failed to set up database schema: {e}")
            return False
    
    async def create_embedding(self, text: str) -> List[float]:
        """Create an embedding for the given text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        if not HAS_OPENAI:
            logging.error("openai is required for embedding generation")
            raise ImportError("openai is required for embedding generation")
            
        response = await self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        
        return response.data[0].embedding
    
    async def add_document(self, title: str, section: str, content: str) -> int:
        """Add a document to the database
        
        Args:
            title: Document title
            section: Document section
            content: Document content
            
        Returns:
            Document ID
        """
        if not self.conn:
            logging.warning("Not connected to database.")
            return -1
            
        try:
            # Create embedding
            embedding = await self.create_embedding(content)
            
            # Insert document
            async with self.conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO documents (title, section, content, embedding)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (title, section, content, embedding)
                )
                result = await cur.fetchone()
                
            return result["id"]
        except Exception as e:
            logging.error(f"Failed to add document: {e}")
            return -1
    
    async def search_documents(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for documents matching the query
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching documents
        """
        if not self.conn:
            logging.warning("Not connected to database.")
            return []
            
        try:
            # Create embedding for query
            query_embedding = await self.create_embedding(query)
            
            # Search for documents
            async with self.conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id, title, section, content,
                           1 - (embedding <-> %s) AS similarity
                    FROM documents
                    ORDER BY similarity DESC
                    LIMIT %s;
                    """,
                    (query_embedding, limit)
                )
                results = await cur.fetchall()
                
            return results
        except Exception as e:
            logging.error(f"Failed to search documents: {e}")
            return []
    
    async def answer_question(self, query: str) -> Dict[str, Any]:
        """Answer a question using RAG
        
        Args:
            query: Question to answer
            
        Returns:
            Dictionary with answer and sources
        """
        # Search for relevant documents
        documents = await self.search_documents(query)
        
        if not documents:
            return {
                "answer": "I couldn't find any relevant information to answer your question.",
                "sources": []
            }
            
        # Create context from documents
        context = "\n\n".join([
            f"Section: {doc['title']} - {doc['section']}\n{doc['content']}"
            for doc in documents
        ])
        
        # Create sources list
        sources = [
            {
                "title": doc["title"],
                "section": doc["section"],
                "similarity": doc["similarity"]
            }
            for doc in documents
        ]
        
        # Create agent
        agent = Agent(
            self.model,
            instructions=f"""
            You are a knowledgeable assistant that answers questions based on the provided context.
            Always base your answer on the information in the context.
            If you don't know the answer or if the context doesn't contain relevant information, say so.
            Keep your answers concise and to the point.
            """
        )
        
        try:
            # Run the agent
            prompt = f"""
            Question: {query}
            
            Context:
            {context}
            """
            
            response = await agent.run(prompt)
            
            return {
                "answer": response.output,
                "sources": sources
            }
        except Exception as e:
            logging.error(f"Error answering question: {e}")
            return {
                "answer": f"An error occurred: {str(e)}",
                "sources": sources
            }

async def build_database(docs_dir: str, rag_system: RAGSystem):
    """Build the RAG database from documentation files
    
    Args:
        docs_dir: Directory containing documentation files
        rag_system: RAG system instance
    """
    # Connect to database
    if not await rag_system.connect():
        logging.error("Failed to connect to database")
        return
    
    try:
        # Set up database schema
        if not await rag_system.setup_database():
            logging.error("Failed to set up database schema")
            return
            
        # Find all markdown files
        docs_path = Path(docs_dir)
        markdown_files = list(docs_path.glob("**/*.md"))
        
        if not markdown_files:
            logging.warning(f"No markdown files found in {docs_dir}")
            return
            
        print(f"Found {len(markdown_files)} markdown files")
        
        # Process each file
        for md_file in markdown_files:
            # Read file
            content = md_file.read_text()
            
            # Split into sections
            sections = split_markdown_into_sections(content)
            
            # Get relative path for title
            rel_path = md_file.relative_to(docs_path)
            
            # Add each section
            for section_title, section_content in sections:
                doc_id = await rag_system.add_document(
                    str(rel_path),
                    section_title,
                    section_content
                )
                
                if doc_id >= 0:
                    print(f"Added section '{section_title}' from {rel_path}")
                
        print("Database build complete")
    finally:
        # Disconnect
        await rag_system.disconnect()

def split_markdown_into_sections(content: str) -> List[Tuple[str, str]]:
    """Split markdown content into sections
    
    Args:
        content: Markdown content
        
    Returns:
        List of (section_title, section_content) tuples
    """
    lines = content.split("\n")
    sections = []
    
    current_section = ""
    current_content = []
    
    for line in lines:
        if line.startswith("# "):
            # New H1 section
            if current_section:
                sections.append((current_section, "\n".join(current_content)))
            current_section = line[2:].strip()
            current_content = []
        elif line.startswith("## "):
            # New H2 section
            if current_section:
                sections.append((current_section, "\n".join(current_content)))
            current_section = line[3:].strip()
            current_content = []
        else:
            current_content.append(line)
    
    # Add the last section
    if current_section:
        sections.append((current_section, "\n".join(current_content)))
    
    # If no sections found, use the whole document
    if not sections:
        sections = [("Main Content", content)]
    
    return sections

async def search_and_answer(query: str, rag_system: RAGSystem):
    """Search for documents and answer a question
    
    Args:
        query: Search query
        rag_system: RAG system instance
    """
    # Connect to database
    if not await rag_system.connect():
        logging.error("Failed to connect to database")
        return
    
    try:
        # Get answer
        result = await rag_system.answer_question(query)
        
        # Display result
        if HAS_RICH:
            console.print(Panel(Markdown(result["answer"]), title="Answer", border_style="green"))
            
            if result["sources"]:
                console.print("\n[bold blue]Sources:[/bold blue]")
                for i, source in enumerate(result["sources"], 1):
                    console.print(f"{i}. {source['title']} - {source['section']} " +
                                  f"(similarity: {source['similarity']:.2f})")
        else:
            print("\nAnswer:")
            print(result["answer"])
            
            if result["sources"]:
                print("\nSources:")
                for i, source in enumerate(result["sources"], 1):
                    print(f"{i}. {source['title']} - {source['section']} " +
                          f"(similarity: {source['similarity']:.2f})")
    finally:
        # Disconnect
        await rag_system.disconnect()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="RAG System")
    parser.add_argument("action", choices=["build", "search"], help="Action to perform")
    parser.add_argument("query", nargs="?", help="Search query (for search action)")
    parser.add_argument("--docs-dir", default="docs", help="Documentation directory (for build action)")
    parser.add_argument("--db-host", default="localhost", help="Database host")
    parser.add_argument("--db-port", type=int, default=5432, help="Database port")
    parser.add_argument("--db-name", default="wrenchai", help="Database name")
    parser.add_argument("--db-user", default="postgres", help="Database user")
    parser.add_argument("--db-password", default="postgres", help="Database password")
    
    args = parser.parse_args()
    
    # Create RAG system
    rag_system = RAGSystem(
        db_host=args.db_host,
        db_port=args.db_port,
        db_name=args.db_name,
        db_user=args.db_user,
        db_password=args.db_password
    )
    
    if args.action == "build":
        asyncio.run(build_database(args.docs_dir, rag_system))
    elif args.action == "search":
        if not args.query:
            print("Error: Search query is required for search action")
            parser.print_help()
            sys.exit(1)
        asyncio.run(search_and_answer(args.query, rag_system))

if __name__ == "__main__":
    main()