# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field
from fastapi import HTTPException, status
import logging
from datetime import datetime
from core.tools.secrets_manager import secrets
from core.tools.memory_manager import MemoryManager
from core.tools.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

class TaskContext(BaseModel):
    """Context for task execution including environment and requirements"""
    environment: Dict[str, Any] = Field(default_factory=dict)
    requirements: List[str] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    artifacts: Dict[str, Any] = Field(default_factory=dict)

class TaskRequest(BaseModel):
    """Enhanced task request model with portfolio-specific fields"""
    task_id: str
    description: str
    requirements: List[str]
    constraints: Optional[Dict[str, Any]] = None
    priority: Optional[str] = "medium"
    deadline: Optional[datetime] = None
    context: Optional[TaskContext] = None

class SuperAgent:
    def __init__(self):
        """
        Initializes the SuperAgent with active task tracking, memory management, and tool registry.
        """
        self.active_tasks: Dict[str, Any] = {}
        self.memory_manager = MemoryManager()
        self.tool_registry = ToolRegistry()
        
    async def analyze_task_requirements(self, task: TaskRequest) -> Dict[str, Any]:
        """
        Performs an asynchronous analysis of a task to determine its complexity, required tools, dependencies, estimated duration, and risk factors.
        
        Args:
            task: The task to be analyzed.
        
        Returns:
            A dictionary containing the task's complexity, required tools, dependencies, estimated duration, and risk factors.
        
        Raises:
            HTTPException: If the analysis fails due to an internal error.
        """
        try:
            analysis = {
                "complexity": self._assess_complexity(task),
                "required_tools": await self._identify_required_tools(task),
                "dependencies": await self._identify_dependencies(task),
                "estimated_duration": self._estimate_duration(task),
                "risk_factors": self._identify_risks(task)
            }
            return analysis
        except Exception as e:
            logger.error(f"Task analysis failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Task analysis failed: {str(e)}"
            )

    async def assign_roles(self, task: TaskRequest) -> Dict[str, List[str]]:
        """
        Assigns agent roles to a task based on dynamically analyzed requirements.
        
        Analyzes the task to determine necessary capabilities and assigns agents to primary and monitoring roles according to required tools. Always includes an inspector agent for monitoring.
        
        Args:
            task: The task request containing details for role assignment.
        
        Returns:
            A dictionary mapping role categories ("primary", "support", "monitoring") to lists of assigned agent names.
        """
        try:
            analysis = await self.analyze_task_requirements(task)
            roles = {
                "primary": [],
                "support": [],
                "monitoring": []
            }
            
            # Assign roles based on task analysis
            if "documentation" in analysis["required_tools"]:
                roles["primary"].append("codifier_agent")
            if "testing" in analysis["required_tools"]:
                roles["primary"].append("test_engineer_agent")
            if "ui_design" in analysis["required_tools"]:
                roles["primary"].append("ux_designer_agent")
            
            # Always include monitoring
            roles["monitoring"].append("inspector_agent")
            
            return roles
        except Exception as e:
            logger.error(f"Role assignment failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Role assignment failed: {str(e)}"
            )

    async def allocate_tools(self, roles: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Allocates tools to each assigned agent role.
        
        Args:
            roles: A mapping of role names to lists of agent identifiers.
        
        Returns:
            A dictionary mapping agent identifiers to lists of allocated tools.
        """
        try:
            # Implement tool allocation logic
            tool_allocation = {
                "inspector_agent": ["monitoring", "analysis", "reporting"],
                "journey_agent": ["execution", "coordination"]
            }
            return tool_allocation
        except Exception as e:
            logger.error(f"Tool allocation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Tool allocation failed: {str(e)}"
            )
    
    async def create_execution_plan(
        self, 
        task: TaskRequest,
        roles: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Creates a detailed multi-phase execution plan for a task, including sequential and parallel phases, assigned agents, actions, and error handling strategies.
        
        The plan is structured into initialization, planning, execution, validation, and deployment phases, with actions and agents determined by task analysis. The plan is stored in memory for tracking and supports parallel processing where applicable.
        
        Args:
            task: The task request containing task details and requirements.
            roles: Mapping of roles to assigned agents for the task.
        
        Returns:
            A dictionary representing the structured execution plan for the task.
        
        Raises:
            HTTPException: If plan creation fails due to an internal error.
        """
        try:
            analysis = await self.analyze_task_requirements(task)
            
            plan = {
                "task_id": task.task_id,
                "phases": [
                    {
                        "name": "initialization",
                        "type": "sequential",
                        "agent": "inspector_agent",
                        "actions": [
                            "validate_requirements",
                            "setup_monitoring",
                            "initialize_workspace"
                        ]
                    },
                    {
                        "name": "planning",
                        "type": "parallel",
                        "actions": [
                            {
                                "name": "design_architecture",
                                "agent": "ux_designer_agent",
                                "dependencies": []
                            },
                            {
                                "name": "setup_testing",
                                "agent": "test_engineer_agent",
                                "dependencies": []
                            }
                        ]
                    },
                    {
                        "name": "execution",
                        "type": "parallel",
                        "actions": self._generate_execution_actions(analysis)
                    },
                    {
                        "name": "validation",
                        "type": "sequential",
                        "agent": "inspector_agent",
                        "actions": [
                            "run_tests",
                            "validate_documentation",
                            "performance_check"
                        ]
                    },
                    {
                        "name": "deployment",
                        "type": "sequential",
                        "agent": "journey_agent",
                        "actions": [
                            "prepare_deployment",
                            "execute_deployment",
                            "verify_deployment"
                        ]
                    }
                ],
                "error_handling": {
                    "retry_count": 3,
                    "fallback_strategy": "human_intervention"
                }
            }
            
            # Store plan in memory for tracking
            await self.memory_manager.store_execution_plan(task.task_id, plan)
            
            return plan
        except Exception as e:
            logger.error(f"Plan creation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Plan creation failed: {str(e)}"
            )

    def _generate_execution_actions(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generates a list of execution actions based on the required tools identified in the task analysis.
        
        Args:
            analysis: The analysis dictionary containing required tools for the task.
        
        Returns:
            A list of action dictionaries specifying the action name, responsible agent, and dependencies.
        """
        actions = []
        
        if "documentation" in analysis["required_tools"]:
            actions.append({
                "name": "generate_documentation",
                "agent": "codifier_agent",
                "dependencies": ["design_architecture"]
            })
            
        if "testing" in analysis["required_tools"]:
            actions.append({
                "name": "implement_tests",
                "agent": "test_engineer_agent",
                "dependencies": ["design_architecture"]
            })
            
        return actions

    async def execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes an execution plan phase by phase, supporting both sequential and parallel processing.
        
        Each phase is executed according to its type, with parallel phases handled concurrently. Execution metrics are updated after each phase. Returns the results of all phases along with updated metrics. Raises an HTTP 500 exception if execution fails.
        """
        try:
            results = {
                "task_id": plan["task_id"],
                "phases": [],
                "metrics": {}
            }
            
            for phase in plan["phases"]:
                if phase["type"] == "parallel":
                    phase_result = await self._execute_parallel_phase(phase)
                else:
                    phase_result = await self.execute_phase(phase)
                results["phases"].append(phase_result)
                
                # Update metrics after each phase
                results["metrics"] = await self.get_execution_metrics(plan["task_id"])
            
            return results
        except Exception as e:
            logger.error(f"Plan execution failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Plan execution failed: {str(e)}"
            )

    async def _execute_parallel_phase(self, phase: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes all actions within a phase concurrently and returns their results.
        
        Args:
            phase: A dictionary representing the phase, containing its name and a list of actions to execute in parallel.
        
        Returns:
            A dictionary with the phase name, type, and the results of all executed actions.
        """
        try:
            results = {
                "name": phase["name"],
                "type": "parallel",
                "actions": []
            }
            
            # Execute actions in parallel using asyncio.gather
            import asyncio
            action_results = await asyncio.gather(
                *[self.execute_action(action) for action in phase["actions"]]
            )
            
            results["actions"] = action_results
            return results
        except Exception as e:
            logger.error(f"Parallel phase execution failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Parallel phase execution failed: {str(e)}"
            )

    async def execute_phase(self, phase: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes all actions in a single phase sequentially and returns their results.
        
        Args:
            phase: A dictionary containing the phase's name, assigned agent, and a list of actions to execute.
        
        Returns:
            A dictionary with the phase name, agent, and a list of results for each executed action.
        
        Raises:
            HTTPException: If execution of any action in the phase fails.
        """
        try:
            results = {
                "name": phase["name"],
                "agent": phase["agent"],
                "actions": []
            }
            
            for action in phase["actions"]:
                action_result = await self.execute_action(action)
                results["actions"].append(action_result)
            
            return results
        except Exception as e:
            logger.error(f"Phase execution failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Phase execution failed: {str(e)}"
            )
    
    async def execute_action(self, action: str) -> Dict[str, Any]:
        """Execute a single action."""
        try:
            # Implement action execution logic
            return {
                "action": action,
                "status": "completed",
                "result": f"Executed {action} successfully"
            }
        except Exception as e:
            logger.error(f"Action execution failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Action execution failed: {str(e)}"
            )
    
    async def get_execution_metrics(self, task_id: str) -> Dict[str, Any]:
        """Get metrics for task execution."""
        try:
            # Implement metrics collection logic
            return {
                "task_id": task_id,
                "duration": "00:05:23",
                "resource_usage": {
                    "cpu": "45%",
                    "memory": "128MB"
                },
                "success_rate": "98%"
            }
        except Exception as e:
            logger.error(f"Metrics collection failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Metrics collection failed: {str(e)}"
            )
    
    async def orchestrate_task(self, task: TaskRequest) -> Dict[str, Any]:
        """Orchestrate task execution using available agents and tools."""
        try:
            # Analyze task and assign roles
            roles = await self.assign_roles(task)
            
            # Allocate tools to roles
            tool_allocation = await self.allocate_tools(roles)
            
            # Create and execute plan
            plan = await self.create_execution_plan(task, roles)
            results = await self.execute_plan(plan)
            
            return {
                "status": "success",
                "task_id": task.task_id,
                "results": results,
                "metrics": await self.get_execution_metrics(task.task_id)
            }
        except Exception as e:
            logger.error(f"Task orchestration failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Task orchestration failed: {str(e)}"
            )
