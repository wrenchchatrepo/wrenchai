"""
Unit tests for the enhanced agent state management system.

This module tests the functionality of the enhanced agent state management system
to ensure that it correctly handles state persistence, context passing, and workflow state.
"""

import unittest
import sys
import os
import asyncio
import tempfile
import json
import shutil
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.agents.agent_state_enhanced import (
    AsyncAgentStateManager,
    AgentState,
    WorkflowState,
    ContextSnapshot,
    AgentStateEntry,
    StateTransaction
)


class TestAsyncAgentStateManager(unittest.IsolatedAsyncioTestCase):
    """Tests for the AsyncAgentStateManager."""
    
    async def asyncSetUp(self):
        """Set up test environment."""
        # Create a temporary directory for persistence
        self.temp_dir = tempfile.mkdtemp()
        
        # Create an instance with the temporary directory
        self.manager = AsyncAgentStateManager(self.temp_dir)
        
        # Test agent IDs
        self.agent_id = "test-agent-1"
        self.agent_id2 = "test-agent-2"
        
        # Create a test workflow
        self.workflow_id = "test-workflow-1"
        self.workflow = await self.manager.create_workflow(
            self.workflow_id,
            "Test Workflow"
        )
    
    async def asyncTearDown(self):
        """Clean up after tests."""
        # Clean up the temporary directory
        shutil.rmtree(self.temp_dir)
    
    async def test_agent_state_basic(self):
        """Test basic agent state operations."""
        # Set a state entry
        await self.manager.set_state_entry(
            self.agent_id,
            "test-key",
            "test-value"
        )
        
        # Get the state entry
        value = await self.manager.get_state_entry(
            self.agent_id,
            "test-key"
        )
        
        self.assertEqual(value, "test-value")
        
        # Delete the state entry
        result = await self.manager.delete_state_entry(
            self.agent_id,
            "test-key"
        )
        
        self.assertTrue(result)
        
        # Get the state entry again (should be default)
        value = await self.manager.get_state_entry(
            self.agent_id,
            "test-key",
            default="default-value"
        )
        
        self.assertEqual(value, "default-value")
    
    async def test_ttl_expiration(self):
        """Test time-to-live expiration."""
        # Set a state entry with a small TTL
        await self.manager.set_state_entry(
            self.agent_id,
            "ttl-key",
            "ttl-value",
            ttl=0  # Immediate expiration
        )
        
        # Get the state entry (should be expired)
        value = await self.manager.get_state_entry(
            self.agent_id,
            "ttl-key",
            default="expired"
        )
        
        self.assertEqual(value, "expired")
    
    async def test_visibility_levels(self):
        """Test different visibility levels."""
        # Set private state
        await self.manager.set_state_entry(
            self.agent_id,
            "private-key",
            "private-value",
            visibility="private"
        )
        
        # Set shared state
        await self.manager.set_state_entry(
            self.agent_id,
            "shared-key",
            "shared-value",
            visibility="shared"
        )
        
        # Set global state
        await self.manager.set_state_entry(
            self.agent_id,
            "global-key",
            "global-value",
            visibility="global"
        )
        
        # Test private visibility (only visible to the owner)
        value1 = await self.manager.get_state_entry(self.agent_id, "private-key")
        value2 = await self.manager.get_state_entry(self.agent_id2, "private-key", default="not-found")
        
        self.assertEqual(value1, "private-value")
        self.assertEqual(value2, "not-found")
        
        # Test shared visibility (visible to all agents)
        value1 = await self.manager.get_state_entry(self.agent_id, "shared-key")
        value2 = await self.manager.get_state_entry(self.agent_id2, "shared-key")
        
        self.assertEqual(value1, "shared-value")
        self.assertEqual(value2, "shared-value")
        
        # Test global visibility (visible to all agents)
        value1 = await self.manager.get_state_entry(self.agent_id, "global-key")
        value2 = await self.manager.get_state_entry(self.agent_id2, "global-key")
        
        self.assertEqual(value1, "global-value")
        self.assertEqual(value2, "global-value")
    
    async def test_operation_history(self):
        """Test operation history tracking."""
        # Register operations
        await self.manager.register_operation(
            self.agent_id,
            "test-operation-1",
            {"param1": "value1"}
        )
        
        await self.manager.register_operation(
            self.agent_id,
            "test-operation-2",
            {"param2": "value2"}
        )
        
        # Get operation history
        history = await self.manager.get_operations_history(self.agent_id)
        
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["operation"], "test-operation-1")
        self.assertEqual(history[1]["operation"], "test-operation-2")
        self.assertEqual(history[0]["metadata"]["param1"], "value1")
        self.assertEqual(history[1]["metadata"]["param2"], "value2")
    
    async def test_workflow_state(self):
        """Test workflow state management."""
        # Update workflow state
        await self.manager.update_workflow_state(
            self.workflow_id,
            status="running",
            current_step="step-1",
            context_update={"param1": "value1"}
        )
        
        # Get workflow state
        workflow = await self.manager.get_workflow_state(self.workflow_id)
        
        self.assertEqual(workflow.status, "running")
        self.assertEqual(workflow.current_step, "step-1")
        self.assertEqual(workflow.context["param1"], "value1")
        
        # Update workflow state again
        await self.manager.update_workflow_state(
            self.workflow_id,
            status="completed",
            current_step="step-2",
            context_update={"param2": "value2"}
        )
        
        # Get workflow state again
        workflow = await self.manager.get_workflow_state(self.workflow_id)
        
        self.assertEqual(workflow.status, "completed")
        self.assertEqual(workflow.current_step, "step-2")
        self.assertEqual(workflow.context["param1"], "value1")
        self.assertEqual(workflow.context["param2"], "value2")
        self.assertEqual(len(workflow.step_history), 2)
        self.assertEqual(workflow.step_history[0], "step-1")
        self.assertEqual(workflow.step_history[1], "step-2")
    
    async def test_context_snapshots(self):
        """Test context snapshot functionality."""
        # Set some state entries
        await self.manager.set_state_entry(
            self.agent_id,
            "snapshot-key-1",
            "snapshot-value-1"
        )
        
        await self.manager.set_state_entry(
            self.agent_id,
            "snapshot-key-2",
            "snapshot-value-2"
        )
        
        # Create a snapshot
        snapshot = await self.manager.create_context_snapshot(
            self.agent_id,
            scope="agent"
        )
        
        # Change state entries
        await self.manager.set_state_entry(
            self.agent_id,
            "snapshot-key-1",
            "changed-value-1"
        )
        
        await self.manager.delete_state_entry(
            self.agent_id,
            "snapshot-key-2"
        )
        
        # Verify changes
        value1 = await self.manager.get_state_entry(self.agent_id, "snapshot-key-1")
        value2 = await self.manager.get_state_entry(self.agent_id, "snapshot-key-2", default="deleted")
        
        self.assertEqual(value1, "changed-value-1")
        self.assertEqual(value2, "deleted")
        
        # Restore snapshot
        result = await self.manager.restore_context_snapshot(
            self.agent_id,
            snapshot.snapshot_id,
            scope="agent"
        )
        
        self.assertTrue(result)
        
        # Verify restored values
        value1 = await self.manager.get_state_entry(self.agent_id, "snapshot-key-1")
        value2 = await self.manager.get_state_entry(self.agent_id, "snapshot-key-2")
        
        self.assertEqual(value1, "snapshot-value-1")
        self.assertEqual(value2, "snapshot-value-2")
    
    async def test_transactions(self):
        """Test transaction functionality."""
        # Start a transaction
        async with self.manager.transaction(self.agent_id) as transaction:
            # Set state entries within the transaction
            await transaction.set("transaction-key-1", "transaction-value-1")
            await transaction.set("transaction-key-2", "transaction-value-2")
            
            # Values should be visible immediately
            value1 = await self.manager.get_state_entry(self.agent_id, "transaction-key-1")
            value2 = await self.manager.get_state_entry(self.agent_id, "transaction-key-2")
            
            self.assertEqual(value1, "transaction-value-1")
            self.assertEqual(value2, "transaction-value-2")
            
            # Auto-commit happens at the end of the context
        
        # Values should still be visible after commit
        value1 = await self.manager.get_state_entry(self.agent_id, "transaction-key-1")
        value2 = await self.manager.get_state_entry(self.agent_id, "transaction-key-2")
        
        self.assertEqual(value1, "transaction-value-1")
        self.assertEqual(value2, "transaction-value-2")
        
        # Test rollback
        transaction = await self.manager.transaction(self.agent_id).__aenter__()
        
        await transaction.set("rollback-key-1", "rollback-value-1")
        await transaction.set("rollback-key-2", "rollback-value-2")
        
        # Values should be visible immediately
        value1 = await self.manager.get_state_entry(self.agent_id, "rollback-key-1")
        value2 = await self.manager.get_state_entry(self.agent_id, "rollback-key-2")
        
        self.assertEqual(value1, "rollback-value-1")
        self.assertEqual(value2, "rollback-value-2")
        
        # Rollback the transaction
        await transaction.rollback()
        
        # Values should be reverted
        value1 = await self.manager.get_state_entry(self.agent_id, "rollback-key-1", default="rolled-back")
        value2 = await self.manager.get_state_entry(self.agent_id, "rollback-key-2", default="rolled-back")
        
        self.assertEqual(value1, "rolled-back")
        self.assertEqual(value2, "rolled-back")
    
    async def test_serialization(self):
        """Test serialization of complex types."""
        # Set a complex object
        complex_object = {
            "nested": {
                "array": [1, 2, 3],
                "date": datetime.utcnow()
            },
            "tuple": (4, 5, 6)
        }
        
        await self.manager.set_state_entry(
            self.agent_id,
            "complex-key",
            complex_object
        )
        
        # Get the complex object
        value = await self.manager.get_state_entry(
            self.agent_id,
            "complex-key"
        )
        
        # Verify the structure (note: tuple will be a list after serialization)
        self.assertIsInstance(value, dict)
        self.assertIsInstance(value["nested"], dict)
        self.assertIsInstance(value["nested"]["array"], list)
        # Not checking the date type since JSON serialization converts it to string
    
    async def test_workflow_scoped_entries(self):
        """Test workflow-scoped state entries."""
        # Set workflow-scoped state entry
        await self.manager.set_state_entry(
            self.agent_id,
            "workflow-key",
            "workflow-value",
            scope="workflow",
            workflow_id=self.workflow_id
        )
        
        # Get workflow-scoped state entry
        value = await self.manager.get_state_entry(
            self.agent_id,
            "workflow-key",
            workflow_id=self.workflow_id
        )
        
        self.assertEqual(value, "workflow-value")
        
        # Get all workflow-scoped entries
        entries = await self.manager.get_all_entries(
            self.agent_id,
            scope="workflow",
            workflow_id=self.workflow_id
        )
        
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries["workflow-key"], "workflow-value")
    
    async def test_tagged_entries(self):
        """Test tagged state entries."""
        # Create and tag entries
        await self.manager.set_state_entry(
            self.agent_id,
            "tag-key-1",
            "tag-value-1",
            tags=["test-tag"]
        )
        
        await self.manager.set_state_entry(
            self.agent_id,
            "tag-key-2",
            "tag-value-2",
            tags=["test-tag", "another-tag"]
        )
        
        # Get state by tag
        state = await self.manager.get_agent_state(self.agent_id)
        tagged_entries = state.get_entries_by_tag("test-tag")
        
        self.assertEqual(len(tagged_entries), 2)
        self.assertEqual(tagged_entries["tag-key-1"], "tag-value-1")
        self.assertEqual(tagged_entries["tag-key-2"], "tag-value-2")
        
        # Get state by another tag
        tagged_entries = state.get_entries_by_tag("another-tag")
        
        self.assertEqual(len(tagged_entries), 1)
        self.assertEqual(tagged_entries["tag-key-2"], "tag-value-2")
        
        # Get state by non-existent tag
        tagged_entries = state.get_entries_by_tag("non-existent-tag")
        
        self.assertEqual(len(tagged_entries), 0)
    
    async def test_persistence(self):
        """Test persistence to disk."""
        # Set some state entries
        await self.manager.set_state_entry(
            self.agent_id,
            "persist-key-1",
            "persist-value-1"
        )
        
        await self.manager.set_state_entry(
            self.agent_id,
            "persist-key-2",
            "persist-value-2"
        )
        
        # Create a new manager that should load from disk
        new_manager = AsyncAgentStateManager(self.temp_dir)
        
        # Get values from the new manager
        value1 = await new_manager.get_state_entry(
            self.agent_id,
            "persist-key-1"
        )
        
        value2 = await new_manager.get_state_entry(
            self.agent_id,
            "persist-key-2"
        )
        
        self.assertEqual(value1, "persist-value-1")
        self.assertEqual(value2, "persist-value-2")


if __name__ == "__main__":
    unittest.main()