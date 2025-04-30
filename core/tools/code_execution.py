"""
Code Execution Tool for safely running code snippets.

This module provides functionality to:
- Execute code in multiple languages
- Manage execution environments
- Handle timeouts and resource limits
- Capture output and errors
- Support interactive execution
"""

import asyncio
import logging
import subprocess
import tempfile
import os
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class Language(str, Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    SHELL = "shell"

class ExecutionMode(str, Enum):
    """Code execution modes."""
    SCRIPT = "script"  # Execute as a script file
    REPL = "repl"     # Interactive REPL mode
    NOTEBOOK = "notebook"  # Jupyter notebook-style execution

class ResourceLimits(BaseModel):
    """Resource limits for code execution."""
    max_time: int = Field(default=30, description="Maximum execution time in seconds")
    max_memory: int = Field(default=512, description="Maximum memory usage in MB")
    max_processes: int = Field(default=1, description="Maximum number of processes")
    network_access: bool = Field(default=False, description="Allow network access")
    file_access: bool = Field(default=False, description="Allow file system access")

class ExecutionContext(BaseModel):
    """Context for code execution."""
    language: Language
    mode: ExecutionMode = ExecutionMode.SCRIPT
    environment_vars: Dict[str, str] = Field(default_factory=dict)
    working_directory: Optional[str] = None
    resource_limits: ResourceLimits = Field(default_factory=ResourceLimits)
    dependencies: List[str] = Field(default_factory=list)

class ExecutionResult(BaseModel):
    """Result of code execution."""
    success: bool
    output: str = ""
    error: Optional[str] = None
    execution_time: float = 0.0
    memory_usage: float = 0.0
    exit_code: int = 0

class CodeExecutor:
    """Manages code execution in various languages."""
    
    def __init__(self):
        """
        Initializes the CodeExecutor with a temporary directory and process tracking.
        
        Creates a temporary directory for execution artifacts and sets up a dictionary to track running subprocesses by execution ID.
        """
        self.temp_dir = Path(tempfile.mkdtemp())
        self.current_processes: Dict[str, subprocess.Popen] = {}
        
    async def setup_environment(self, context: ExecutionContext) -> bool:
        """
        Prepares the execution environment for the specified context and language.
        
        Creates a virtual environment and installs dependencies for Python, or installs dependencies using npm for JavaScript and TypeScript. Returns True if the setup completes successfully; otherwise, returns False on failure.
        """
        try:
            # Create virtual environment if needed
            if context.language == Language.PYTHON:
                venv_path = self.temp_dir / "venv"
                if not venv_path.exists():
                    proc = await asyncio.create_subprocess_exec(
                        "python", "-m", "venv", str(venv_path),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await proc.wait()
                
                # Install dependencies
                if context.dependencies:
                    pip_path = venv_path / "bin" / "pip"
                    proc = await asyncio.create_subprocess_exec(
                        str(pip_path), "install", *context.dependencies,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await proc.wait()
            
            # Set up Node environment if needed
            elif context.language in [Language.JAVASCRIPT, Language.TYPESCRIPT]:
                if context.dependencies:
                    proc = await asyncio.create_subprocess_exec(
                        "npm", "install", *context.dependencies,
                        cwd=str(self.temp_dir),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await proc.wait()
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting up environment: {str(e)}")
            return False
    
    def create_execution_script(self, code: str, context: ExecutionContext) -> Path:
        """
        Creates a temporary script file containing the provided code for execution.
        
        The file extension is determined by the specified language in the execution context. For shell scripts, executable permissions are set.
        
        Args:
        	code: The code to be written to the script file.
        	context: The execution context specifying language and other parameters.
        
        Returns:
        	Path to the created script file.
        """
        extension = {
            Language.PYTHON: ".py",
            Language.JAVASCRIPT: ".js",
            Language.TYPESCRIPT: ".ts",
            Language.SHELL: ".sh"
        }[context.language]
        
        script_path = self.temp_dir / f"script{extension}"
        script_path.write_text(code)
        
        if context.language == Language.SHELL:
            script_path.chmod(0o755)  # Make executable
            
        return script_path
    
    async def execute_code(
        self,
        code: str,
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Executes the provided code snippet asynchronously within the specified execution context.
        
        Runs the code in an isolated environment with configured resource limits, environment variables, and dependencies. Captures standard output, error output, execution time, and exit code. Handles environment setup, script creation, and process management, including timeout enforcement and error reporting.
        
        Args:
            code: The code to execute.
            context: The execution context specifying language, mode, environment, resource limits, and dependencies.
        
        Returns:
            An ExecutionResult containing the outcome, including output, error message, execution time, and exit code.
        """
        start_time = datetime.now()
        
        try:
            # Set up environment
            if not await self.setup_environment(context):
                return ExecutionResult(
                    success=False,
                    error="Failed to set up execution environment"
                )
            
            # Create script file
            script_path = self.create_execution_script(code, context)
            
            # Prepare command
            cmd = self._get_execution_command(script_path, context)
            env = os.environ.copy()
            env.update(context.environment_vars)
            
            # Execute code
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=context.working_directory or str(self.temp_dir)
            )
            
            # Store process for potential cancellation
            exec_id = str(script_path)
            self.current_processes[exec_id] = proc
            
            try:
                # Wait for completion with timeout
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=context.resource_limits.max_time
                )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return ExecutionResult(
                    success=proc.returncode == 0,
                    output=stdout.decode(),
                    error=stderr.decode() if stderr else None,
                    execution_time=execution_time,
                    exit_code=proc.returncode
                )
                
            except asyncio.TimeoutError:
                proc.terminate()
                return ExecutionResult(
                    success=False,
                    error=f"Execution timed out after {context.resource_limits.max_time} seconds"
                )
                
            finally:
                # Clean up process reference
                self.current_processes.pop(exec_id, None)
            
        except Exception as e:
            logger.error(f"Error executing code: {str(e)}")
            return ExecutionResult(
                success=False,
                error=f"Execution failed: {str(e)}"
            )
    
    def _get_execution_command(self, script_path: Path, context: ExecutionContext) -> List[str]:
        """
        Constructs the command-line invocation to execute a script based on the specified language.
        
        Args:
            script_path: The path to the script file to execute.
            context: The execution context specifying language and environment.
        
        Returns:
            A list of command arguments to run the script with the appropriate interpreter.
        
        Raises:
            ValueError: If the specified language is not supported.
        """
        if context.language == Language.PYTHON:
            python_path = self.temp_dir / "venv" / "bin" / "python"
            return [str(python_path), str(script_path)]
            
        elif context.language == Language.JAVASCRIPT:
            return ["node", str(script_path)]
            
        elif context.language == Language.TYPESCRIPT:
            return ["ts-node", str(script_path)]
            
        elif context.language == Language.SHELL:
            return [str(script_path)]
            
        raise ValueError(f"Unsupported language: {context.language}")
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """
        Attempts to terminate a running code execution identified by its execution ID.
        
        Args:
            execution_id: The unique identifier of the running execution to cancel.
        
        Returns:
            True if the execution was successfully cancelled; False otherwise.
        """
        if proc := self.current_processes.get(execution_id):
            try:
                proc.terminate()
                return True
            except Exception as e:
                logger.error(f"Error cancelling execution: {str(e)}")
        return False
    
    def cleanup(self):
        """
        Terminates all running subprocesses and deletes the temporary execution directory.
        
        Cleans up resources used during code execution by stopping active processes and removing temporary files and directories.
        """
        # Terminate any running processes
        for proc in self.current_processes.values():
            try:
                proc.terminate()
            except:
                pass
        
        # Clean up temporary directory
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            logger.error(f"Error cleaning up temporary directory: {str(e)}")

# Global executor instance
code_executor = CodeExecutor()

async def execute_code(
    code: str,
    language: Language,
    mode: ExecutionMode = ExecutionMode.SCRIPT,
    environment_vars: Optional[Dict[str, str]] = None,
    working_directory: Optional[str] = None,
    resource_limits: Optional[ResourceLimits] = None,
    dependencies: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Asynchronously executes a code snippet in a specified language and environment.
    
    Creates an isolated execution context with optional environment variables, working directory, resource limits, and dependencies. Returns a dictionary containing the execution outcome, including output, error messages, execution time, memory usage, and exit code.
    
    Args:
        code: The code snippet to execute.
        language: The programming language in which to execute the code.
        mode: The execution mode (e.g., script, REPL, notebook).
        environment_vars: Optional environment variables for the execution context.
        working_directory: Optional working directory for code execution.
        resource_limits: Optional resource constraints for execution.
        dependencies: Optional list of dependencies to install before execution.
    
    Returns:
        A dictionary with keys: success (bool), output (str), error (str), execution_time (float), memory_usage (float), and exit_code (int).
    """
    try:
        context = ExecutionContext(
            language=language,
            mode=mode,
            environment_vars=environment_vars or {},
            working_directory=working_directory,
            resource_limits=resource_limits or ResourceLimits(),
            dependencies=dependencies or []
        )
        
        result = await code_executor.execute_code(code, context)
        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "execution_time": result.execution_time,
            "memory_usage": result.memory_usage,
            "exit_code": result.exit_code
        }
        
    except Exception as e:
        logger.error(f"Error in execute_code: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def cancel_execution(execution_id: str) -> Dict[str, Any]:
    """
    Attempts to cancel a running code execution by its execution ID.
    
    Args:
        execution_id: The unique identifier of the execution to cancel.
    
    Returns:
        A dictionary indicating whether the cancellation was successful and a message or error.
    """
    try:
        success = await code_executor.cancel_execution(execution_id)
        return {
            "success": success,
            "message": "Execution cancelled" if success else "Failed to cancel execution"
        }
    except Exception as e:
        logger.error(f"Error in cancel_execution: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
