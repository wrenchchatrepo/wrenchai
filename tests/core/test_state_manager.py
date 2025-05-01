"""Tests for the State Manager module."""

import pytest
import os
import tempfile
from datetime import datetime, timedelta
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from core.state_manager import (
    StateManager, 
    StateVariable, 
    StateGroup,
    StateScope,
    StatePermission,
    StateNotFoundError,
    StateAccessError,
    StateValidationError
)

# Test basic variable creation and value access
def test_state_variable_creation():
    # Create a simple variable
    var = StateVariable(
        name="test_var",
        value="test_value",
        description="A test variable"
    )
    
    assert var.name == "test_var"
    assert var.value == "test_value"
    assert var.metadata.description == "A test variable"
    
    # Create a variable with a default value
    var_with_default = StateVariable(
        name="default_var",
        default="default_value"
    )
    
    assert var_with_default.value == "default_value"
    
    # Create a typed variable
    int_var = StateVariable(
        name="int_var",
        value=10,
        value_type=int
    )
    
    assert int_var.value == 10
    
    # Test validation
    with pytest.raises(TypeError):
        int_var.value = "not an int"

# Test variable validation with custom validator
def test_variable_custom_validation():
    # Create a variable with a custom validator
    def is_positive(value):
        return isinstance(value, int) and value > 0
    
    pos_var = StateVariable(
        name="positive_int",
        value=5,
        validator=is_positive
    )
    
    assert pos_var.value == 5
    
    # Try setting an invalid value
    with pytest.raises(ValueError):
        pos_var.value = -10
    
    # Set a valid value
    pos_var.value = 20
    assert pos_var.value == 20

# Test StateManager basic operations
def test_state_manager_basic():
    manager = StateManager()
    
    # Create a variable through the manager
    manager.create_variable(
        name="managed_var",
        value="managed_value",
        description="A managed variable"
    )
    
    # Get the variable
    var = manager.get_variable("managed_var")
    assert var.name == "managed_var"
    assert var.value == "managed_value"
    
    # Get the variable value directly
    value = manager.get_variable_value("managed_var")
    assert value == "managed_value"
    
    # Set a new value
    manager.set_variable_value("managed_var", "new_value")
    assert manager.get_variable_value("managed_var") == "new_value"
    
    # Try to get a non-existent variable
    with pytest.raises(StateNotFoundError):
        manager.get_variable("non_existent")
    
    # Get a non-existent variable with default
    assert manager.get_variable_value("non_existent", "default") == "default"

# Test variable grouping
def test_state_groups():
    manager = StateManager()
    
    # Create some variables
    var1 = manager.create_variable(name="var1", value="value1")
    var2 = manager.create_variable(name="var2", value="value2")
    var3 = manager.create_variable(name="var3", value="value3")
    
    # Create a group
    group = manager.create_group(name="test_group", description="Test group")
    
    # Add variables to the group
    manager.add_variable_to_group("var1", "test_group")
    manager.add_variable_to_group("var2", "test_group")
    
    # Get the group
    retrieved_group = manager.get_group("test_group")
    assert retrieved_group.name == "test_group"
    assert len(retrieved_group.variables) == 2
    assert "var1" in retrieved_group.variables
    assert "var2" in retrieved_group.variables
    assert "var3" not in retrieved_group.variables

# Test permission controls
def test_permission_controls():
    manager = StateManager()
    
    # Create variables with different permissions
    manager.create_variable(
        name="read_only_var",
        value="initial",
        permission=StatePermission.READ_ONLY
    )
    
    manager.create_variable(
        name="private_var",
        value="private",
        permission=StatePermission.PRIVATE,
        owner="owner1"
    )
    
    manager.create_variable(
        name="protected_var",
        value="protected",
        permission=StatePermission.PROTECTED,
        owner="owner1",
        access_list=["allowed_user"]
    )
    
    # Try to modify a read-only variable
    with pytest.raises(StateAccessError):
        manager.set_variable_value("read_only_var", "new_value")
    
    # Try to access a private variable
    with pytest.raises(StateAccessError):
        manager.set_variable_value("private_var", "new_value", requestor="not_owner")
    
    # Owner can modify their private variable
    manager.set_variable_value("private_var", "owner_change", requestor="owner1")
    assert manager.get_variable_value("private_var") == "owner_change"
    
    # Try to access a protected variable
    with pytest.raises(StateAccessError):
        manager.set_variable_value("protected_var", "new_value", requestor="not_allowed")
    
    # Allowed user can modify protected variable
    manager.set_variable_value("protected_var", "allowed_change", requestor="allowed_user")
    assert manager.get_variable_value("protected_var") == "allowed_change"

# Test time-to-live functionality
def test_variable_ttl():
    manager = StateManager()
    
    # Create a variable with a short TTL
    manager.create_variable(
        name="short_lived",
        value="temporary",
        ttl=1  # 1 second TTL
    )
    
    # Access immediately
    assert manager.get_variable_value("short_lived") == "temporary"
    
    # Wait for TTL to expire
    time.sleep(1.1)
    
    # Try to access after expiration
    with pytest.raises(StateNotFoundError):
        manager.get_variable("short_lived")
    
    # Default value should be returned for get_variable_value
    assert manager.get_variable_value("short_lived", "expired") == "expired"

