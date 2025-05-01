"""Real-time progress tracking system for workflow execution.

This module provides a hierarchical progress tracking system for workflows, supporting:
- Hierarchical progress tracking (workflow -> step -> subtask)
- Real-time progress updates via WebSockets
- Persistent storage of progress information
- Progress state recovery after disconnections
- Time estimation for workflow completion

Key components:
- ProgressTracker: Main class for tracking and reporting progress
- ProgressState: Data structure for storing progress state
- ProgressItem: Represents a workflow, step, or subtask in the progress hierarchy
- ProgressEstimator: Estimates completion time based on historical data
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable

# Import required components from existing system
from .api import manager as websocket_manager
from .state_manager import StateManager, StateScope, StateVariable, state_manager
from .recovery_system import CheckpointManager, Checkpoint, CheckpointType

logger = logging.getLogger(__name__)


class ProgressStatus(str, Enum):
    """Status of a progress item."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    SKIPPED = "skipped"
    WAITING = "waiting"  # Waiting for dependency


class ProgressItemType(str, Enum):
    """Type of progress item in the hierarchy."""
    WORKFLOW = "workflow"
    STEP = "step"
    SUBTASK = "subtask"
    OPERATION = "operation"  # Lowest level of tracking


class ProgressEvent(str, Enum):
    """Events that can be triggered during progress tracking."""
    CREATED = "created"
    STARTED = "started"
    UPDATED = "updated"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    RESUMED = "resumed"
    SKIPPED = "skipped"
    ESTIMATED = "estimated"  # Time estimation updated


class ProgressItem:
    """Represents a trackable item in the progress hierarchy."""

    def __init__(
        self,
        id: str,
        name: str,
        type: ProgressItemType,
        parent_id: Optional[str] = None,
        description: str = "",
        weight: float = 1.0,
        total_work: float = 100.0,
        status: ProgressStatus = ProgressStatus.NOT_STARTED,
    ):
        """Initialize a progress item.
        
        Args:
            id: Unique identifier for the item
            name: Display name for the item
            type: Type of progress item (workflow, step, subtask, operation)
            parent_id: ID of the parent item (None for top-level items)
            description: Detailed description of the item
            weight: Relative importance weight for calculating parent progress
            total_work: Total work units for this item (100.0 by default)
            status: Initial status of the item
        """
        self.id = id
        self.name = name
        self.type = type
        self.parent_id = parent_id
        self.description = description
        self.weight = weight
        self.total_work = total_work
        self.status = status
        
        # Progress tracking
        self.work_completed = 0.0
        self.percent_complete = 0.0
        
        # Timing information
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.paused_at: Optional[datetime] = None
        self.paused_duration = timedelta(seconds=0)
        
        # Child items
        self.child_ids: Set[str] = set()
        
        # Estimation
        self.estimated_duration: Optional[timedelta] = None
        self.estimated_completion_time: Optional[datetime] = None
    
    def start(self):
        """Mark the item as started."""
        if self.status == ProgressStatus.NOT_STARTED:
            self.started_at = datetime.utcnow()
            self.updated_at = self.started_at
            self.status = ProgressStatus.IN_PROGRESS
    
    def update(self, work_completed: float):
        """Update progress on the item.
        
        Args:
            work_completed: Amount of work completed (absolute value)
        """
        self.work_completed = min(work_completed, self.total_work)
        self.percent_complete = (self.work_completed / self.total_work) * 100.0
        self.updated_at = datetime.utcnow()
        
        if self.work_completed >= self.total_work:
            self.complete()
    
    def increment(self, work_increment: float):
        """Increment progress on the item.
        
        Args:
            work_increment: Amount of work to add to current progress
        """
        self.update(self.work_completed + work_increment)
    
    def complete(self):
        """Mark the item as completed."""
        self.work_completed = self.total_work
        self.percent_complete = 100.0
        self.status = ProgressStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.updated_at = self.completed_at
    
    def fail(self, error_message: Optional[str] = None):
        """Mark the item as failed.
        
        Args:
            error_message: Optional error message describing the failure
        """
        self.status = ProgressStatus.FAILED
        self.updated_at = datetime.utcnow()
        if error_message:
            self.description = f"{self.description}\nError: {error_message}"
    
    def pause(self):
        """Pause progress on the item."""
        if self.status == ProgressStatus.IN_PROGRESS:
            self.status = ProgressStatus.PAUSED
            self.paused_at = datetime.utcnow()
            self.updated_at = self.paused_at
    
    def resume(self):
        """Resume progress on the item."""
        if self.status == ProgressStatus.PAUSED and self.paused_at:
            # Calculate and store paused duration
            now = datetime.utcnow()
            self.paused_duration += now - self.paused_at
            
            # Update status
            self.status = ProgressStatus.IN_PROGRESS
            self.updated_at = now
            self.paused_at = None
    
    def skip(self):
        """Mark the item as skipped."""
        self.status = ProgressStatus.SKIPPED
        self.updated_at = datetime.utcnow()
    
    def add_child(self, child_id: str):
        """Add a child item to this item.
        
        Args:
            child_id: ID of the child item
        """
        self.child_ids.add(child_id)
    
    def remove_child(self, child_id: str):
        """Remove a child item from this item.
        
        Args:
            child_id: ID of the child item to remove
        """
        if child_id in self.child_ids:
            self.child_ids.remove(child_id)
    
    def get_active_duration(self) -> timedelta:
        """Get the active duration of the item (excluding paused time).
        
        Returns:
            Active duration as a timedelta
        """
        if not self.started_at:
            return timedelta(seconds=0)
            
        end_time = self.completed_at or self.updated_at or datetime.utcnow()
        total_duration = end_time - self.started_at
        
        # Subtract paused duration
        active_duration = total_duration - self.paused_duration
        
        # If currently paused, subtract current pause duration
        if self.status == ProgressStatus.PAUSED and self.paused_at:
            active_duration -= (datetime.utcnow() - self.paused_at)
            
        return active_duration
    
    def set_estimated_duration(self, duration: timedelta):
        """Set the estimated duration for this item.
        
        Args:
            duration: Estimated duration for the item
        """
        self.estimated_duration = duration
        
        # Calculate estimated completion time
        if self.started_at:
            self.estimated_completion_time = self.started_at + duration + self.paused_duration
            
            # If paused, add the current pause duration
            if self.status == ProgressStatus.PAUSED and self.paused_at:
                self.estimated_completion_time += (datetime.utcnow() - self.paused_at)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the progress item to a dictionary for persistence.
        
        Returns:
            Dictionary representation of the item
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "parent_id": self.parent_id,
            "description": self.description,
            "weight": self.weight,
            "total_work": self.total_work,
            "work_completed": self.work_completed,
            "percent_complete": self.percent_complete,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "paused_duration": self.paused_duration.total_seconds(),
            "child_ids": list(self.child_ids),
            "estimated_duration": self.estimated_duration.total_seconds() if self.estimated_duration else None,
            "estimated_completion_time": self.estimated_completion_time.isoformat() if self.estimated_completion_time else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgressItem':
        """Create a progress item from a dictionary.
        
        Args:
            data: Dictionary representation of the item
            
        Returns:
            Progress item instance
        """
        item = cls(
            id=data["id"],
            name=data["name"],
            type=ProgressItemType(data["type"]),
            parent_id=data["parent_id"],
            description=data["description"],
            weight=data["weight"],
            total_work=data["total_work"],
            status=ProgressStatus(data["status"]),
        )
        
        # Set direct properties
        item.work_completed = data["work_completed"]
        item.percent_complete = data["percent_complete"]
        item.child_ids = set(data["child_ids"])
        
        # Parse datetime fields
        item.created_at = datetime.fromisoformat(data["created_at"])
        
        if data["started_at"]:
            item.started_at = datetime.fromisoformat(data["started_at"])
            
        if data["updated_at"]:
            item.updated_at = datetime.fromisoformat(data["updated_at"])
            
        if data["completed_at"]:
            item.completed_at = datetime.fromisoformat(data["completed_at"])
            
        if data["paused_at"]:
            item.paused_at = datetime.fromisoformat(data["paused_at"])
            
        # Parse timedelta fields
        item.paused_duration = timedelta(seconds=data["paused_duration"])
        
        if data["estimated_duration"] is not None:
            item.estimated_duration = timedelta(seconds=data["estimated_duration"])
            
        if data["estimated_completion_time"]:
            item.estimated_completion_time = datetime.fromisoformat(data["estimated_completion_time"])
            
        return item
    
    def __repr__(self) -> str:
        """Get string representation of the progress item.
        
        Returns:
            String representation
        """
        return f"ProgressItem(id={self.id}, name={self.name}, type={self.type.value}, status={self.status.value}, progress={self.percent_complete:.1f}%)"


