# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import subprocess
import os
import sys
from typing import Optional, Dict, Any

def execute(command: str, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Execute a command and return the result.
    
    Args:
        command: The command to execute
        cwd: Working directory for the command
        env: Environment variables for the command
        
    Returns:
        Dict containing stdout, stderr, and return code
    """
    try:
        # Use shell=True for complex commands
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            cwd=cwd,
            env={**os.environ, **(env or {})}
        )
        
        stdout, stderr = process.communicate()
        
        return {
            'stdout': stdout.decode('utf-8'),
            'stderr': stderr.decode('utf-8'),
            'returncode': process.returncode
        }
    except Exception as e:
        return {
            'stdout': '',
            'stderr': str(e),
            'returncode': 1
        }

def execute_code(code: str) -> str:
    """Execute Python code and return the result.
    
    Args:
        code: Python code to execute
        
    Returns:
        String containing the execution result
    """
    try:
        # Create a temporary file
        with open('temp_code.py', 'w') as f:
            f.write(code)
        
        # Execute the file
        result = execute(f"{sys.executable} temp_code.py")
        
        # Clean up
        os.remove('temp_code.py')
        
        if result['returncode'] == 0:
            return result['stdout']
        else:
            return f"Error: {result['stderr']}"
    except Exception as e:
        return f"Error executing code: {str(e)}"
