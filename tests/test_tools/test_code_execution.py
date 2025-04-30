"""Tests for the Code Execution Tool."""

import pytest
import asyncio
import os
from pathlib import Path
from typing import Dict, Any

from core.tools.code_execution import (
    Language,
    ExecutionMode,
    ResourceLimits,
    ExecutionContext,
    ExecutionResult,
    CodeExecutor,
    code_executor,
    execute_code,
    cancel_execution
)

@pytest.fixture
def sample_python_code():
    """Sample Python code for testing."""
    return """
def greet(name):
    return f"Hello, {name}!"

print(greet("World"))
"""

@pytest.fixture
def sample_javascript_code():
    """Sample JavaScript code for testing."""
    return """
function greet(name) {
    return `Hello, ${name}!`;
}

console.log(greet("World"));
"""

@pytest.fixture
def sample_typescript_code():
    """Sample TypeScript code for testing."""
    return """
function greet(name: string): string {
    return `Hello, ${name}!`;
}

console.log(greet("World"));
"""

@pytest.fixture
def sample_shell_code():
    """Sample shell script for testing."""
    return """
#!/bin/bash
echo "Hello, World!"
"""

@pytest.fixture
def resource_limits():
    """Sample resource limits."""
    return ResourceLimits(
        max_time=5,
        max_memory=256,
        max_processes=1,
        network_access=False,
        file_access=True
    )

@pytest.fixture
async def executor():
    """Create a CodeExecutor instance."""
    exec = CodeExecutor()
    yield exec
    exec.cleanup()

@pytest.mark.asyncio
async def test_python_execution(executor, sample_python_code):
    """Test Python code execution."""
    context = ExecutionContext(
        language=Language.PYTHON,
        mode=ExecutionMode.SCRIPT
    )
    
    result = await executor.execute_code(sample_python_code, context)
    
    assert result.success
    assert "Hello, World!" in result.output
    assert result.error is None
    assert result.execution_time > 0

@pytest.mark.asyncio
async def test_javascript_execution(executor, sample_javascript_code):
    """Test JavaScript code execution."""
    context = ExecutionContext(
        language=Language.JAVASCRIPT,
        mode=ExecutionMode.SCRIPT
    )
    
    result = await executor.execute_code(sample_javascript_code, context)
    
    assert result.success
    assert "Hello, World!" in result.output
    assert result.error is None

@pytest.mark.asyncio
async def test_typescript_execution(executor, sample_typescript_code):
    """Test TypeScript code execution."""
    context = ExecutionContext(
        language=Language.TYPESCRIPT,
        mode=ExecutionMode.SCRIPT
    )
    
    result = await executor.execute_code(sample_typescript_code, context)
    
    assert result.success
    assert "Hello, World!" in result.output
    assert result.error is None

@pytest.mark.asyncio
async def test_shell_execution(executor, sample_shell_code):
    """Test shell script execution."""
    context = ExecutionContext(
        language=Language.SHELL,
        mode=ExecutionMode.SCRIPT
    )
    
    result = await executor.execute_code(sample_shell_code, context)
    
    assert result.success
    assert "Hello, World!" in result.output
    assert result.error is None

@pytest.mark.asyncio
async def test_execution_with_dependencies(executor):
    """Test code execution with dependencies."""
    code = """
import numpy as np
print(np.array([1, 2, 3]).mean())
"""
    
    context = ExecutionContext(
        language=Language.PYTHON,
        dependencies=["numpy"]
    )
    
    result = await executor.execute_code(code, context)
    
    assert result.success
    assert "2.0" in result.output

@pytest.mark.asyncio
async def test_execution_timeout(executor):
    """Test execution timeout."""
    code = """
import time
time.sleep(10)
"""
    
    context = ExecutionContext(
        language=Language.PYTHON,
        resource_limits=ResourceLimits(max_time=1)
    )
    
    result = await executor.execute_code(code, context)
    
    assert not result.success
    assert "timed out" in result.error.lower()

