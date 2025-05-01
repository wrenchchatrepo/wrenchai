"""State variable management for workflow execution.

This module provides a structured approach to managing state variables during workflow execution,
with support for variable definition, validation, type information, and persistence.

Key components:
- StateVariable: Defines variables with metadata, validation, and type information
- StateManager: Manages state variables throughout workflow execution
- Persistence mechanisms to save/load state
- Debug utilities for state introspection
"""

import json
import logging
from typing import Any, Dict, List, Optional, Set, Type, Union, Callable, TypeVar
from datetime import datetime
from enum import Enum
from pathlib import Path
import os
import threading
import copy
import inspect
from pydantic import BaseModel, Field, ValidationError, create_model
from dataclasses import dataclass

logger = logging.getLogger(__name__)

T = TypeVar('T')

class StateScope(str, Enum):
    """Scope of a state variable."""
    LOCAL = "local"        # Only accessible in current node/step
    WORKFLOW = "workflow"  # Accessible throughout workflow
    GLOBAL = "global"      # Accessible across all workflows
    

class StatePermission(str, Enum):
    """Permission level for state variable access."""
    READ_ONLY = "read_only"      # Can only be read after initialization
    READ_WRITE = "read_write"    # Can be read and written
    PRIVATE = "private"          # Only accessible to the owner
    SHARED = "shared"            # Accessible to specified components
    PROTECTED = "protected"      # Accessible to components with access control


class StateVariableMeta(BaseModel):
    """Metadata for a state variable."""
    name: str = Field(..., description="Name of the variable")
    description: str = Field("", description="Description of the variable and its purpose")
    scope: StateScope = Field(StateScope.WORKFLOW, description="Scope of the variable")
    permission: StatePermission = Field(StatePermission.READ_WRITE, description="Permission level for the variable")
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing the variable")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the variable was created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="When the variable was last updated")
    owner: Optional[str] = Field(None, description="ID of the component that owns the variable")
    access_list: List[str] = Field(default_factory=list, description="List of component IDs that can access the variable")
    ttl: Optional[int] = Field(None, description="Time-to-live in seconds (None for no expiration)")
    
    def update_timestamp(self):
        """Update the last updated timestamp."""
        self.updated_at = datetime.utcnow()


