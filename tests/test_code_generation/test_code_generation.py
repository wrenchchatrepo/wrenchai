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
    Provides a sample CodeSpec fixture describing a recursive factorial function.
    
    Returns:
        A CodeSpec instance with a description, requirements, and usage examples for a factorial function.
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
    Provides a sample GenerationContext fixture for testing code generation scenarios.
    
    Returns:
        A GenerationContext configured with typical project settings and additional context.
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
    """
    Tests that generating code with output type 'code' produces only code output.
    
    Verifies that the generated result contains non-empty code, no tests or documentation,
    and valid dependencies and setup instructions.
    """
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
    """
    Tests that code, tests, and documentation are generated when requesting all output types.
    
    Verifies that the generated result includes non-empty code, tests, documentation, a list of dependencies, and setup instructions.
    """
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
    """
    Tests that generating with output type "docs" produces only documentation.
    
    Verifies that the generated result contains non-empty documentation, no code, no tests, and includes dependencies and setup instructions.
    """
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
    Tests that an exception is raised when an invalid language is provided to the generate function.
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
    """
    Tests that an exception is raised when an invalid framework is provided to the generate function.
    """
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
    Tests code generation for a REST API endpoint specification with multiple dependencies.
    
    Verifies that the generated code, tests, and documentation include references to FastAPI, SQLAlchemy, Pydantic, and relevant API features.
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
    """
    Tests code generation from a minimal specification containing only a description.
    
    Asserts that the generated code includes a print statement, and that tests and
    documentation are produced.
    """
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
    Tests code generation with a custom context, verifying that generated code, tests, and documentation reflect the specified style guide, test framework, and documentation format.
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