import pytest
from pathlib import Path
import tempfile
import textwrap
from typing import Dict, Any

from core.agents.codifier_agent import CodifierAgent, DocumentationRequest
from core.tools.documentation_tools import (
    DocstringParser,
    TypeHintAnalyzer,
    MarkdownGenerator,
    OpenAPIGenerator
)

@pytest.fixture
def sample_python_file():
    """Create a temporary Python file for testing."""
    content = textwrap.dedent('''
        from typing import List, Optional
        
        class Calculator:
            """A simple calculator class."""
            
            def add(self, x: float, y: float) -> float:
                """Add two numbers.
                
                Args:
                    x: First number
                    y: Second number
                    
                Returns:
                    Sum of x and y
                """
                return x + y
            
            def subtract(self, x: float, y: float) -> float:
                # Missing docstring
                return x - y
                
            def multiply(self, x: float, y: float) -> float:
                """Multiply two numbers."""  # Incomplete docstring
                return x * y
    ''')
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
    yield f.name
    Path(f.name).unlink()

@pytest.fixture
def sample_fastapi_file():
    """Create a temporary FastAPI file for testing."""
    content = textwrap.dedent('''
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
        
        app = FastAPI()
        
        class Item(BaseModel):
            name: str
            price: float
            
        @app.get("/items/{item_id}")
        async def read_item(item_id: int):
            """Get an item by ID.
            
            Args:
                item_id: The ID of the item
                
            Returns:
                The item details
            """
            return {"item_id": item_id}
    ''')
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
    yield f.name
    Path(f.name).unlink()

@pytest.fixture
async def codifier_agent():
    """Create a CodifierAgent instance."""
    agent = CodifierAgent()
    return agent

@pytest.mark.asyncio
async def test_docstring_parsing(sample_python_file):
    """Test docstring parsing functionality."""
    parser = DocstringParser()
    docstrings = await parser.parse_file(sample_python_file)
    
    assert 'Calculator' in docstrings
    assert 'add' in docstrings
    assert 'subtract' not in docstrings  # No docstring
    assert docstrings['Calculator']['docstring'] == 'A simple calculator class.'
    
    validation = await parser.validate(sample_python_file)
    assert any(result['valid'] for result in validation)
    assert any(not result['valid'] for result in validation)

@pytest.mark.asyncio
async def test_type_hint_analysis(sample_python_file):
    """Test type hint analysis functionality."""
    analyzer = TypeHintAnalyzer()
    type_info = await analyzer.analyze_file(sample_python_file)
    
    assert 'add' in type_info
    assert type_info['add']['args']['x'] == 'float'
    assert type_info['add']['args']['y'] == 'float'
    assert type_info['add']['returns'] == 'float'

@pytest.mark.asyncio
async def test_markdown_generation(sample_python_file):
    """Test markdown documentation generation."""
    generator = MarkdownGenerator()
    docs = await generator.generate_docs(sample_python_file)
    
    assert '# Calculator' in docs
    assert '### add' in docs
    assert 'def add(self, x: float, y: float) -> float:' in docs

@pytest.mark.asyncio
async def test_openapi_generation(sample_fastapi_file):
    """Test OpenAPI documentation generation."""
    generator = OpenAPIGenerator()
    docs = await generator.generate_docs(sample_fastapi_file)
    
    assert 'paths' in docs
    assert '/items/{item_id}' in docs
    
    validation = await generator.validate(sample_fastapi_file)
    assert validation[0]['valid']

@pytest.mark.asyncio
async def test_codifier_agent_docstring_generation(
    codifier_agent: CodifierAgent,
    sample_python_file: str
):
    """Test CodifierAgent's docstring generation."""
    request = DocumentationRequest(
        source_path=sample_python_file,
        doc_type='docstring',
        include_private=False
    )
    
    response = await codifier_agent.generate_documentation(request)
    assert response.success
    assert 'subtract' in response.generated_docs
    assert 'Args:' in response.generated_docs
    assert 'Returns:' in response.generated_docs

@pytest.mark.asyncio
async def test_codifier_agent_api_docs(
    codifier_agent: CodifierAgent,
    sample_fastapi_file: str
):
    """Test CodifierAgent's API documentation generation."""
    request = DocumentationRequest(
        source_path=sample_fastapi_file,
        doc_type='api',
        include_private=False
    )
    
    response = await codifier_agent.generate_documentation(request)
    assert response.success
    assert 'paths' in response.generated_docs
    assert '/items/{item_id}' in response.generated_docs

@pytest.mark.asyncio
async def test_codifier_agent_markdown_docs(
    codifier_agent: CodifierAgent,
    sample_python_file: str
):
    """Test CodifierAgent's markdown documentation generation."""
    request = DocumentationRequest(
        source_path=sample_python_file,
        doc_type='markdown',
        include_private=False
    )
    
    response = await codifier_agent.generate_documentation(request)
    assert response.success
    assert '# Calculator' in response.generated_docs
    assert '### add' in response.generated_docs

@pytest.mark.asyncio
async def test_codifier_agent_validation(
    codifier_agent: CodifierAgent,
    sample_python_file: str
):
    """Test CodifierAgent's documentation validation."""
    request = DocumentationRequest(
        source_path=sample_python_file,
        doc_type='docstring',
        include_private=False
    )
    
    validation = await codifier_agent.validate_documentation(request)
    assert isinstance(validation, list)
    assert len(validation) > 0
    assert all('valid' in result for result in validation)
    assert all('issues' in result for result in validation)

@pytest.mark.asyncio
async def test_codifier_agent_error_handling(codifier_agent: CodifierAgent):
    """Test CodifierAgent's error handling."""
    request = DocumentationRequest(
        source_path='nonexistent_file.py',
        doc_type='docstring',
        include_private=False
    )
    
    with pytest.raises(FileNotFoundError):
        await codifier_agent.generate_documentation(request)
        
@pytest.mark.asyncio
async def test_codifier_agent_invalid_doc_type(
    codifier_agent: CodifierAgent,
    sample_python_file: str
):
    """Test CodifierAgent's handling of invalid documentation types."""
    request = DocumentationRequest(
        source_path=sample_python_file,
        doc_type='invalid_type',
        include_private=False
    )
    
    with pytest.raises(ValueError):
        await codifier_agent.generate_documentation(request) 