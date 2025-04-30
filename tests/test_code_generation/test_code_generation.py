"""
Tests for the Code Generation Tool.

This module contains tests for all core functionality of the code generation tool,
including code, test, and documentation generation.
"""

import pytest
from typing import Dict, Any

from core.tools.code_generation import (
    CodeSpec,
    GenerationContext,
    GeneratedCode,
    generate
)

@pytest.fixture
def sample_spec() -> CodeSpec:
    """
    Provides a sample CodeSpec fixture for testing code generation.
    
    Returns:
        A CodeSpec instance describing a recursive factorial function, including requirements and usage examples.
    """
    return CodeSpec(
        description="Create a function to calculate factorial",
        requirements=[
            "Function should be recursive",
            "Should handle positive integers",
            "Should raise ValueError for negative numbers"
        ],
        examples=[
            "factorial(5) -> 120",
            "factorial(0) -> 1"
        ]
    )

@pytest.fixture
def sample_context() -> GenerationContext:
    """
    Provides a sample GenerationContext fixture for testing code generation.
    
    Returns:
        A GenerationContext configured for a library project using PEP8, pytest, and Google doc format, with additional context for package name and author.
    """
    return GenerationContext(
        project_type="library",
        style_guide="pep8",
        test_framework="pytest",
        doc_format="google",
        additional_context={
            "package_name": "math_utils",
            "author": "WrenchAI"
        }
    )

@pytest.mark.asyncio
async def test_generate_code_only(sample_spec: CodeSpec, sample_context: GenerationContext):
    """Test generating only code."""
    result = await generate(
        spec=sample_spec,
        language="python",
        framework="standard",
        output_type="code",
        context=sample_context
    )
    
    assert isinstance(result, GeneratedCode)
    assert result.code != ""
    assert result.tests is None
    assert result.docs is None
    assert isinstance(result.dependencies, list)
    assert isinstance(result.setup_instructions, str)

@pytest.mark.asyncio
async def test_generate_with_tests(sample_spec: CodeSpec, sample_context: GenerationContext):
    """Test generating code with tests."""
    result = await generate(
        spec=sample_spec,
        language="python",
        framework="standard",
        output_type="all",
        context=sample_context
    )
    
    assert isinstance(result, GeneratedCode)
    assert result.code != ""
    assert result.tests is not None
    assert result.docs is not None
    assert isinstance(result.dependencies, list)
    assert isinstance(result.setup_instructions, str)

@pytest.mark.asyncio
async def test_generate_docs_only(sample_spec: CodeSpec, sample_context: GenerationContext):
    """Test generating only documentation."""
    result = await generate(
        spec=sample_spec,
        language="python",
        framework="standard",
        output_type="docs",
        context=sample_context
    )
    
    assert isinstance(result, GeneratedCode)
    assert result.code == ""
    assert result.tests is None
    assert result.docs is not None
    assert isinstance(result.dependencies, list)
    assert isinstance(result.setup_instructions, str)

@pytest.mark.asyncio
async def test_invalid_language():
    """
    Tests that an exception is raised when an unsupported language is specified during code generation.
    """
    spec = CodeSpec(description="Test invalid language")
    
    with pytest.raises(Exception):
        await generate(
            spec=spec,
            language="invalid_language",
            framework="standard"
        )

@pytest.mark.asyncio
async def test_invalid_framework():
    """Test handling of invalid framework."""
    spec = CodeSpec(description="Test invalid framework")
    
    with pytest.raises(Exception):
        await generate(
            spec=spec,
            language="python",
            framework="invalid_framework"
        )

@pytest.mark.asyncio
async def test_complex_spec(sample_context: GenerationContext):
    """
    Tests code generation for a complex REST API specification with multiple dependencies.
    
    Verifies that the generated code, tests, and documentation include references to FastAPI, SQLAlchemy, and Pydantic, and that the output matches the requirements and examples specified in the complex spec.
    """
    spec = CodeSpec(
        description="Create a REST API endpoint",
        requirements=[
            "POST endpoint for user creation",
            "Input validation using Pydantic",
            "Database integration with SQLAlchemy",
            "Error handling for duplicate users"
        ],
        dependencies=[
            "fastapi",
            "sqlalchemy",
            "pydantic"
        ],
        examples=[
            "POST /users/ with user data",
            "Returns 201 on success",
            "Returns 400 on validation error",
            "Returns 409 on duplicate user"
        ]
    )
    
    result = await generate(
        spec=spec,
        language="python",
        framework="fastapi",
        output_type="all",
        context=sample_context
    )
    
    assert isinstance(result, GeneratedCode)
    assert "fastapi" in result.dependencies
    assert "sqlalchemy" in result.dependencies
    assert "pydantic" in result.dependencies
    assert "POST" in result.code
    assert "test_create_user" in result.tests
    assert "API documentation" in result.docs

@pytest.mark.asyncio
async def test_minimal_spec():
    """Test generating code from a minimal specification."""
    spec = CodeSpec(description="Print hello world")
    
    result = await generate(
        spec=spec,
        language="python",
        framework="standard"
    )
    
    assert isinstance(result, GeneratedCode)
    assert "print" in result.code
    assert result.tests is not None
    assert result.docs is not None

@pytest.mark.asyncio
async def test_custom_context():
    """
    Tests code generation with a custom context, verifying that style guide, test framework, and documentation format influence the generated output as expected.
    
    Asserts that the generated code includes references to JSON formatting and debug logging, tests mention the unittest framework, and documentation follows the numpy doc format.
    """
    spec = CodeSpec(description="Create a logging utility")
    context = GenerationContext(
        project_type="application",
        style_guide="google",
        test_framework="unittest",
        doc_format="numpy",
        additional_context={
            "log_format": "json",
            "log_level": "DEBUG"
        }
    )
    
    result = await generate(
        spec=spec,
        language="python",
        framework="standard",
        context=context
    )
    
    assert isinstance(result, GeneratedCode)
    assert "json" in result.code.lower()
    assert "debug" in result.code.lower()
    assert "unittest" in result.tests.lower()
    assert "Parameters" in result.docs  # Numpy doc format uses "Parameters" 