@pytest.mark.asyncio
async def test_execution_with_environment_vars(executor):
    """Test execution with environment variables."""
    code = """
import os
print(os.environ.get('TEST_VAR'))
"""
    
    context = ExecutionContext(
        language=Language.PYTHON,
        environment_vars={"TEST_VAR": "test_value"}
    )
    
    result = await executor.execute_code(code, context)
    
    assert result.success
    assert "test_value" in result.output

@pytest.mark.asyncio
async def test_execution_with_working_directory(executor, tmp_path):
    """Test execution with custom working directory."""
    # Create a test file in the temp directory
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    code = """
import os
print(os.listdir('.'))
"""
    
    context = ExecutionContext(
        language=Language.PYTHON,
        working_directory=str(tmp_path)
    )
    
    result = await executor.execute_code(code, context)
    
    assert result.success
    assert "test.txt" in result.output

@pytest.mark.asyncio
async def test_invalid_code_execution(executor):
    """Test execution of invalid code."""
    code = """
print(undefined_variable)
"""
    
    context = ExecutionContext(
        language=Language.PYTHON
    )
    
    result = await executor.execute_code(code, context)
    
    assert not result.success
    assert result.error is not None
    assert "NameError" in result.error

@pytest.mark.asyncio
async def test_cancel_execution(executor):
    """Test cancelling execution."""
    code = """
import time
time.sleep(30)
"""
    
    context = ExecutionContext(
        language=Language.PYTHON
    )
    
    # Start execution in background
    task = asyncio.create_task(executor.execute_code(code, context))
    
    # Wait briefly for execution to start
    await asyncio.sleep(0.1)
    
    # Cancel execution
    exec_id = str(next(iter(executor.current_processes.keys())))
    cancelled = await executor.cancel_execution(exec_id)
    
    assert cancelled
    
    # Wait for task to complete
    result = await task
    assert not result.success

@pytest.mark.asyncio
async def test_execute_code_helper():
    """Test the execute_code helper function."""
    code = """
print("Hello from helper!")
"""
    
    result = await execute_code(
        code=code,
        language=Language.PYTHON,
        mode=ExecutionMode.SCRIPT,
        environment_vars={"TEST": "test"},
        resource_limits=ResourceLimits(max_time=5)
    )
    
    assert result["success"]
    assert "Hello from helper!" in result["output"]

@pytest.mark.asyncio
async def test_cancel_execution_helper():
    """Test the cancel_execution helper function."""
    # Start a long-running execution
    code = """
import time
time.sleep(30)
"""
    
    # Start execution in background
    task = asyncio.create_task(execute_code(
        code=code,
        language=Language.PYTHON
    ))
    
    # Wait briefly for execution to start
    await asyncio.sleep(0.1)
    
    # Get execution ID
    exec_id = str(next(iter(code_executor.current_processes.keys())))
    
    # Cancel execution
    result = await cancel_execution(exec_id)
    
    assert result["success"]
    
    # Wait for task to complete
    final_result = await task
    assert not final_result["success"]

def test_cleanup(executor):
    """Test cleanup of temporary files and processes."""
    temp_dir = executor.temp_dir
    assert temp_dir.exists()
    
    executor.cleanup()
    assert not temp_dir.exists()

def test_resource_limits_validation():
    """Test resource limits validation."""
    # Valid limits
    limits = ResourceLimits(
        max_time=30,
        max_memory=512,
        max_processes=1
    )
    assert limits.max_time == 30
    assert limits.max_memory == 512
    
    # Invalid time
    with pytest.raises(ValueError):
        ResourceLimits(max_time=-1)
    
    # Invalid memory
    with pytest.raises(ValueError):
        ResourceLimits(max_memory=-1)

def test_execution_context_validation():
    """Test execution context validation."""
    # Valid context
    context = ExecutionContext(
        language=Language.PYTHON,
        mode=ExecutionMode.SCRIPT
    )
    assert context.language == Language.PYTHON
    assert context.mode == ExecutionMode.SCRIPT
    
    # Invalid language
    with pytest.raises(ValueError):
        ExecutionContext(language="invalid")
    
    # Invalid mode
    with pytest.raises(ValueError):
        ExecutionContext(
            language=Language.PYTHON,
            mode="invalid"
        ) 