class StateVariable(Generic[T]):
    """Defines a state variable with metadata, validation, and type information."""
    
    def __init__(
        self,
        name: str,
        value: T = None,
        default: T = None,
        description: str = "",
        scope: StateScope = StateScope.WORKFLOW,
        permission: StatePermission = StatePermission.READ_WRITE,
        validator: Optional[Callable[[T], bool]] = None,
        value_type: Optional[Type] = None,
        tags: List[str] = None,
        owner: Optional[str] = None,
        access_list: List[str] = None,
        ttl: Optional[int] = None,
    ):
        """Initialize a state variable.
        
        Args:
            name: Name of the variable
            value: Initial value of the variable
            default: Default value if none provided
            description: Description of the variable and its purpose
            scope: Scope of the variable
            permission: Permission level for the variable
            validator: Function to validate values
            value_type: Type annotation for the variable
            tags: Tags for categorizing the variable
            owner: ID of the component that owns the variable
            access_list: List of component IDs that can access the variable
            ttl: Time-to-live in seconds (None for no expiration)
        """
        self.metadata = StateVariableMeta(
            name=name,
            description=description,
            scope=scope,
            permission=permission,
            tags=tags or [],
            owner=owner,
            access_list=access_list or [],
            ttl=ttl,
        )
        self._value = None
        self._default = default
        self._validator = validator
        self._value_type = value_type or type(value) if value is not None else type(default) if default is not None else Any
        
        # Set the initial value if provided
        if value is not None:
            self.value = value
        elif default is not None:
            self.value = copy.deepcopy(default)
    
    @property
    def value(self) -> T:
        """Get the variable value.
        
        Returns:
            The variable value
        """
        if self._value is None and self._default is not None:
            return copy.deepcopy(self._default)
        return self._value
    
    @value.setter
    def value(self, new_value: T):
        """Set the variable value with validation.
        
        Args:
            new_value: The new value to set
            
        Raises:
            ValueError: If the value fails validation
            TypeError: If the value has the wrong type
        """
        # Validate type if specified
        if self._value_type is not Any and not isinstance(new_value, self._value_type):
            raise TypeError(f"Value must be of type {self._value_type.__name__}, got {type(new_value).__name__}")
        
        # Apply validator if specified
        if self._validator is not None and not self._validator(new_value):
            raise ValueError(f"Value failed validation for {self.metadata.name}")
        
        # Update the value and timestamp
        self._value = new_value
        self.metadata.update_timestamp()
    
    @property
    def name(self) -> str:
        """Get the variable name.
        
        Returns:
            The variable name
        """
        return self.metadata.name
    
    def reset(self):
        """Reset the variable to its default value."""
        if self._default is not None:
            self._value = copy.deepcopy(self._default)
        else:
            self._value = None
        self.metadata.update_timestamp()
    
    def is_expired(self) -> bool:
        """Check if the variable has expired.
        
        Returns:
            True if the variable has expired, False otherwise
        """
        if self.metadata.ttl is None:
            return False
        
        age = (datetime.utcnow() - self.metadata.updated_at).total_seconds()
        return age > self.metadata.ttl
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the variable to a dictionary for persistence.
        
        Returns:
            Dictionary representation of the variable
        """
        return {
            "metadata": self.metadata.dict(),
            "value": self._value,
            "default": self._default,
            "value_type": self._value_type.__name__ if hasattr(self._value_type, "__name__") else str(self._value_type),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateVariable':
        """Create a state variable from a dictionary.
        
        Args:
            data: Dictionary representation of the variable
            
        Returns:
            StateVariable instance
        """
        # Create a variable with metadata
        metadata = StateVariableMeta(**data["metadata"])
        variable = cls(
            name=metadata.name,
            description=metadata.description,
            scope=metadata.scope,
            permission=metadata.permission,
            tags=metadata.tags,
            owner=metadata.owner,
            access_list=metadata.access_list,
            ttl=metadata.ttl,
        )
        
        # Set additional properties
        variable.metadata = metadata
        variable._value = data["value"]
        variable._default = data["default"]
        
        # Try to resolve the value type
        type_name = data["value_type"]
        try:
            if type_name in ("Any", "<class 'typing.Any'>"):
                variable._value_type = Any
            else:
                # Try to resolve basic types
                basic_types = {
                    "str": str,
                    "int": int, 
                    "float": float,
                    "bool": bool,
                    "dict": dict,
                    "list": list,
                    "tuple": tuple,
                    "set": set,
                    "NoneType": type(None),
                }
                variable._value_type = basic_types.get(type_name, Any)
        except (ValueError, AttributeError):
            variable._value_type = Any
        
        return variable
    
    def __repr__(self) -> str:
        """Get a string representation of the variable.
        
        Returns:
            String representation
        """
        return f"StateVariable(name={self.metadata.name}, type={self._value_type.__name__ if hasattr(self._value_type, '__name__') else str(self._value_type)}, value={self._value})"


class StateGroup(BaseModel):
    """A group of related state variables."""
    name: str
    description: str = ""
    variables: Dict[str, StateVariable] = Field(default_factory=dict)

    def add_variable(self, variable: StateVariable):
        """Add a variable to the group.
        
        Args:
            variable: The variable to add
        """
        self.variables[variable.name] = variable
    
    def get_variable(self, name: str) -> Optional[StateVariable]:
        """Get a variable from the group.
        
        Args:
            name: The name of the variable
            
        Returns:
            The variable or None if not found
        """
        return self.variables.get(name)
    
    def remove_variable(self, name: str) -> bool:
        """Remove a variable from the group.
        
        Args:
            name: The name of the variable
            
        Returns:
            True if the variable was removed, False if it wasn't found
        """
        if name in self.variables:
            del self.variables[name]
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the group to a dictionary for persistence.
        
        Returns:
            Dictionary representation of the group
        """
        return {
            "name": self.name,
            "description": self.description,
            "variables": {name: var.to_dict() for name, var in self.variables.items()},
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateGroup':
        """Create a state group from a dictionary.
        
        Args:
            data: Dictionary representation of the group
            
        Returns:
            StateGroup instance
        """
        group = cls(name=data["name"], description=data["description"])
        for name, var_data in data["variables"].items():
            group.variables[name] = StateVariable.from_dict(var_data)
        return group


class StateNotFoundError(Exception):
    """Exception raised when a state variable is not found."""
    pass


class StateAccessError(Exception):
    """Exception raised when a state variable cannot be accessed due to permissions."""
    pass


class StateValidationError(Exception):
    """Exception raised when a state variable value fails validation."""
    pass


class StateChangeEvent(BaseModel):
    """Event model for state changes."""
    variable_name: str
    old_value: Any = None
    new_value: Any = None
    changed_by: str = "system"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StateManager:
    """Manages state variables for workflow execution."""
    
    def __init__(self, persistence_dir: Optional[str] = None):
        """Initialize the state manager.
        
        Args:
            persistence_dir: Directory for state persistence (optional)
        """
        self._variables: Dict[str, StateVariable] = {}
        self._groups: Dict[str, StateGroup] = {}
        self._hooks: Dict[str, List[Callable]] = {
            "pre_change": [],
            "post_change": [],
            "validation": [],
        }
        self._change_history: List[StateChangeEvent] = []
        self._persistence_dir = persistence_dir or os.path.join("data", "state")
        self._lock = threading.RLock()
        
        # Set up persistence directory
        if self._persistence_dir:
            os.makedirs(self._persistence_dir, exist_ok=True)

    def register_variable(self, variable: StateVariable) -> StateVariable:
        """Register a variable with the state manager.
        
        Args:
            variable: The variable to register
            
        Returns:
            The registered variable
            
        Raises:
            ValueError: If a variable with the same name already exists
        """
        with self._lock:
            if variable.name in self._variables:
                raise ValueError(f"Variable '{variable.name}' already exists")
            
            self._variables[variable.name] = variable
            return variable
    
    def register_variables(self, variables: List[StateVariable]) -> List[StateVariable]:
        """Register multiple variables with the state manager.
        
        Args:
            variables: The variables to register
            
        Returns:
            The registered variables
            
        Raises:
            ValueError: If any variable name already exists
        """
        registered = []
        for variable in variables:
            registered.append(self.register_variable(variable))
        return registered
    
    def register_group(self, group: StateGroup) -> StateGroup:
        """Register a group with the state manager.
        
        Args:
            group: The group to register
            
        Returns:
            The registered group
            
        Raises:
            ValueError: If a group with the same name already exists
        """
        with self._lock:
            if group.name in self._groups:
                raise ValueError(f"Group '{group.name}' already exists")
            
            self._groups[group.name] = group
            
            # Register all variables in the group
            for variable in group.variables.values():
                if variable.name not in self._variables:
                    self._variables[variable.name] = variable
            
            return group
    
    def create_variable(
        self,
        name: str,
        value: Any = None,
        default: Any = None,
        description: str = "",
        scope: StateScope = StateScope.WORKFLOW,
        permission: StatePermission = StatePermission.READ_WRITE,
        validator: Optional[Callable[[Any], bool]] = None,
        value_type: Optional[Type] = None,
        tags: List[str] = None,
        owner: Optional[str] = None,
        access_list: List[str] = None,
        ttl: Optional[int] = None,
    ) -> StateVariable:
        """Create and register a new variable.
        
        Args:
            name: Name of the variable
            value: Initial value of the variable
            default: Default value if none provided
            description: Description of the variable and its purpose
            scope: Scope of the variable
            permission: Permission level for the variable
            validator: Function to validate values
            value_type: Type annotation for the variable
            tags: Tags for categorizing the variable
            owner: ID of the component that owns the variable
            access_list: List of component IDs that can access the variable
            ttl: Time-to-live in seconds (None for no expiration)
            
        Returns:
            The created variable
            
        Raises:
            ValueError: If a variable with the same name already exists
        """
        variable = StateVariable(
            name=name,
            value=value,
            default=default,
            description=description,
            scope=scope,
            permission=permission,
            validator=validator,
            value_type=value_type,
            tags=tags,
            owner=owner,
            access_list=access_list,
            ttl=ttl,
        )
        
        return self.register_variable(variable)
    
    def create_group(self, name: str, description: str = "") -> StateGroup:
        """Create and register a new group.
        
        Args:
            name: Name of the group
            description: Description of the group
            
        Returns:
            The created group
            
        Raises:
            ValueError: If a group with the same name already exists
        """
        group = StateGroup(name=name, description=description)
        return self.register_group(group)

    def get_variable(self, name: str) -> StateVariable:
        """Get a variable by name.
        
        Args:
            name: Name of the variable
            
        Returns:
            The variable
            
        Raises:
            StateNotFoundError: If the variable is not found
        """
        with self._lock:
            if name not in self._variables or self._variables[name].is_expired():
                raise StateNotFoundError(f"Variable '{name}' not found or expired")
            
            return self._variables[name]
    
    def get_variable_value(self, name: str, default: Any = None) -> Any:
        """Get a variable's value by name.
        
        Args:
            name: Name of the variable
            default: Default value to return if the variable is not found
            
        Returns:
            The variable value or default if not found
        """
        try:
            return self.get_variable(name).value
        except StateNotFoundError:
            return default
    
    def set_variable_value(self, name: str, value: Any, requestor: str = "system") -> bool:
        """Set a variable's value by name.
        
        Args:
            name: Name of the variable
            value: New value for the variable
            requestor: ID of the component requesting the change
            
        Returns:
            True if the value was set, False otherwise
            
        Raises:
            StateNotFoundError: If the variable is not found
            StateAccessError: If the variable cannot be modified
            StateValidationError: If the value fails validation
        """
        with self._lock:
            # Check if variable exists
            if name not in self._variables:
                raise StateNotFoundError(f"Variable '{name}' not found")
            
            variable = self._variables[name]
            
            # Check if expired
            if variable.is_expired():
                raise StateNotFoundError(f"Variable '{name}' has expired")
            
            # Check permissions
            if variable.metadata.permission == StatePermission.READ_ONLY:
                raise StateAccessError(f"Variable '{name}' is read-only")
            
            if variable.metadata.permission == StatePermission.PRIVATE and variable.metadata.owner != requestor:
                raise StateAccessError(f"Variable '{name}' is private to {variable.metadata.owner}")
            
            if (variable.metadata.permission == StatePermission.PROTECTED and 
                variable.metadata.owner != requestor and 
                requestor not in variable.metadata.access_list):
                raise StateAccessError(f"Variable '{name}' is protected and {requestor} does not have access")
            
            # Pre-change hooks
            old_value = variable.value
            for hook in self._hooks["pre_change"]:
                hook(name, old_value, value, requestor)
            
            try:
                # Validation hooks
                for hook in self._hooks["validation"]:
                    if not hook(name, value, requestor):
                        raise StateValidationError(f"Value failed validation hook for '{name}'")
                
                # Set the value
                variable.value = value
                
                # Record change
                event = StateChangeEvent(
                    variable_name=name,
                    old_value=old_value,
                    new_value=value,
                    changed_by=requestor,
                )
                self._change_history.append(event)
                
                # Post-change hooks
                for hook in self._hooks["post_change"]:
                    hook(name, old_value, value, requestor)
                
                return True
            except (ValueError, TypeError) as e:
                raise StateValidationError(f"Invalid value for '{name}': {str(e)}")
    
    def delete_variable(self, name: str, requestor: str = "system") -> bool:
        """Delete a variable.
        
        Args:
            name: Name of the variable
            requestor: ID of the component requesting the deletion
            
        Returns:
            True if the variable was deleted, False otherwise
            
        Raises:
            StateAccessError: If the variable cannot be deleted
        """
        with self._lock:
            if name not in self._variables:
                return False
            
            variable = self._variables[name]
            
            # Check permissions
            if (variable.metadata.permission in [StatePermission.PRIVATE, StatePermission.PROTECTED] and 
                variable.metadata.owner != requestor):
                raise StateAccessError(f"Variable '{name}' cannot be deleted by {requestor}")
            
            # Remove from all groups
            for group in self._groups.values():
                group.remove_variable(name)
            
            # Remove the variable
            del self._variables[name]
            
            return True
    
    def get_group(self, name: str) -> StateGroup:
        """Get a group by name.
        
        Args:
            name: Name of the group
            
        Returns:
            The group
            
        Raises:
            StateNotFoundError: If the group is not found
        """
        with self._lock:
            if name not in self._groups:
                raise StateNotFoundError(f"Group '{name}' not found")
            
            return self._groups[name]
    
    def add_variable_to_group(self, variable_name: str, group_name: str) -> bool:
        """Add a variable to a group.
        
        Args:
            variable_name: Name of the variable
            group_name: Name of the group
            
        Returns:
            True if the variable was added, False otherwise
            
        Raises:
            StateNotFoundError: If the variable or group is not found
        """
        with self._lock:
            if variable_name not in self._variables:
                raise StateNotFoundError(f"Variable '{variable_name}' not found")
            
            if group_name not in self._groups:
                raise StateNotFoundError(f"Group '{group_name}' not found")
            
            self._groups[group_name].add_variable(self._variables[variable_name])
            return True
    
    def add_hook(self, hook_type: str, hook: Callable) -> bool:
        """Add a hook function.
        
        Args:
            hook_type: Type of hook (pre_change, post_change, validation)
            hook: Hook function to add
            
        Returns:
            True if the hook was added, False otherwise
        """
        with self._lock:
            if hook_type not in self._hooks:
                return False
            
            self._hooks[hook_type].append(hook)
            return True
    
    def remove_hook(self, hook_type: str, hook: Callable) -> bool:
        """Remove a hook function.
        
        Args:
            hook_type: Type of hook (pre_change, post_change, validation)
            hook: Hook function to remove
            
        Returns:
            True if the hook was removed, False otherwise
        """
        with self._lock:
            if hook_type not in self._hooks:
                return False
            
            if hook in self._hooks[hook_type]:
                self._hooks[hook_type].remove(hook)
                return True
            
            return False
    
    def get_change_history(self, variable_name: Optional[str] = None, limit: int = 100) -> List[StateChangeEvent]:
        """Get the change history for a variable.
        
        Args:
            variable_name: Name of the variable (None for all variables)
            limit: Maximum number of events to return
            
        Returns:
            List of change events
        """
        with self._lock:
            if variable_name is None:
                history = self._change_history
            else:
                history = [event for event in self._change_history if event.variable_name == variable_name]
            
            # Return most recent events first
            return sorted(history, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def clear_history(self):
        """Clear the change history."""
        with self._lock:
            self._change_history.clear()
    
    def save_state(self, filename: Optional[str] = None):
        """Save the state to a file.
        
        Args:
            filename: Name of the file to save to (default: 'state.json')
        """
        if not self._persistence_dir:
            return
        
        with self._lock:
            filename = filename or "state.json"
            filepath = os.path.join(self._persistence_dir, filename)
            
            data = {
                "variables": {name: var.to_dict() for name, var in self._variables.items()},
                "groups": {name: group.to_dict() for name, group in self._groups.items()},
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            try:
                with open(filepath, 'w') as f:
                    json.dump(data, f, default=str, indent=2)
                logger.info(f"State saved to {filepath}")
            except Exception as e:
                logger.error(f"Error saving state to {filepath}: {e}")
    
    def load_state(self, filename: Optional[str] = None):
        """Load the state from a file.
        
        Args:
            filename: Name of the file to load from (default: 'state.json')
            
        Returns:
            True if the state was loaded, False otherwise
        """
        if not self._persistence_dir:
            return False
        
        with self._lock:
            filename = filename or "state.json"
            filepath = os.path.join(self._persistence_dir, filename)
            
            if not os.path.exists(filepath):
                logger.warning(f"State file {filepath} not found")
                return False
            
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                # Clear existing state
                self._variables.clear()
                self._groups.clear()
                
                # Load variables
                for name, var_data in data["variables"].items():
                    self._variables[name] = StateVariable.from_dict(var_data)
                
                # Load groups
                for name, group_data in data["groups"].items():
                    self._groups[name] = StateGroup.from_dict(group_data)
                
                logger.info(f"State loaded from {filepath}")
                return True
            except Exception as e:
                logger.error(f"Error loading state from {filepath}: {e}")
                return False
    
    def get_variables_by_tag(self, tag: str) -> List[StateVariable]:
        """Get variables by tag.
        
        Args:
            tag: Tag to filter by
            
        Returns:
            List of variables with the tag
        """
        with self._lock:
            return [var for var in self._variables.values() if tag in var.metadata.tags]
    
    def get_variables_by_scope(self, scope: StateScope) -> List[StateVariable]:
        """Get variables by scope.
        
        Args:
            scope: Scope to filter by
            
        Returns:
            List of variables with the scope
        """
        with self._lock:
            return [var for var in self._variables.values() if var.metadata.scope == scope]
    
    def get_variables_by_owner(self, owner: str) -> List[StateVariable]:
        """Get variables by owner.
        
        Args:
            owner: Owner to filter by
            
        Returns:
            List of variables with the owner
        """
        with self._lock:
            return [var for var in self._variables.values() if var.metadata.owner == owner]
    
    def debug_info(self) -> Dict[str, Any]:
        """Get debug information about the state manager.
        
        Returns:
            Dictionary of debug information
        """
        with self._lock:
            return {
                "variable_count": len(self._variables),
                "group_count": len(self._groups),
                "variables": {name: {
                    "type": str(var._value_type),
                    "scope": var.metadata.scope,
                    "permission": var.metadata.permission,
                    "last_updated": var.metadata.updated_at.isoformat(),
                    "has_value": var.value is not None
                } for name, var in self._variables.items()},
                "groups": {name: {
                    "description": group.description,
                    "variable_count": len(group.variables)
                } for name, group in self._groups.items()},
                "hook_counts": {name: len(hooks) for name, hooks in self._hooks.items()},
                "change_history_count": len(self._change_history),
            }
    
    def create_state_schema(self) -> Type[BaseModel]:
        """Create a Pydantic model representing the current state schema.
        
        Returns:
            A Pydantic model class for the current state
        """
        with self._lock:
            fields = {}
            for name, var in self._variables.items():
                # Use Any for complex types
                field_type = var._value_type if var._value_type not in (dict, list, tuple, set) else Any
                
                fields[name] = (
                    Optional[field_type] if var.value is None else field_type, 
                    Field(
                        default=var.value if var.value is not None else None,
                        description=var.metadata.description
                    )
                )
            
            return create_model('StateSchema', **fields)
    
    def export_state_to_dict(self) -> Dict[str, Any]:
        """Export the current state as a simple dictionary.
        
        Returns:
            Dictionary representation of the current state values
        """
        with self._lock:
            return {name: var.value for name, var in self._variables.items() if var.value is not None}
    
    def __repr__(self) -> str:
        """Get a string representation of the state manager.
        
        Returns:
            String representation
        """
        return f"StateManager(variables={len(self._variables)}, groups={len(self._groups)})"


# Create a global instance for convenience
state_manager = StateManager()