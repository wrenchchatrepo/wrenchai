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
    """
    Provides a sample Python code snippet that prints a greeting for testing purposes.
    
    Returns:
        A multi-line string containing Python code that defines and calls a greeting function.
    """
    return """
def greet(name):
    return f"Hello, {name}!"

print(greet("World"))
"""

@pytest.fixture
def sample_javascript_code():
    """
    Provides a sample JavaScript code snippet that prints a greeting message.
    
    Returns:
        A string containing JavaScript code for testing purposes.
    """
    return """
function greet(name) {
    return `Hello, ${name}!`;
}

console.log(greet("World"));
"""

@pytest.fixture
def sample_typescript_code():
    """
    Provides a sample TypeScript code snippet that prints a greeting message.
    
    Returns:
        A string containing TypeScript code for testing purposes.
    """
    return """
function greet(name: string): string {
    return `Hello, ${name}!`;
}

console.log(greet("World"));
"""

@pytest.fixture
def sample_shell_code():
    """
    Provides a sample shell script that prints "Hello, World!" for testing purposes.
    """
    return """
#!/bin/bash
echo "Hello, World!"
"""

@pytest.fixture
def resource_limits():
    """
    Provides a sample ResourceLimits instance with predefined constraints for testing.
    
    Returns:
        A ResourceLimits object with set limits on time, memory, processes, and access permissions.
    """
    return ResourceLimits(
        max_time=5,
        max_memory=256,
        max_processes=1,
        network_access=False,
        file_access=True
    )

@pytest.fixture
async def executor():
    """
    Asynchronous pytest fixture that provides a CodeExecutor instance for test cases.
    
    Yields:
        A CodeExecutor instance for use within a test. Ensures cleanup after the test completes.
    """
    exec = CodeExecutor()
    yield exec
    exec.cleanup()

@pytest.mark.asyncio
async def test_python_execution(executor, sample_python_code):
    """
    Tests that Python code executes successfully and produces the expected output.
    
    Asserts that execution is successful, the output contains "Hello, World!", no error is present, and execution time is positive.
    """
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
    """
    Tests execution of JavaScript code using the executor and verifies successful output.
    
    Asserts that the execution succeeds, the output contains "Hello, World!", and no error is present.
    """
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
    """
    Tests execution of TypeScript code in script mode and verifies successful output.
    
    Asserts that the execution succeeds, the output contains "Hello, World!", and no error is present.
    """
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
    """
    Tests execution of a shell script and verifies successful output.
    
    Asserts that the shell script runs successfully, produces the expected output, and does not return an error.
    """
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
    """
    Tests that Python code requiring external dependencies executes successfully.
    
    Verifies that code importing and using the 'numpy' library runs correctly when
    the dependency is specified, and that the expected output is produced.
    """
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
    """
    Tests that code execution fails with an appropriate error message when exceeding the maximum allowed execution time.
    """
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
    """
    Tests that code execution correctly accesses and outputs environment variables.
    
    Executes Python code that prints the value of an environment variable set in the execution context, and verifies that the output contains the expected value.
    """
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
    """
    Tests that code execution in a custom working directory can access files present in that directory.
    
    Creates a test file in a temporary directory, executes Python code listing directory contents, and asserts that the file is visible in the output.
    """
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
    """
    Tests that executing invalid Python code results in failure and returns a NameError.
    
    Verifies that the execution fails, an error message is present, and the error contains 'NameError' when running code referencing an undefined variable.
    """
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
    """
    Tests that a running code execution can be cancelled and reports failure upon cancellation.
    
    Starts a long-running Python code execution, cancels it using the executor's cancellation method, and asserts that the cancellation succeeds and the final result indicates unsuccessful execution.
    """
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
    """
    Tests the execute_code helper function for successful Python code execution.
    
    Verifies that the helper correctly executes Python code with specified environment variables and resource limits, and that the output contains the expected string.
    """
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
    """
    Tests that the cancel_execution helper function successfully cancels a running code execution.
    
    Starts a long-running Python code execution, cancels it using the execution ID, and asserts that cancellation is successful and the final result indicates failure.
    """
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
    """
    Tests that the executor's temporary directory is removed after calling cleanup.
    """
    temp_dir = executor.temp_dir
    assert temp_dir.exists()
    
    executor.cleanup()
    assert not temp_dir.exists()

def test_resource_limits_validation():
    """
    Tests that ResourceLimits accepts valid parameters and raises ValueError for invalid max_time or max_memory values.
    """
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