# Test persistence
def test_state_persistence():
    # Use a temporary directory for persistence
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a manager with persistence
        manager1 = StateManager(persistence_dir=temp_dir)
        
        # Create some variables
        manager1.create_variable(name="persist_var1", value="value1")
        manager1.create_variable(name="persist_var2", value=42)
        
        # Create a group
        group = manager1.create_group(name="persist_group")
        manager1.add_variable_to_group("persist_var1", "persist_group")
        
        # Save the state
        manager1.save_state()
        
        # Create a new manager and load the state
        manager2 = StateManager(persistence_dir=temp_dir)
        assert manager2.load_state()
        
        # Check that variables were loaded
        assert manager2.get_variable_value("persist_var1") == "value1"
        assert manager2.get_variable_value("persist_var2") == 42
        
        # Check that the group was loaded
        group2 = manager2.get_group("persist_group")
        assert "persist_var1" in group2.variables

# Test state hooking
def test_state_hooks():
    manager = StateManager()
    
    # Create a variable
    manager.create_variable(name="hooked_var", value="initial")
    
    # Create hook trackers
    pre_change_calls = []
    post_change_calls = []
    validation_calls = []
    
    # Define hooks
    def pre_change_hook(name, old_value, new_value, requestor):
        pre_change_calls.append((name, old_value, new_value, requestor))
    
    def post_change_hook(name, old_value, new_value, requestor):
        post_change_calls.append((name, old_value, new_value, requestor))
    
    def validation_hook(name, value, requestor):
        validation_calls.append((name, value, requestor))
        # Reject values containing "invalid"
        return "invalid" not in str(value)
    
    # Register hooks
    manager.add_hook("pre_change", pre_change_hook)
    manager.add_hook("post_change", post_change_hook)
    manager.add_hook("validation", validation_hook)
    
    # Make a valid change
    manager.set_variable_value("hooked_var", "valid_value", requestor="test_user")
    
    # Check that hooks were called
    assert len(pre_change_calls) == 1
    assert pre_change_calls[0][0] == "hooked_var"  # name
    assert pre_change_calls[0][1] == "initial"     # old_value
    assert pre_change_calls[0][2] == "valid_value" # new_value
    assert pre_change_calls[0][3] == "test_user"   # requestor
    
    assert len(post_change_calls) == 1
    assert len(validation_calls) == 1
    
    # Try an invalid change
    with pytest.raises(StateValidationError):
        manager.set_variable_value("hooked_var", "invalid_value")
    
    # Check that only pre-change and validation hooks were called
    assert len(pre_change_calls) == 2
    assert len(validation_calls) == 2
    assert len(post_change_calls) == 1  # No change to post_change count
    
    # Current value should still be the valid one
    assert manager.get_variable_value("hooked_var") == "valid_value"

# Test change history
def test_change_history():
    manager = StateManager()
    
    # Create a variable
    manager.create_variable(name="tracked_var", value="initial")
    
    # Make some changes
    manager.set_variable_value("tracked_var", "value1", requestor="user1")
    manager.set_variable_value("tracked_var", "value2", requestor="user2")
    manager.set_variable_value("tracked_var", "value3", requestor="user1")
    
    # Get history
    history = manager.get_change_history("tracked_var")
    
    # Check history
    assert len(history) == 3
    assert history[0].variable_name == "tracked_var"
    assert history[0].new_value == "value3"
    assert history[0].changed_by == "user1"
    assert history[1].new_value == "value2"
    assert history[2].new_value == "value1"
    
    # Get limited history
    limited = manager.get_change_history("tracked_var", limit=2)
    assert len(limited) == 2
    assert limited[0].new_value == "value3"
    assert limited[1].new_value == "value2"
    
    # Clear history
    manager.clear_history()
    assert len(manager.get_change_history("tracked_var")) == 0

# Test Pydantic schema generation
def test_state_schema_generation():
    manager = StateManager()
    
    # Create some variables with different types
    manager.create_variable(name="string_var", value="string", description="A string")
    manager.create_variable(name="int_var", value=42, description="An integer")
    manager.create_variable(name="list_var", value=[1, 2, 3], description="A list")
    
    # Generate schema
    schema_model = manager.create_state_schema()
    
    # Check the model fields
    assert "string_var" in schema_model.__annotations__
    assert "int_var" in schema_model.__annotations__
    assert "list_var" in schema_model.__annotations__
    
    # Create an instance of the schema
    schema_instance = schema_model()
    assert schema_instance.string_var == "string"
    assert schema_instance.int_var == 42
    assert schema_instance.list_var == [1, 2, 3]

# Test integration with existing workflow system
def test_workflow_integration():
    manager = StateManager()
    
    # Simulate a workflow with state
    manager.create_variable(
        name="workflow_step",
        value="start",
        scope=StateScope.WORKFLOW
    )
    
    manager.create_variable(
        name="user_query",
        value="How do I integrate with the workflow?",
        scope=StateScope.WORKFLOW
    )
    
    manager.create_variable(
        name="context",
        value={"session_id": "123456"},
        scope=StateScope.WORKFLOW
    )
    
    # Update state as workflow progresses
    manager.set_variable_value("workflow_step", "processing")
    
    # Add to context
    context = manager.get_variable_value("context")
    context["start_time"] = datetime.utcnow().isoformat()
    manager.set_variable_value("context", context)
    
    # Check state
    assert manager.get_variable_value("workflow_step") == "processing"
    assert "start_time" in manager.get_variable_value("context")
    
    # Export state as dict
    state_dict = manager.export_state_to_dict()
    assert "workflow_step" in state_dict
    assert "user_query" in state_dict
    assert "context" in state_dict
    
    # Complete workflow
    manager.set_variable_value("workflow_step", "complete")
    assert manager.get_variable_value("workflow_step") == "complete"