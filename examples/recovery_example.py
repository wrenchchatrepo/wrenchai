"""Example demonstrating the recovery system.

This example shows how to use the recovery system for workflow error handling,
including different recovery strategies and error handling patterns.
"""

import asyncio
import logging
import random
import time
from typing import Dict, Any

from core.state_manager import state_manager, StateScope
from core.recovery_system import (
    init_recovery_manager, RecoveryCallback, RecoveryContext, 
    RecoveryAction, ErrorCategory, with_recovery
)


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("recovery_example")


class CustomRecoveryCallback(RecoveryCallback):
    """Custom callback for recovery events."""
    
    async def pre_recovery(self, context: RecoveryContext) -> None:
        """Called before recovery attempt."""
        logger.info(f"Recovery attempt starting for error: {str(context.error)[:100]}...")
        
    async def post_recovery(self, context: RecoveryContext, action: RecoveryAction, success: bool) -> None:
        """Called after recovery attempt."""
        logger.info(f"Recovery completed with action {action.value}, success: {success}")
        
    async def on_abort(self, context: RecoveryContext) -> None:
        """Called when workflow is aborted."""
        logger.warning(f"Workflow aborted due to unrecoverable error: {context.error}")


async def unstable_operation(fail_probability: float = 0.7) -> str:
    """Simulates an unstable operation that might fail.
    
    Args:
        fail_probability: Probability of failure (0.0 to 1.0)
        
    Returns:
        Operation result
        
    Raises:
        Various exceptions based on random chance
    """
    # Simulate work
    await asyncio.sleep(0.2)
    
    # Potentially fail
    if random.random() < fail_probability:
        error_types = [
            (ValueError, "Invalid value encountered", ErrorCategory.STATE_INVALID),
            (TimeoutError, "Operation timed out", ErrorCategory.TIMEOUT),
            (ConnectionError, "Failed to connect to service", ErrorCategory.TRANSIENT),
            (RuntimeError, "Unexpected runtime error", ErrorCategory.UNKNOWN),
        ]
        
        error_class, message, _ = random.choice(error_types)
        raise error_class(message)
        
    return "Operation completed successfully"


async def alternate_calculation(context: RecoveryContext) -> None:
    """Alternate path for calculation step.
    
    Args:
        context: Recovery context
    """
    logger.info("Executing alternate calculation path")
    
    # Get workflow state from recovery context
    workflow_id = context.workflow_id
    
    # Put some default result in the state
    state_manager.set_variable_value(
        f"{workflow_id}_calculation_result",
        "Default result from alternate path",
        requestor=workflow_id
    )


async def run_workflow(workflow_id: str) -> Dict[str, Any]:
    """Run a sample workflow with error recovery.
    
    Args:
        workflow_id: Unique ID for the workflow
        
    Returns:
        Workflow results
    """
    logger.info(f"Starting workflow {workflow_id}")
    
    # Initialize the recovery manager
    recovery_manager = init_recovery_manager()
    
    # Register our custom callback
    recovery_manager.register_callback(CustomRecoveryCallback())
    
    # Set up an alternate path strategy
    alternate_path_strategy = next(
        s for s in recovery_manager._strategies 
        if s.name == "alternate_path"
    )
    alternate_path_strategy.register_alternate_path("calculation_step", alternate_calculation)
    
    # Initialize workflow state
    state_manager.create_variable(
        f"{workflow_id}_input", 
        "Sample input data",
        scope=StateScope.WORKFLOW
    )
    
    try:
        # Step 1: Data preparation
        logger.info("Executing data preparation step")
        data_prep_result = await with_recovery(
            recovery_manager,
            workflow_id,
            "data_preparation_step",
            unstable_operation,
            fail_probability=0.3
        )
        
        state_manager.create_variable(
            f"{workflow_id}_data_prep_result",
            data_prep_result,
            scope=StateScope.WORKFLOW
        )
        
        # Step 2: Calculation (more likely to fail)
        logger.info("Executing calculation step")
        try:
            calculation_result = await with_recovery(
                recovery_manager,
                workflow_id,
                "calculation_step",
                unstable_operation,
                fail_probability=0.8
            )
            
            state_manager.create_variable(
                f"{workflow_id}_calculation_result",
                calculation_result,
                scope=StateScope.WORKFLOW
            )
        except Exception as e:
            logger.warning(f"Calculation step failed permanently: {e}")
            # Alternate path was likely used, check state for result
        
        # Step 3: Finalization
        logger.info("Executing finalization step")
        finalization_result = await with_recovery(
            recovery_manager,
            workflow_id,
            "finalization_step",
            unstable_operation,
            fail_probability=0.4
        )
        
        state_manager.create_variable(
            f"{workflow_id}_finalization_result",
            finalization_result,
            scope=StateScope.WORKFLOW
        )
        
        # Collect results
        results = {}
        for name in [f"{workflow_id}_data_prep_result", 
                    f"{workflow_id}_calculation_result",
                    f"{workflow_id}_finalization_result"]:
            try:
                results[name] = state_manager.get_variable_value(name)
            except:
                results[name] = "Not available"
                
        logger.info(f"Workflow {workflow_id} completed with results: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Workflow {workflow_id} failed: {e}")
        return {"error": str(e), "status": "failed"}
    finally:
        # Get recovery history
        history = recovery_manager.get_recovery_history(workflow_id)
        logger.info(f"Recovery events: {len(history)}")


async def main():
    """Run multiple workflow instances."""
    workflows = []
    for i in range(3):
        workflow_id = f"workflow_{i}_{int(time.time())}"
        workflows.append(run_workflow(workflow_id))
        
    await asyncio.gather(*workflows)


if __name__ == "__main__":
    asyncio.run(main())