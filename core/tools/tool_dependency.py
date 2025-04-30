"""Tool dependency management system for WrenchAI.

This module provides functionality to:
- Verify and manage tool dependencies
- Check if required tools are available
- Manage tool version compatibility
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from pydantic import BaseModel, Field
import json
from pathlib import Path
import os
import yaml
import importlib.util
import inspect
from enum import Enum

logger = logging.getLogger(__name__)

class DependencyType(str, Enum):
    """Types of tool dependencies."""
    REQUIRED = "required"  # Tool won't work without this dependency
    OPTIONAL = "optional"  # Tool has limited functionality without this dependency
    ENHANCED = "enhanced"  # Tool works but with enhanced features when dependency is available

class DependencyStatus(str, Enum):
    """Status of tool dependencies."""
    SATISFIED = "satisfied"  # Dependency is available and correct version
    MISSING = "missing"      # Dependency is not available
    VERSION_MISMATCH = "version_mismatch"  # Dependency version is incompatible
    UNKNOWN = "unknown"      # Dependency status couldn't be determined

class ToolDependency(BaseModel):
    """Model for tool dependencies."""
    name: str = Field(..., description="Name of the dependency")
    type: DependencyType = Field(default=DependencyType.REQUIRED, description="Type of dependency")
    min_version: Optional[str] = Field(None, description="Minimum version required")
    max_version: Optional[str] = Field(None, description="Maximum version supported")
    module_path: Optional[str] = Field(None, description="Import path for Python module")
    binary_name: Optional[str] = Field(None, description="Name of binary executable")
    check_command: Optional[str] = Field(None, description="Command to check dependency")
    fallback: Optional[str] = Field(None, description="Fallback dependency if this one is missing")

class ToolDependencyManager:
    """System for managing tool dependencies."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initializes the ToolDependencyManager with the specified configuration file.
        
        If no configuration path is provided, uses the default path "core/configs/tool_dependencies.yaml". Loads tool dependency definitions and prepares internal caches.
        """
        self.tool_dependencies: Dict[str, List[ToolDependency]] = {}
        self.dependency_status_cache: Dict[str, Dict[str, DependencyStatus]] = {}
        self.config_path = config_path or os.path.join("core", "configs", "tool_dependencies.yaml")
        self._load_configuration()
        
    def _load_configuration(self):
        """
        Loads tool dependency configuration from a YAML file or creates a default configuration if the file is missing or invalid.
        
        Parses the configuration to populate the internal mapping of tool IDs to their dependencies. If loading fails, falls back to generating a default configuration.
        """
        try:
            config_path = Path(self.config_path)
            if not config_path.exists():
                logger.warning(f"Tool dependency config not found at {self.config_path}")
                self._create_default_config()
                return
                
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            # Parse tool dependency configuration
            for tool_config in config.get('tools', []):
                tool_id = tool_config.get('id')
                if not tool_id:
                    continue
                
                dependencies = []
                for dep_config in tool_config.get('dependencies', []):
                    if 'name' not in dep_config:
                        continue
                        
                    dependencies.append(ToolDependency(
                        name=dep_config['name'],
                        type=dep_config.get('type', DependencyType.REQUIRED),
                        min_version=dep_config.get('min_version'),
                        max_version=dep_config.get('max_version'),
                        module_path=dep_config.get('module_path'),
                        binary_name=dep_config.get('binary_name'),
                        check_command=dep_config.get('check_command'),
                        fallback=dep_config.get('fallback')
                    ))
                
                self.tool_dependencies[tool_id] = dependencies
                
            logger.info(f"Loaded tool dependency config with {len(self.tool_dependencies)} tools")
        except Exception as e:
            logger.error(f"Error loading tool dependency config: {e}")
            self._create_default_config()
            
    def _create_default_config(self):
        """
        Creates and writes a default tool dependency configuration file if none exists.
        
        Initializes the tool dependency mapping with predefined tools and their dependencies,
        writes the configuration to the specified path, and loads it into the manager. If an
        error occurs during creation or loading, logs the error.
        """
        default_config = {
            'tools': [
                {
                    'id': 'web_search',
                    'dependencies': [
                        {
                            'name': 'requests',
                            'type': 'required',
                            'module_path': 'requests'
                        },
                        {
                            'name': 'beautifulsoup4',
                            'type': 'enhanced',
                            'module_path': 'bs4'
                        }
                    ]
                },
                {
                    'id': 'code_execution',
                    'dependencies': [
                        {
                            'name': 'python',
                            'type': 'required',
                            'min_version': '3.8',
                            'check_command': 'python --version'
                        }
                    ]
                },
                {
                    'id': 'github_tool',
                    'dependencies': [
                        {
                            'name': 'PyGithub',
                            'type': 'required',
                            'module_path': 'github'
                        }
                    ]
                },
                {
                    'id': 'puppeteer',
                    'dependencies': [
                        {
                            'name': 'nodejs',
                            'type': 'required',
                            'check_command': 'node --version',
                            'min_version': '14.0.0'
                        },
                        {
                            'name': 'puppeteer',
                            'type': 'required',
                            'check_command': 'npx puppeteer --version',
                            'min_version': '13.0.0'
                        }
                    ]
                }
            ]
        }
        
        try:
            config_path = Path(self.config_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                yaml.dump(default_config, f)
                
            logger.info(f"Created default tool dependency config at {self.config_path}")
            
            # Load the default config
            for tool_config in default_config.get('tools', []):
                tool_id = tool_config.get('id')
                if not tool_id:
                    continue
                
                dependencies = []
                for dep_config in tool_config.get('dependencies', []):
                    if 'name' not in dep_config:
                        continue
                        
                    dependencies.append(ToolDependency(
                        name=dep_config['name'],
                        type=dep_config.get('type', DependencyType.REQUIRED),
                        min_version=dep_config.get('min_version'),
                        max_version=dep_config.get('max_version'),
                        module_path=dep_config.get('module_path'),
                        binary_name=dep_config.get('binary_name'),
                        check_command=dep_config.get('check_command'),
                        fallback=dep_config.get('fallback')
                    ))
                
                self.tool_dependencies[tool_id] = dependencies
        except Exception as e:
            logger.error(f"Error creating default tool dependency config: {e}")
    
    def check_dependency_status(self, dependency: ToolDependency) -> DependencyStatus:
        """
        Determines the status of a single tool dependency.
        
        Checks whether the specified dependency is present and meets version constraints, either by importing a Python module or executing a command for a binary. Returns the dependency's status as satisfied, missing, version mismatch, or unknown.
        	
        Args:
        	dependency: The tool dependency to verify.
        
        Returns:
        	The status of the dependency as a DependencyStatus value.
        """
        # Check Python module dependency
        if dependency.module_path:
            try:
                # Try to import the module
                spec = importlib.util.find_spec(dependency.module_path)
                if spec is None:
                    return DependencyStatus.MISSING
                
                # Check version if specified
                if dependency.min_version or dependency.max_version:
                    try:
                        module = importlib.import_module(dependency.module_path)
                        version = getattr(module, "__version__", None)
                        if not version:
                            version = getattr(module, "version", None)
                        
                        if not version:
                            logger.warning(f"Could not determine version for module {dependency.module_path}")
                            return DependencyStatus.UNKNOWN
                        
                        # Check version constraints
                        if dependency.min_version and version < dependency.min_version:
                            return DependencyStatus.VERSION_MISMATCH
                        if dependency.max_version and version > dependency.max_version:
                            return DependencyStatus.VERSION_MISMATCH
                    except Exception as e:
                        logger.warning(f"Error checking version for {dependency.name}: {e}")
                        return DependencyStatus.UNKNOWN
                
                return DependencyStatus.SATISFIED
            except Exception as e:
                logger.warning(f"Error importing {dependency.module_path}: {e}")
                return DependencyStatus.MISSING
        
        # Check binary dependency with command
        if dependency.check_command:
            try:
                import subprocess
                result = subprocess.run(
                    dependency.check_command,
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    return DependencyStatus.MISSING
                
                # Parse version from command output if needed
                if dependency.min_version or dependency.max_version:
                    output = result.stdout.strip()
                    # Very basic version extraction - would need more sophisticated
                    # parsing for real applications
                    import re
                    version_match = re.search(r'\d+(\.\d+)+', output)
                    if not version_match:
                        logger.warning(f"Could not extract version from output: {output}")
                        return DependencyStatus.UNKNOWN
                    
                    version = version_match.group(0)
                    
                    # Check version constraints
                    if dependency.min_version and version < dependency.min_version:
                        return DependencyStatus.VERSION_MISMATCH
                    if dependency.max_version and version > dependency.max_version:
                        return DependencyStatus.VERSION_MISMATCH
                
                return DependencyStatus.SATISFIED
            except Exception as e:
                logger.warning(f"Error checking binary {dependency.name}: {e}")
                return DependencyStatus.MISSING
        
        # If no specific checks, assume it's satisfied
        logger.warning(f"No check method specified for dependency {dependency.name}")
        return DependencyStatus.UNKNOWN
    
    def check_tool_dependencies(self, tool_id: str) -> Dict[str, DependencyStatus]:
        """
        Checks and returns the status of all dependencies for a specified tool.
        
        For each dependency, determines if it is satisfied, missing, or has a version mismatch. If a dependency is unsatisfied and a fallback is defined, checks the fallback and uses it if satisfied. Results are cached for subsequent calls.
        
        Args:
            tool_id: The identifier of the tool whose dependencies are to be checked.
        
        Returns:
            A dictionary mapping dependency names to their status for the specified tool.
        """
        # Return from cache if available
        if tool_id in self.dependency_status_cache:
            return self.dependency_status_cache[tool_id]
        
        # Check if tool has registered dependencies
        if tool_id not in self.tool_dependencies:
            logger.warning(f"No dependencies registered for tool {tool_id}")
            return {}
        
        # Check each dependency
        result = {}
        for dependency in self.tool_dependencies[tool_id]:
            status = self.check_dependency_status(dependency)
            result[dependency.name] = status
            
            # If this dependency is missing but has a fallback, check the fallback
            if status in [DependencyStatus.MISSING, DependencyStatus.VERSION_MISMATCH] and dependency.fallback:
                fallback_dependencies = [d for d in self.tool_dependencies[tool_id] 
                                      if d.name == dependency.fallback]
                if fallback_dependencies:
                    fallback_status = self.check_dependency_status(fallback_dependencies[0])
                    if fallback_status == DependencyStatus.SATISFIED:
                        # Indicate that we'll use the fallback
                        result[dependency.name] = DependencyStatus.SATISFIED
                        logger.info(f"Using fallback {dependency.fallback} for {dependency.name}")
        
        # Cache the results
        self.dependency_status_cache[tool_id] = result
        return result
    
    def can_tool_run(self, tool_id: str) -> Tuple[bool, Optional[str]]:
        """
        Determines whether a tool can run based on the status of its required dependencies.
        
        Checks all dependencies for the specified tool and returns a tuple indicating if the tool can run. If any required dependencies are missing or not satisfied, returns False and a reason listing the missing dependencies; otherwise, returns True and None.
        
        Args:
            tool_id: The identifier of the tool to check.
        
        Returns:
            A tuple (can_run, reason), where can_run is True if the tool can run, and reason is a string describing missing required dependencies if it cannot.
        """
        # If no dependencies are registered, assume it can run
        if tool_id not in self.tool_dependencies:
            return True, None
        
        # Check all dependencies
        dependency_status = self.check_tool_dependencies(tool_id)
        
        # Check if any required dependencies are missing
        missing_required = []
        for dependency in self.tool_dependencies[tool_id]:
            status = dependency_status.get(dependency.name)
            if dependency.type == DependencyType.REQUIRED and status != DependencyStatus.SATISFIED:
                missing_required.append(dependency.name)
        
        if missing_required:
            return False, f"Missing required dependencies: {', '.join(missing_required)}"
        
        return True, None
    
    def get_limited_functionality(self, tool_id: str) -> List[str]:
        """
        Returns a list of missing optional or enhanced dependencies for a tool.
        
        Args:
            tool_id: The identifier of the tool to check.
        
        Returns:
            A list of dependency names that are optional or enhanced and are not satisfied, indicating limited functionality for the tool.
        """
        # If no dependencies are registered, return empty list
        if tool_id not in self.tool_dependencies:
            return []
        
        # Check all dependencies
        dependency_status = self.check_tool_dependencies(tool_id)
        
        # Check which optional or enhanced dependencies are missing
        missing_optional = []
        for dependency in self.tool_dependencies[tool_id]:
            status = dependency_status.get(dependency.name)
            if dependency.type in [DependencyType.OPTIONAL, DependencyType.ENHANCED] and status != DependencyStatus.SATISFIED:
                missing_optional.append(dependency.name)
        
        return missing_optional
    
    def verify_tools_availability(self, tool_ids: List[str]) -> Dict[str, bool]:
        """
        Checks the availability of multiple tools based on their dependency status.
        
        Args:
            tool_ids: List of tool identifiers to check.
        
        Returns:
            A dictionary mapping each tool ID to a boolean indicating whether the tool can run.
        """
        result = {}
        for tool_id in tool_ids:
            can_run, _ = self.can_tool_run(tool_id)
            result[tool_id] = can_run
        return result
    
    def get_dependency_report(self) -> Dict[str, Any]:
        """
        Generates a detailed report of dependency statuses for all registered tools.
        
        The report includes, for each tool, whether it can run, the reason if not, and the status of each dependency. It also aggregates lists of missing required dependencies, missing optional dependencies, and dependencies with version mismatches across all tools.
        
        Returns:
            A dictionary containing per-tool dependency statuses, missing required and optional dependencies, and version mismatches.
        """
        report = {
            "tools": {},
            "missing_required": [],
            "missing_optional": [],
            "version_mismatches": []
        }
        
        for tool_id, dependencies in self.tool_dependencies.items():
            # Check dependencies for this tool
            dependency_status = self.check_tool_dependencies(tool_id)
            can_run, reason = self.can_tool_run(tool_id)
            
            tool_report = {
                "can_run": can_run,
                "reason": reason,
                "dependencies": dependency_status
            }
            
            report["tools"][tool_id] = tool_report
            
            # Add to summary lists
            for dependency in dependencies:
                status = dependency_status.get(dependency.name)
                if status == DependencyStatus.MISSING:
                    if dependency.type == DependencyType.REQUIRED:
                        report["missing_required"].append({
                            "tool": tool_id,
                            "dependency": dependency.name
                        })
                    else:
                        report["missing_optional"].append({
                            "tool": tool_id,
                            "dependency": dependency.name
                        })
                elif status == DependencyStatus.VERSION_MISMATCH:
                    report["version_mismatches"].append({
                        "tool": tool_id,
                        "dependency": dependency.name,
                        "min_version": dependency.min_version,
                        "max_version": dependency.max_version
                    })
        
        return report
    
    def clear_cache(self):
        """
        Clears the cached dependency status results.
        
        Removes all entries from the internal cache, forcing fresh dependency checks on subsequent operations.
        """
        self.dependency_status_cache.clear()

# Global instance for application-wide use
tool_dependency_manager = ToolDependencyManager()