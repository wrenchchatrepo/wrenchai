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
        Initializes the ToolDependencyManager with tool dependency configurations.
        
        If a configuration file path is provided, loads dependencies from that file; otherwise, uses the default configuration path. Initializes internal structures for managing tool dependencies and their statuses.
        """
        self.tool_dependencies: Dict[str, List[ToolDependency]] = {}
        self.dependency_status_cache: Dict[str, Dict[str, DependencyStatus]] = {}
        self.config_path = config_path or os.path.join("core", "configs", "tool_dependencies.yaml")
        self._load_configuration()
        
    def _load_configuration(self):
        """
        Loads tool dependency configuration from the specified YAML file.
        
        If the configuration file does not exist or an error occurs during loading,
        a default configuration is created instead. Parsed dependencies are stored
        internally for each tool.
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
        
        Initializes the internal tool dependency mapping with predefined sample tools and their dependencies. Logs an error if the configuration file cannot be created.
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
        Determines the availability and version compatibility of a single tool dependency.
        
        Checks whether the specified dependency is present and, if applicable, whether its version meets the defined constraints. Supports both Python module and binary dependencies. Returns the appropriate status based on the outcome of the checks.
        
        Args:
        	dependency: The dependency to verify.
        
        Returns:
        	A DependencyStatus indicating if the dependency is satisfied, missing, has a version mismatch, or is unknown.
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
        
        For each dependency, determines if it is satisfied, missing, or has a version mismatch. If a dependency is unsatisfied and a fallback is specified, checks the fallback and marks the dependency as satisfied if the fallback is available. Results are cached for subsequent calls.
        
        Args:
            tool_id: The identifier of the tool whose dependencies are to be checked.
        
        Returns:
            A dictionary mapping each dependency name to its status.
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
        Determines if a tool can run by verifying that all required dependencies are satisfied.
        
        Args:
            tool_id: The identifier of the tool to check.
        
        Returns:
            A tuple where the first element is True if the tool can run, False otherwise.
            The second element is a reason string if the tool cannot run, or None if it can.
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
        Returns a list of optional or enhanced dependencies that are missing for a given tool.
        
        Args:
            tool_id: The identifier of the tool to check.
        
        Returns:
            A list of dependency names representing missing optional or enhanced dependencies, indicating limited functionality for the tool.
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
        Checks the availability of multiple tools based on their dependency statuses.
        
        Args:
            tool_ids: List of tool identifiers to check.
        
        Returns:
            A dictionary mapping each tool ID to a boolean indicating whether all required dependencies are satisfied.
        """
        result = {}
        for tool_id in tool_ids:
            can_run, _ = self.can_tool_run(tool_id)
            result[tool_id] = can_run
        return result
    
    def get_dependency_report(self) -> Dict[str, Any]:
        """
        Generates a detailed report on the dependency status of all registered tools.
        
        Returns:
            A dictionary containing, for each tool, its ability to run, reasons for any failure,
            and the status of each dependency. Also includes aggregated lists of missing required
            dependencies, missing optional dependencies, and version mismatches across all tools.
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
        
        Removes all entries from the internal cache, forcing future dependency checks to re-evaluate statuses.
        """
        self.dependency_status_cache.clear()

# Global instance for application-wide use
tool_dependency_manager = ToolDependencyManager()