class ProgressState:
    """Manages the state of all progress items."""
    
    def __init__(self):
        """Initialize the progress state."""
        self.items: Dict[str, ProgressItem] = {}
        self.root_ids: Set[str] = set()
        self._lock = Lock()
    
    def add_item(self, item: ProgressItem) -> str:
        """Add a progress item to the state.
        
        Args:
            item: The progress item to add
            
        Returns:
            ID of the added item
        """
        with self._lock:
            self.items[item.id] = item
            
            # Add as child to parent if exists
            if item.parent_id and item.parent_id in self.items:
                self.items[item.parent_id].add_child(item.id)
            else:
                # No parent, so it's a root item
                self.root_ids.add(item.id)
                
            return item.id
    
    def get_item(self, item_id: str) -> Optional[ProgressItem]:
        """Get a progress item by ID.
        
        Args:
            item_id: ID of the item to get
            
        Returns:
            The progress item, or None if not found
        """
        with self._lock:
            return self.items.get(item_id)
    
    def get_children(self, item_id: str) -> List[ProgressItem]:
        """Get all children of a progress item.
        
        Args:
            item_id: ID of the parent item
            
        Returns:
            List of child items
        """
        with self._lock:
            if item_id not in self.items:
                return []
                
            parent = self.items[item_id]
            return [self.items[child_id] for child_id in parent.child_ids if child_id in self.items]
    
    def update_item(self, item_id: str, work_completed: float) -> bool:
        """Update progress on an item.
        
        Args:
            item_id: ID of the item to update
            work_completed: Amount of work completed
            
        Returns:
            True if the item was updated, False otherwise
        """
        with self._lock:
            if item_id not in self.items:
                return False
                
            item = self.items[item_id]
            item.update(work_completed)
            
            # If it has a parent, update parent's progress based on children
            if item.parent_id and item.parent_id in self.items:
                self._update_parent_progress(item.parent_id)
                
            return True
    
    def _update_parent_progress(self, parent_id: str):
        """Update a parent item's progress based on its children.
        
        Args:
            parent_id: ID of the parent item
        """
        parent = self.items[parent_id]
        children = self.get_children(parent_id)
        
        if not children:
            return
            
        # Calculate weighted progress
        total_weight = sum(child.weight for child in children)
        
        if total_weight > 0:
            weighted_progress = sum(
                (child.percent_complete / 100.0) * child.weight 
                for child in children
            ) / total_weight
            
            # Update parent's work completed
            parent.update(parent.total_work * weighted_progress)
            
            # Recursively update parent's parent if exists
            if parent.parent_id and parent.parent_id in self.items:
                self._update_parent_progress(parent.parent_id)
    
    def mark_item_status(self, item_id: str, status: ProgressStatus, 
                        cascade: bool = False) -> bool:
        """Mark an item with a status.
        
        Args:
            item_id: ID of the item to mark
            status: New status for the item
            cascade: Whether to cascade the status to children
            
        Returns:
            True if the item was marked, False otherwise
        """
        with self._lock:
            if item_id not in self.items:
                return False
                
            item = self.items[item_id]
            
            # Apply status-specific actions
            if status == ProgressStatus.IN_PROGRESS:
                if not item.started_at:
                    item.start()
                else:
                    item.resume()
            elif status == ProgressStatus.COMPLETED:
                item.complete()
            elif status == ProgressStatus.FAILED:
                item.fail()
            elif status == ProgressStatus.PAUSED:
                item.pause()
            elif status == ProgressStatus.SKIPPED:
                item.skip()
            else:
                item.status = status
                item.updated_at = datetime.utcnow()
                
            # Cascade to children if requested
            if cascade:
                for child_id in item.child_ids:
                    if child_id in self.items:
                        self.mark_item_status(child_id, status, cascade=True)
                        
            # Update parent progress
            if item.parent_id and item.parent_id in self.items:
                self._update_parent_progress(item.parent_id)
                
            return True
    
    def remove_item(self, item_id: str, cascade: bool = True) -> bool:
        """Remove a progress item.
        
        Args:
            item_id: ID of the item to remove
            cascade: Whether to remove children as well
            
        Returns:
            True if the item was removed, False otherwise
        """
        with self._lock:
            if item_id not in self.items:
                return False
                
            item = self.items[item_id]
            
            # Remove from parent if exists
            if item.parent_id and item.parent_id in self.items:
                self.items[item.parent_id].remove_child(item_id)
            else:
                # Remove from root ids
                self.root_ids.discard(item_id)
                
            # Remove children if requested
            if cascade:
                for child_id in list(item.child_ids):
                    self.remove_item(child_id, cascade=True)
                    
            # Remove the item
            del self.items[item_id]
            
            return True
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get a summary of all progress items.
        
        Returns:
            Dictionary with progress summary information
        """
        with self._lock:
            root_items = [self.items[root_id] for root_id in self.root_ids if root_id in self.items]
            
            # Overall progress is weighted average of root items
            total_weight = sum(item.weight for item in root_items)
            
            if total_weight > 0:
                overall_progress = sum(
                    (item.percent_complete / 100.0) * item.weight 
                    for item in root_items
                ) / total_weight * 100.0
            else:
                overall_progress = 0.0
                
            # Get latest estimated completion time
            active_workflows = [item for item in root_items if item.status == ProgressStatus.IN_PROGRESS 
                              and item.estimated_completion_time]
                              
            if active_workflows:
                estimated_completion = max(item.estimated_completion_time for item in active_workflows)
            else:
                estimated_completion = None
                
            return {
                "overall_progress": overall_progress,
                "total_items": len(self.items),
                "root_items": len(root_items),
                "active_items": sum(1 for item in self.items.values() if item.status == ProgressStatus.IN_PROGRESS),
                "completed_items": sum(1 for item in self.items.values() if item.status == ProgressStatus.COMPLETED),
                "failed_items": sum(1 for item in self.items.values() if item.status == ProgressStatus.FAILED),
                "estimated_completion": estimated_completion.isoformat() if estimated_completion else None,
            }
    
    def get_item_tree(self, root_id: Optional[str] = None) -> Dict[str, Any]:
        """Get a hierarchical representation of the progress items.
        
        Args:
            root_id: ID of the root item (None for all roots)
            
        Returns:
            Dictionary with hierarchical progress information
        """
        with self._lock:
            def build_tree(item_id: str) -> Dict[str, Any]:
                item = self.items[item_id]
                tree = item.to_dict()
                tree["children"] = [
                    build_tree(child_id) 
                    for child_id in item.child_ids 
                    if child_id in self.items
                ]
                return tree
                
            if root_id:
                if root_id not in self.items:
                    return {}
                return build_tree(root_id)
            else:
                # Build trees for all root items
                return {
                    "root_items": [
                        build_tree(root_id) 
                        for root_id in self.root_ids 
                        if root_id in self.items
                    ]
                }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the progress state to a dictionary for persistence.
        
        Returns:
            Dictionary representation of the state
        """
        with self._lock:
            return {
                "items": {item_id: item.to_dict() for item_id, item in self.items.items()},
                "root_ids": list(self.root_ids),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgressState':
        """Create a progress state from a dictionary.
        
        Args:
            data: Dictionary representation of the state
            
        Returns:
            Progress state instance
        """
        state = cls()
        
        # Load items
        for item_id, item_data in data["items"].items():
            item = ProgressItem.from_dict(item_data)
            state.items[item_id] = item
            
        # Set root IDs
        state.root_ids = set(data["root_ids"])
        
        return state


class ProgressEstimator:
    """Estimates completion time for progress items."""
    
    def __init__(self, history_window: int = 10):
        """Initialize the progress estimator.
        
        Args:
            history_window: Number of historical samples to consider for estimation
        """
        self.history_window = history_window
        self.historical_data: Dict[str, List[Dict[str, Any]]] = {}
        self.active_estimations: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
    
    def start_estimation(self, item_id: str, item_type: ProgressItemType, 
                        total_work: float) -> None:
        """Start time estimation for a progress item.
        
        Args:
            item_id: ID of the item to estimate
            item_type: Type of the item
            total_work: Total work units for the item
        """
        with self._lock:
            self.active_estimations[item_id] = {
                "start_time": datetime.utcnow(),
                "item_type": item_type,
                "total_work": total_work,
                "last_progress": 0.0,
                "last_time": datetime.utcnow(),
                "progress_history": [],
            }
    
    def update_progress(self, item_id: str, current_progress: float) -> Optional[timedelta]:
        """Update progress for an item and recalculate estimated completion time.
        
        Args:
            item_id: ID of the item
            current_progress: Current progress (0.0 - 100.0)
            
        Returns:
            Estimated time to completion as timedelta, or None if estimation not possible
        """
        with self._lock:
            if item_id not in self.active_estimations:
                return None
                
            estimation = self.active_estimations[item_id]
            now = datetime.utcnow()
            
            # Record progress point
            progress_point = {
                "timestamp": now,
                "progress": current_progress,
                "elapsed": (now - estimation["start_time"]).total_seconds()
            }
            
            # Add to history if progress has actually changed
            if current_progress > estimation["last_progress"]:
                estimation["progress_history"].append(progress_point)
                estimation["last_progress"] = current_progress
                estimation["last_time"] = now
                
                # Prune history to window size
                if len(estimation["progress_history"]) > self.history_window:
                    estimation["progress_history"] = estimation["progress_history"][-self.history_window:]
                    
            # Can't estimate with less than 2 data points
            if len(estimation["progress_history"]) < 2:
                return None
                
            # Calculate progress rate (progress units per second)
            progress_rates = []
            for i in range(1, len(estimation["progress_history"])):
                prev = estimation["progress_history"][i-1]
                curr = estimation["progress_history"][i]
                
                time_diff = curr["elapsed"] - prev["elapsed"]
                progress_diff = curr["progress"] - prev["progress"]
                
                if time_diff > 0:
                    rate = progress_diff / time_diff
                    progress_rates.append(rate)
            
            # Use median rate for better stability
            progress_rates.sort()
            if len(progress_rates) % 2 == 0:
                median_rate = (
                    progress_rates[len(progress_rates)//2 - 1] +
                    progress_rates[len(progress_rates)//2]
                ) / 2
            else:
                median_rate = progress_rates[len(progress_rates)//2]
                
            # Avoid division by zero
            if median_rate <= 0:
                return None
                
            # Calculate estimated time to completion
            remaining_progress = 100.0 - current_progress
            estimated_seconds = remaining_progress / median_rate
            
            return timedelta(seconds=estimated_seconds)
    
    def complete_estimation(self, item_id: str) -> None:
        """Complete time estimation for an item and store historical data.
        
        Args:
            item_id: ID of the completed item
        """
        with self._lock:
            if item_id not in self.active_estimations:
                return
                
            estimation = self.active_estimations[item_id]
            
            # Store in historical data for future reference
            item_type = estimation["item_type"]
            if item_type not in self.historical_data:
                self.historical_data[item_type] = []
                
            self.historical_data[item_type].append({
                "total_work": estimation["total_work"],
                "actual_duration": (datetime.utcnow() - estimation["start_time"]).total_seconds(),
                "progress_history": estimation["progress_history"],
            })
            
            # Prune historical data
            if len(self.historical_data[item_type]) > self.history_window * 2:
                self.historical_data[item_type] = self.historical_data[item_type][-self.history_window * 2:]
                
            # Remove from active estimations
            del self.active_estimations[item_id]
    
    def get_initial_estimate(self, item_type: ProgressItemType, 
                            total_work: float) -> Optional[timedelta]:
        """Get an initial time estimate based on historical data.
        
        Args:
            item_type: Type of the item
            total_work: Total work units for the item
            
        Returns:
            Initial time estimate as timedelta, or None if not enough historical data
        """
        with self._lock:
            if item_type not in self.historical_data or not self.historical_data[item_type]:
                return None
                
            # Get similar items from history based on total work
            similar_items = [
                item for item in self.historical_data[item_type]
                if 0.5 * total_work <= item["total_work"] <= 2.0 * total_work
            ]
            
            if not similar_items:
                # Fall back to all items of this type
                similar_items = self.historical_data[item_type]
                
            # Calculate average duration
            total_duration = sum(item["actual_duration"] for item in similar_items)
            avg_duration = total_duration / len(similar_items)
            
            # Scale based on work units ratio
            avg_work = sum(item["total_work"] for item in similar_items) / len(similar_items)
            scaled_duration = avg_duration * (total_work / avg_work)
            
            return timedelta(seconds=scaled_duration)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the estimator to a dictionary for persistence.
        
        Returns:
            Dictionary representation of the estimator
        """
        with self._lock:
            return {
                "history_window": self.history_window,
                "historical_data": self.historical_data,
                "active_estimations": self.active_estimations,
            }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgressEstimator':
        """Create a progress estimator from a dictionary.
        
        Args:
            data: Dictionary representation of the estimator
            
        Returns:
            Progress estimator instance
        """
        estimator = cls(history_window=data["history_window"])
        estimator.historical_data = data["historical_data"]
        estimator.active_estimations = data["active_estimations"]
        
        return estimator


class ProgressTracker:
    """Manages real-time progress tracking for workflows."""
    
    def __init__(
        self, 
        state_manager: Optional[StateManager] = None,
        persistence_dir: Optional[str] = None,
        checkpoint_interval: int = 30,  # Checkpoint every 30 seconds
        broadcast_interval: int = 2,    # Broadcast updates every 2 seconds
    ):
        """Initialize the progress tracker.
        
        Args:
            state_manager: State manager for variables (uses global if None)
            persistence_dir: Directory for persistence files
            checkpoint_interval: Interval in seconds for automatic checkpoints
            broadcast_interval: Interval in seconds for broadcasting updates
        """
        self.state_manager = state_manager or state_manager
        self._persistence_dir = persistence_dir or os.path.join("data", "progress")
        self.checkpoint_interval = checkpoint_interval
        self.broadcast_interval = broadcast_interval
        
        # Ensure persistence directory exists
        if self._persistence_dir:
            os.makedirs(self._persistence_dir, exist_ok=True)
            
        # Create state and estimator
        self.state = ProgressState()
        self.estimator = ProgressEstimator()
        
        # Active workflows and update queue
        self.active_workflows: Dict[str, str] = {}  # session_id -> workflow_id
        self._update_queue: Set[str] = set()  # item_ids with pending updates
        self._lock = Lock()
        
        # Async tasks
        self._checkpoint_task = None
        self._broadcast_task = None
        self._running = False
    
    async def start(self):
        """Start background tasks for progress tracking."""
        if self._running:
            return
            
        self._running = True
        self._checkpoint_task = asyncio.create_task(self._checkpoint_loop())
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        
        logger.info("Progress tracker started")
    
    async def stop(self):
        """Stop background tasks for progress tracking."""
        if not self._running:
            return
            
        self._running = False
        
        if self._checkpoint_task:
            self._checkpoint_task.cancel()
            try:
                await self._checkpoint_task
            except asyncio.CancelledError:
                pass
                
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
                
        # Save final checkpoint
        await self.save_checkpoint()
        
        logger.info("Progress tracker stopped")
    
    async def register_session(self, session_id: str, workflow_id: str):
        """Register a client session with a workflow.
        
        Args:
            session_id: Client session ID
            workflow_id: ID of the workflow to track
        """
        with self._lock:
            self.active_workflows[session_id] = workflow_id
    
    async def unregister_session(self, session_id: str):
        """Unregister a client session.
        
        Args:
            session_id: Client session ID to unregister
        """
        with self._lock:
            if session_id in self.active_workflows:
                del self.active_workflows[session_id]
    
    def create_workflow(
        self, 
        name: str, 
        description: str = "",
        total_work: float = 100.0,
        workflow_id: Optional[str] = None
    ) -> str:
        """Create a new top-level workflow.
        
        Args:
            name: Name of the workflow
            description: Description of the workflow
            total_work: Total work units for the workflow
            workflow_id: Optional ID for the workflow (generated if None)
            
        Returns:
            ID of the created workflow
        """
        workflow_id = workflow_id or f"workflow_{uuid.uuid4()}"
        
        workflow = ProgressItem(
            id=workflow_id,
            name=name,
            type=ProgressItemType.WORKFLOW,
            description=description,
            total_work=total_work,
        )
        
        # Add to state
        self.state.add_item(workflow)
        
        # Get initial estimate if possible
        initial_estimate = self.estimator.get_initial_estimate(
            ProgressItemType.WORKFLOW, total_work
        )
        
        if initial_estimate:
            workflow.set_estimated_duration(initial_estimate)
            
        # Start estimation
        self.estimator.start_estimation(workflow_id, ProgressItemType.WORKFLOW, total_work)
        
        # Queue update
        self._queue_update(workflow_id)
        
        # Return the workflow ID
        return workflow_id
    
    def create_step(
        self, 
        workflow_id: str, 
        name: str, 
        description: str = "",
        weight: float = 1.0,
        total_work: float = 100.0,
        step_id: Optional[str] = None
    ) -> str:
        """Create a new step in a workflow.
        
        Args:
            workflow_id: ID of the parent workflow
            name: Name of the step
            description: Description of the step
            weight: Relative importance weight for calculating parent progress
            total_work: Total work units for the step
            step_id: Optional ID for the step (generated if None)
            
        Returns:
            ID of the created step
        """
        step_id = step_id or f"step_{uuid.uuid4()}"
        
        step = ProgressItem(
            id=step_id,
            name=name,
            type=ProgressItemType.STEP,
            parent_id=workflow_id,
            description=description,
            weight=weight,
            total_work=total_work,
        )
        
        # Add to state
        self.state.add_item(step)
        
        # Get initial estimate if possible
        initial_estimate = self.estimator.get_initial_estimate(
            ProgressItemType.STEP, total_work
        )
        
        if initial_estimate:
            step.set_estimated_duration(initial_estimate)
            
        # Start estimation
        self.estimator.start_estimation(step_id, ProgressItemType.STEP, total_work)
        
        # Queue update
        self._queue_update(step_id)
        
        # Return the step ID
        return step_id
    
    def create_subtask(
        self, 
        parent_id: str, 
        name: str, 
        description: str = "",
        weight: float = 1.0,
        total_work: float = 100.0,
        subtask_id: Optional[str] = None
    ) -> str:
        """Create a new subtask in a step or workflow.
        
        Args:
            parent_id: ID of the parent item
            name: Name of the subtask
            description: Description of the subtask
            weight: Relative importance weight for calculating parent progress
            total_work: Total work units for the subtask
            subtask_id: Optional ID for the subtask (generated if None)
            
        Returns:
            ID of the created subtask
        """
        subtask_id = subtask_id or f"subtask_{uuid.uuid4()}"
        
        subtask = ProgressItem(
            id=subtask_id,
            name=name,
            type=ProgressItemType.SUBTASK,
            parent_id=parent_id,
            description=description,
            weight=weight,
            total_work=total_work,
        )
        
        # Add to state
        self.state.add_item(subtask)
        
        # Get initial estimate if possible
        initial_estimate = self.estimator.get_initial_estimate(
            ProgressItemType.SUBTASK, total_work
        )
        
        if initial_estimate:
            subtask.set_estimated_duration(initial_estimate)
            
        # Start estimation
        self.estimator.start_estimation(subtask_id, ProgressItemType.SUBTASK, total_work)
        
        # Queue update
        self._queue_update(subtask_id)
        
        # Return the subtask ID
        return subtask_id
    
    def create_operation(
        self, 
        parent_id: str, 
        name: str, 
        description: str = "",
        weight: float = 1.0,
        total_work: float = 100.0,
        operation_id: Optional[str] = None
    ) -> str:
        """Create a new operation (lowest-level task).
        
        Args:
            parent_id: ID of the parent item
            name: Name of the operation
            description: Description of the operation
            weight: Relative importance weight for calculating parent progress
            total_work: Total work units for the operation
            operation_id: Optional ID for the operation (generated if None)
            
        Returns:
            ID of the created operation
        """
        operation_id = operation_id or f"operation_{uuid.uuid4()}"
        
        operation = ProgressItem(
            id=operation_id,
            name=name,
            type=ProgressItemType.OPERATION,
            parent_id=parent_id,
            description=description,
            weight=weight,
            total_work=total_work,
        )
        
        # Add to state
        self.state.add_item(operation)
        
        # Get initial estimate if possible
        initial_estimate = self.estimator.get_initial_estimate(
            ProgressItemType.OPERATION, total_work
        )
        
        if initial_estimate:
            operation.set_estimated_duration(initial_estimate)
            
        # Start estimation
        self.estimator.start_estimation(operation_id, ProgressItemType.OPERATION, total_work)
        
        # Queue update
        self._queue_update(operation_id)
        
        # Return the operation ID
        return operation_id
    
    def start_item(self, item_id: str) -> bool:
        """Start progress on an item.
        
        Args:
            item_id: ID of the item to start
            
        Returns:
            True if the item was started, False otherwise
        """
        result = self.state.mark_item_status(item_id, ProgressStatus.IN_PROGRESS)
        
        if result:
            # Queue update
            self._queue_update(item_id)
            
        return result
    
    def update_progress(self, item_id: str, progress: float) -> bool:
        """Update progress on an item.
        
        Args:
            item_id: ID of the item to update
            progress: Absolute progress value (0.0 - 100.0)
            
        Returns:
            True if the item was updated, False otherwise
        """
        # Get item
        item = self.state.get_item(item_id)
        if not item:
            return False
            
        # Start if not started
        if item.status == ProgressStatus.NOT_STARTED:
            self.start_item(item_id)
            
        # Update progress
        work_completed = (progress / 100.0) * item.total_work
        result = self.state.update_item(item_id, work_completed)
        
        if result:
            # Update time estimation
            updated_estimate = self.estimator.update_progress(item_id, progress)
            
            if updated_estimate and item.status == ProgressStatus.IN_PROGRESS:
                item.set_estimated_duration(updated_estimate)
                
            # Queue update
            self._queue_update(item_id)
            
            # If completed, update estimation history
            if progress >= 100.0:
                self.estimator.complete_estimation(item_id)
                
        return result
    
    def increment_progress(self, item_id: str, increment: float) -> bool:
        """Increment progress on an item.
        
        Args:
            item_id: ID of the item to update
            increment: Relative progress increment
            
        Returns:
            True if the item was updated, False otherwise
        """
        # Get item
        item = self.state.get_item(item_id)
        if not item:
            return False
            
        # Calculate new progress percentage
        new_progress = item.percent_complete + increment
        
        # Update with the new progress
        return self.update_progress(item_id, new_progress)
    
    def complete_item(self, item_id: str, cascade: bool = False) -> bool:
        """Mark an item as completed.
        
        Args:
            item_id: ID of the item to complete
            cascade: Whether to mark all children as completed as well
            
        Returns:
            True if the item was completed, False otherwise
        """
        result = self.state.mark_item_status(item_id, ProgressStatus.COMPLETED, cascade)
        
        if result:
            # Complete estimation
            self.estimator.complete_estimation(item_id)
            
            # Queue update
            self._queue_update(item_id)
            
        return result
    
    def fail_item(self, item_id: str, error_message: Optional[str] = None, 
                cascade: bool = False) -> bool:
        """Mark an item as failed.
        
        Args:
            item_id: ID of the item to fail
            error_message: Optional error message describing the failure
            cascade: Whether to mark all children as failed as well
            
        Returns:
            True if the item was marked as failed, False otherwise
        """
        item = self.state.get_item(item_id)
        if not item:
            return False
            
        # Add error message if provided
        if error_message:
            item.fail(error_message)
            
        result = self.state.mark_item_status(item_id, ProgressStatus.FAILED, cascade)
        
        if result:
            # Complete estimation
            self.estimator.complete_estimation(item_id)
            
            # Queue update
            self._queue_update(item_id)
            
        return result
    
    def pause_item(self, item_id: str, cascade: bool = False) -> bool:
        """Pause progress on an item.
        
        Args:
            item_id: ID of the item to pause
            cascade: Whether to pause all children as well
            
        Returns:
            True if the item was paused, False otherwise
        """
        result = self.state.mark_item_status(item_id, ProgressStatus.PAUSED, cascade)
        
        if result:
            # Queue update
            self._queue_update(item_id)
            
        return result
    
    def resume_item(self, item_id: str, cascade: bool = False) -> bool:
        """Resume progress on a paused item.
        
        Args:
            item_id: ID of the item to resume
            cascade: Whether to resume all children as well
            
        Returns:
            True if the item was resumed, False otherwise
        """
        result = self.state.mark_item_status(item_id, ProgressStatus.IN_PROGRESS, cascade)
        
        if result:
            # Queue update
            self._queue_update(item_id)
            
        return result
    
    def skip_item(self, item_id: str, cascade: bool = False) -> bool:
        """Mark an item as skipped.
        
        Args:
            item_id: ID of the item to skip
            cascade: Whether to mark all children as skipped as well
            
        Returns:
            True if the item was marked as skipped, False otherwise
        """
        result = self.state.mark_item_status(item_id, ProgressStatus.SKIPPED, cascade)
        
        if result:
            # Complete estimation
            self.estimator.complete_estimation(item_id)
            
            # Queue update
            self._queue_update(item_id)
            
        return result
    
    def get_progress(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get the current progress of an item.
        
        Args:
            item_id: ID of the item
            
        Returns:
            Dictionary with progress information, or None if not found
        """
        item = self.state.get_item(item_id)
        if not item:
            return None
            
        # Get children progress
        children = self.state.get_children(item_id)
        children_progress = [
            {
                "id": child.id,
                "name": child.name,
                "type": child.type.value,
                "status": child.status.value,
                "progress": child.percent_complete,
                "child_count": len(child.child_ids),
            }
            for child in children
        ]
        
        # Build detailed progress report
        return {
            "id": item.id,
            "name": item.name,
            "type": item.type.value,
            "description": item.description,
            "status": item.status.value,
            "progress": item.percent_complete,
            "work_completed": item.work_completed,
            "total_work": item.total_work,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "started_at": item.started_at.isoformat() if item.started_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
            "estimated_completion": item.estimated_completion_time.isoformat() if item.estimated_completion_time else None,
            "children": children_progress,
            "child_count": len(children),
        }
    
    def get_workflow_progress(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the complete hierarchical progress for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Dictionary with complete hierarchical progress information, or None if not found
        """
        return self.state.get_item_tree(workflow_id)
    
    def get_overall_progress(self) -> Dict[str, Any]:
        """Get the overall progress across all workflows.
        
        Returns:
            Dictionary with overall progress information
        """
        return self.state.get_progress_summary()
    
    async def save_checkpoint(self, filename: Optional[str] = None) -> bool:
        """Save the current progress state to a checkpoint file.
        
        Args:
            filename: Optional filename for the checkpoint
            
        Returns:
            True if the checkpoint was saved successfully, False otherwise
        """
        if not self._persistence_dir:
            return False
            
        try:
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"progress_checkpoint_{timestamp}.json"
                
            # Create full path
            filepath = os.path.join(self._persistence_dir, filename)
            
            # Save state
            with open(filepath, 'w') as f:
                json.dump({
                    "state": self.state.to_dict(),
                    "estimator": self.estimator.to_dict(),
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": "1.0",
                }, f, indent=2)
                
            logger.info(f"Progress checkpoint saved to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving progress checkpoint: {e}")
            return False
    
    async def load_checkpoint(self, filename: Optional[str] = None) -> bool:
        """Load progress state from a checkpoint file.
        
        Args:
            filename: Filename of the checkpoint to load (latest if None)
            
        Returns:
            True if the checkpoint was loaded successfully, False otherwise
        """
        if not self._persistence_dir:
            return False
            
        try:
            # Find latest checkpoint if filename not provided
            if not filename:
                checkpoint_files = [f for f in os.listdir(self._persistence_dir) 
                                   if f.startswith("progress_checkpoint_") and f.endswith(".json")]
                                   
                if not checkpoint_files:
                    logger.warning("No checkpoint files found")
                    return False
                    
                checkpoint_files.sort(reverse=True)  # Latest first
                filename = checkpoint_files[0]
                
            # Create full path
            filepath = os.path.join(self._persistence_dir, filename)
            
            # Load state
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            # Validate version
            if data.get("version", "1.0") != "1.0":
                logger.warning(f"Checkpoint version mismatch: {data.get('version')}")
                
            # Restore state
            self.state = ProgressState.from_dict(data["state"])
            self.estimator = ProgressEstimator.from_dict(data["estimator"])
            
            logger.info(f"Progress checkpoint loaded from {filepath}")
            
            # Queue updates for all items
            for item_id in self.state.items:
                self._queue_update(item_id)
                
            return True
            
        except Exception as e:
            logger.error(f"Error loading progress checkpoint: {e}")
            return False
    
    def _queue_update(self, item_id: str):
        """Queue an item for update broadcast.
        
        Args:
            item_id: ID of the item to queue
        """
        with self._lock:
            self._update_queue.add(item_id)
    
    async def _checkpoint_loop(self):
        """Background task for periodic checkpointing."""
        try:
            while self._running:
                await asyncio.sleep(self.checkpoint_interval)
                await self.save_checkpoint()
        except asyncio.CancelledError:
            logger.debug("Checkpoint loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in checkpoint loop: {e}")
    
    async def _broadcast_loop(self):
        """Background task for broadcasting updates."""
        try:
            while self._running:
                # Wait for broadcast interval
                await asyncio.sleep(self.broadcast_interval)
                
                # Get items to update
                with self._lock:
                    items_to_update = list(self._update_queue)
                    self._update_queue.clear()
                    
                if not items_to_update:
                    continue
                    
                # Broadcast updates for each item
                for item_id in items_to_update:
                    item = self.state.get_item(item_id)
                    if not item:
                        continue
                        
                    # Find the workflow for this item
                    workflow_id = item_id
                    current_item = item
                    
                    # Traverse up to find the root workflow
                    while current_item.parent_id:
                        parent_id = current_item.parent_id
                        parent = self.state.get_item(parent_id)
                        if not parent:
                            break
                            
                        workflow_id = parent_id if parent.type == ProgressItemType.WORKFLOW else workflow_id
                        current_item = parent
                        
                    # Find sessions for this workflow
                    sessions_to_notify = [
                        session_id for session_id, wf_id in self.active_workflows.items()
                        if wf_id == workflow_id
                    ]
                    
                    # Broadcast update to relevant sessions
                    for session_id in sessions_to_notify:
                        # Get update event type based on status
                        if item.status == ProgressStatus.COMPLETED:
                            event = ProgressEvent.COMPLETED
                        elif item.status == ProgressStatus.FAILED:
                            event = ProgressEvent.FAILED
                        elif item.status == ProgressStatus.IN_PROGRESS and not item.started_at:
                            event = ProgressEvent.STARTED
                        elif item.status == ProgressStatus.PAUSED:
                            event = ProgressEvent.PAUSED
                        elif item.status == ProgressStatus.SKIPPED:
                            event = ProgressEvent.SKIPPED
                        else:
                            event = ProgressEvent.UPDATED
                            
                        # Prepare update message
                        update_message = {
                            "type": "progress_update",
                            "client_id": session_id,
                            "event": event.value,
                            "item_id": item.id,
                            "item_type": item.type.value,
                            "name": item.name,
                            "status": item.status.value,
                            "progress": item.percent_complete,
                            "workflow_id": workflow_id,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                        
                        # Add time estimation if available
                        if item.estimated_completion_time:
                            update_message["estimated_completion"] = item.estimated_completion_time.isoformat()
                            
                        # Broadcast to client
                        try:
                            await websocket_manager.broadcast(update_message, session_id)
                        except Exception as e:
                            logger.warning(f"Error broadcasting to {session_id}: {e}")
        
        except asyncio.CancelledError:
            logger.debug("Broadcast loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in broadcast loop: {e}")


# Create a global instance for convenience
progress_tracker = None

def init_progress_tracker(
    state_manager_instance=None,
    persistence_dir=None,
    checkpoint_interval=30,
    broadcast_interval=2
):
    """Initialize the global progress tracker.
    
    Args:
        state_manager_instance: The state manager to use
        persistence_dir: Directory for persistence files
        checkpoint_interval: Interval in seconds for automatic checkpoints
        broadcast_interval: Interval in seconds for broadcasting updates
        
    Returns:
        The initialized progress tracker
    """
    global progress_tracker
    
    # Create progress tracker if not already initialized
    if progress_tracker is None:
        progress_tracker = ProgressTracker(
            state_manager=state_manager_instance,
            persistence_dir=persistence_dir,
            checkpoint_interval=checkpoint_interval,
            broadcast_interval=broadcast_interval,
        )
        
    return progress_tracker


# Context manager for tracking progress
class track_progress:
    """Context manager for tracking progress of a workflow step.
    
    Usage:
    ```python
    with track_progress("My step", parent_id=workflow_id, total_work=100.0) as progress:
        # Do work...
        progress.update(25.0)  # 25% complete
        
        # More work...
        progress.increment(25.0)  # 50% complete
        
        # Even more work...
        progress.update(100.0)  # 100% complete
    ```
    """
    
    def __init__(
        self,
        name: str,
        parent_id: str,
        description: str = "",
        weight: float = 1.0,
        total_work: float = 100.0,
        type: ProgressItemType = ProgressItemType.STEP,
        auto_start: bool = True,
        item_id: Optional[str] = None,
    ):
        """Initialize the progress tracker context manager.
        
        Args:
            name: Name of the progress item
            parent_id: ID of the parent item
            description: Description of the progress item
            weight: Relative importance weight
            total_work: Total work units
            type: Type of progress item (step, subtask, operation)
            auto_start: Whether to automatically start progress when entering context
            item_id: Optional specific ID for the item
        """
        self.name = name
        self.parent_id = parent_id
        self.description = description
        self.weight = weight
        self.total_work = total_work
        self.type = type
        self.auto_start = auto_start
        self.item_id = item_id
        self.created_item_id = None
        
        # Ensure we have a progress tracker
        global progress_tracker
        if progress_tracker is None:
            progress_tracker = init_progress_tracker()
            
        self.tracker = progress_tracker
    
    def __enter__(self):
        """Enter the context manager and create/start the progress item."""
        # Create appropriate item type
        if self.type == ProgressItemType.STEP:
            self.created_item_id = self.tracker.create_step(
                workflow_id=self.parent_id,
                name=self.name,
                description=self.description,
                weight=self.weight,
                total_work=self.total_work,
                step_id=self.item_id,
            )
        elif self.type == ProgressItemType.SUBTASK:
            self.created_item_id = self.tracker.create_subtask(
                parent_id=self.parent_id,
                name=self.name,
                description=self.description,
                weight=self.weight,
                total_work=self.total_work,
                subtask_id=self.item_id,
            )
        elif self.type == ProgressItemType.OPERATION:
            self.created_item_id = self.tracker.create_operation(
                parent_id=self.parent_id,
                name=self.name,
                description=self.description,
                weight=self.weight,
                total_work=self.total_work,
                operation_id=self.item_id,
            )
        else:
            raise ValueError(f"Unsupported progress item type: {self.type}")
            
        # Auto-start if requested
        if self.auto_start:
            self.tracker.start_item(self.created_item_id)
            
        # Return self as progress tracker interface
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and complete/fail the progress item."""
        if exc_type is not None:
            # An exception occurred, mark as failed
            error_message = str(exc_val) if exc_val else "Unknown error"
            self.tracker.fail_item(self.created_item_id, error_message)
        else:
            # No exception, ensure item is completed
            item = self.tracker.state.get_item(self.created_item_id)
            if item and item.percent_complete < 100.0:
                self.tracker.complete_item(self.created_item_id)
    
    def update(self, progress: float):
        """Update absolute progress value.
        
        Args:
            progress: Absolute progress value (0.0 - 100.0)
        """
        self.tracker.update_progress(self.created_item_id, progress)
    
    def increment(self, increment: float):
        """Increment progress by given amount.
        
        Args:
            increment: Amount to increment progress by
        """
        self.tracker.increment_progress(self.created_item_id, increment)
    
    def complete(self):
        """Mark the item as completed."""
        self.tracker.complete_item(self.created_item_id)
    
    def fail(self, error_message: Optional[str] = None):
        """Mark the item as failed.
        
        Args:
            error_message: Optional error message describing the failure
        """
        self.tracker.fail_item(self.created_item_id, error_message)
    
    def pause(self):
        """Pause progress on the item."""
        self.tracker.pause_item(self.created_item_id)
    
    def resume(self):
        """Resume progress on the item."""
        self.tracker.resume_item(self.created_item_id)