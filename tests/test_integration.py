"""
Integration tests for the WrenchAI system.

These tests verify the integration between different components:
1. Agent-to-agent communication
2. Database integration
3. API endpoints
4. Tool integration
5. End-to-end workflows
6. Portfolio workflows
7. Multi-agent collaboration
8. Tool chain integration
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List
import json
import os
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from wrenchai.core.agents.super_agent import SuperAgent
from wrenchai.core.agents.journey_agent import JourneyAgent
from wrenchai.core.agents.codifier_agent import Codifier
from wrenchai.core.agents.test_engineer_agent import TestEngineer
from wrenchai.core.agent_system import AgentManager
from wrenchai.core.tools.tool_registry import ToolRegistry
from wrenchai.core.db.models import Base
from wrenchai.fastapi.app.main import app
from wrenchai.core.tools.secrets_manager import secrets

# Test database URL
TEST_DB_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture
async def test_db():
    """Create a test database and tables."""
    engine = create_async_engine(TEST_DB_URL, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    # Cleanup
    await engine.dispose()
    if os.path.exists("./test.db"):
        os.remove("./test.db")

@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def mock_secrets():
    """Mock the secrets manager."""
    with patch('wrenchai.core.tools.secrets_manager.secrets') as mock:
        mock.get_secret.return_value = "test-secret"
        yield mock

@pytest.fixture
def agent_manager():
    """Create an agent manager with test configuration."""
    manager = AgentManager(config_dir="tests/test_configs")
    tool_registry = ToolRegistry()
    manager.set_tool_registry(tool_registry)
    return manager

class TestAgentCommunication:
    """Test agent-to-agent communication."""
    
    @pytest.mark.asyncio
    async def test_agent_message_passing(self, agent_manager):
        """Test that agents can pass messages between each other."""
        # Initialize agents
        super_agent = agent_manager.initialize_agent("SuperAgent")
        journey_agent = agent_manager.initialize_agent("JourneyAgent")
        
        # Create a test message
        message = {
            "type": "task_assignment",
            "content": "Create a new repository",
            "metadata": {"priority": "high"}
        }
        
        # Send message from super agent to journey agent
        response = await super_agent.send_message(journey_agent.id, message)
        
        # Verify message was received and processed
        assert response["status"] == "success"
        assert "message_id" in response
        
        # Check journey agent received the message
        received = await journey_agent.get_messages()
        assert len(received) > 0
        assert received[0]["content"] == message["content"]
    
    @pytest.mark.asyncio
    async def test_multi_agent_collaboration(self, agent_manager):
        """Test multiple agents collaborating on a task."""
        # Initialize agents
        super_agent = agent_manager.initialize_agent("SuperAgent")
        journey_agent = agent_manager.initialize_agent("JourneyAgent")
        codifier = agent_manager.initialize_agent("Codifier")
        
        # Create a collaborative task
        task = {
            "type": "documentation",
            "content": "Document the API endpoints",
            "workflow": ["analyze", "document", "review"]
        }
        
        # Start the collaboration
        workflow_result = await super_agent.coordinate_task(
            task,
            [journey_agent.id, codifier.id]
        )
        
        # Verify workflow completion
        assert workflow_result["status"] == "completed"
        assert "documentation" in workflow_result["outputs"]
        assert workflow_result["participants"] == [journey_agent.id, codifier.id]

class TestDatabaseIntegration:
    """Test database integration with the system."""
    
    @pytest.mark.asyncio
    async def test_agent_state_persistence(self, test_db, agent_manager):
        """Test that agent state can be persisted to the database."""
        # Initialize an agent
        agent = agent_manager.initialize_agent("JourneyAgent")
        
        # Create some agent state
        state = {
            "task_id": "test-task",
            "status": "in_progress",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Save state to database
        await agent.save_state(test_db, state)
        
        # Retrieve state from database
        loaded_state = await agent.load_state(test_db)
        
        # Verify state was persisted correctly
        assert loaded_state["task_id"] == state["task_id"]
        assert loaded_state["status"] == state["status"]
    
    @pytest.mark.asyncio
    async def test_workflow_history_tracking(self, test_db, agent_manager):
        """Test tracking of workflow history in the database."""
        # Initialize workflow
        workflow_id = "test-workflow"
        agents = [
            agent_manager.initialize_agent("SuperAgent"),
            agent_manager.initialize_agent("JourneyAgent")
        ]
        
        # Create some workflow steps
        steps = [
            {"step_id": 1, "action": "initialize", "status": "completed"},
            {"step_id": 2, "action": "process", "status": "in_progress"}
        ]
        
        # Record workflow history
        for step in steps:
            await agent_manager.record_workflow_step(
                test_db,
                workflow_id,
                step,
                [agent.id for agent in agents]
            )
        
        # Retrieve workflow history
        history = await agent_manager.get_workflow_history(test_db, workflow_id)
        
        # Verify history was recorded correctly
        assert len(history) == len(steps)
        assert history[0]["step_id"] == steps[0]["step_id"]
        assert history[1]["status"] == steps[1]["status"]

class TestAPIEndpoints:
    """Test API endpoint integration."""
    
    def test_agent_api_endpoints(self, test_client):
        """Test agent-related API endpoints."""
        # Test creating a new agent
        response = test_client.post(
            "/api/v1/agents/",
            json={
                "role": "JourneyAgent",
                "name": "test-journey-agent",
                "tools": ["web_search", "code_generation"]
            }
        )
        assert response.status_code == 200
        agent_id = response.json()["agent_id"]
        
        # Test getting agent status
        response = test_client.get(f"/api/v1/agents/{agent_id}/status")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"
        
        # Test assigning a task to the agent
        response = test_client.post(
            f"/api/v1/agents/{agent_id}/tasks",
            json={
                "type": "analysis",
                "content": "Analyze the codebase"
            }
        )
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        
        # Test getting task status
        response = test_client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        assert "status" in response.json()
    
    def test_workflow_api_endpoints(self, test_client):
        """Test workflow-related API endpoints."""
        # Test creating a new workflow
        response = test_client.post(
            "/api/v1/workflows/",
            json={
                "name": "test-workflow",
                "description": "Test workflow",
                "steps": [
                    {
                        "step_id": 1,
                        "action": "initialize",
                        "agent_role": "SuperAgent"
                    }
                ]
            }
        )
        assert response.status_code == 200
        workflow_id = response.json()["workflow_id"]
        
        # Test getting workflow status
        response = test_client.get(f"/api/v1/workflows/{workflow_id}")
        assert response.status_code == 200
        assert "status" in response.json()
        
        # Test updating workflow
        response = test_client.put(
            f"/api/v1/workflows/{workflow_id}",
            json={"status": "completed"}
        )
        assert response.status_code == 200
        
        # Test listing workflows
        response = test_client.get("/api/v1/workflows/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

class TestToolIntegration:
    """Test integration with various tools."""
    
    @pytest.mark.asyncio
    async def test_tool_registry_integration(self, agent_manager):
        """Test that agents can access and use tools from the registry."""
        # Initialize an agent with tools
        agent = agent_manager.initialize_agent(
            "JourneyAgent",
            mcp_servers=["github", "run-python"]
        )
        
        # Test tool availability
        tools = agent.get_available_tools()
        assert "github" in tools
        assert "run-python" in tools
        
        # Test tool execution
        result = await agent.execute_tool(
            "github",
            "list_repositories",
            {"owner": "test-org"}
        )
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_tool_error_handling(self, agent_manager):
        """Test handling of tool execution errors."""
        agent = agent_manager.initialize_agent("JourneyAgent")
        
        # Test handling of missing tool
        with pytest.raises(ValueError):
            await agent.execute_tool(
                "nonexistent_tool",
                "some_action",
                {}
            )
        
        # Test handling of invalid parameters
        with pytest.raises(ValueError):
            await agent.execute_tool(
                "github",
                "list_repositories",
                {"invalid_param": "value"}
            )

class TestEndToEndWorkflows:
    """Test end-to-end workflows."""
    
    @pytest.mark.asyncio
    async def test_documentation_workflow(self, agent_manager, test_db):
        """Test the complete documentation workflow."""
        # Initialize the workflow
        workflow_id = "doc-workflow-test"
        workflow_config = {
            "name": "Documentation Generation",
            "steps": [
                {
                    "step_id": "analyze",
                    "agent": "JourneyAgent",
                    "action": "analyze_codebase"
                },
                {
                    "step_id": "document",
                    "agent": "Codifier",
                    "action": "generate_documentation"
                },
                {
                    "step_id": "test",
                    "agent": "TestEngineer",
                    "action": "validate_documentation"
                }
            ]
        }
        
        # Run the workflow
        result = await agent_manager.run_workflow(
            workflow_id,
            workflow_config,
            {"codebase_path": "./tests/test_data"}
        )
        
        # Verify workflow completion
        assert result["status"] == "completed"
        assert "documentation" in result["outputs"]
        assert result["outputs"]["documentation"]["validation"]["passed"]
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, agent_manager, test_db):
        """
        Tests that a workflow can recover from errors using retries and a fallback action.
        
        Initializes a workflow designed to trigger an error, verifies that recovery attempts occur,
        and asserts that the workflow completes successfully via the specified fallback path.
        """
        # Initialize workflow with intentional error
        workflow_id = "error-recovery-test"
        workflow_config = {
            "name": "Error Recovery Test",
            "steps": [
                {
                    "step_id": "error_step",
                    "agent": "JourneyAgent",
                    "action": "trigger_error",
                    "recovery": {
                        "max_retries": 3,
                        "fallback_action": "alternative_path"
                    }
                }
            ]
        }
        
        # Run the workflow
        result = await agent_manager.run_workflow(
            workflow_id,
            workflow_config,
            {"trigger_recovery": True}
        )
        
        # Verify error recovery
        assert result["status"] == "completed"
        assert result["recovery_attempts"] > 0
        assert result["final_path"] == "alternative_path"

class TestPortfolioWorkflows:
    """Test portfolio-specific end-to-end workflows."""
    
    @pytest.mark.asyncio
    async def test_portfolio_creation_workflow(self, agent_manager, test_db, mock_secrets):
        """
        Tests the end-to-end workflow for creating a portfolio using multiple agents.
        
        Initializes required agents, coordinates a portfolio creation task, and verifies that the workflow completes successfully with expected output URLs and correct database entries for the created portfolio.
        """
        # Initialize required agents
        super_agent = agent_manager.initialize_agent("SuperAgent")
        journey_agent = agent_manager.initialize_agent("JourneyAgent")
        codifier = agent_manager.initialize_agent("Codifier")
        
        # Create portfolio creation task
        task = {
            "type": "portfolio_creation",
            "content": {
                "title": "Test Portfolio",
                "sections": ["About", "Projects", "Skills"],
                "theme": "modern",
                "deployment": "github-pages"
            }
        }
        
        # Execute the workflow
        result = await super_agent.coordinate_task(
            task,
            [journey_agent.id, codifier.id]
        )
        
        # Verify portfolio creation
        assert result["status"] == "completed"
        assert "repository_url" in result["outputs"]
        assert "deployment_url" in result["outputs"]
        
        # Verify database entries
        portfolio = await agent_manager.get_portfolio(test_db, result["portfolio_id"])
        assert portfolio["title"] == task["content"]["title"]
        assert portfolio["status"] == "published"
    
    @pytest.mark.asyncio
    async def test_content_update_workflow(self, agent_manager, test_db, mock_secrets):
        """
        Tests the workflow for updating portfolio content and verifies database and repository changes.
        
        This test initializes a portfolio, performs a content update via an agent, and checks that the update is reflected in the portfolio's content and that a corresponding git commit is created.
        """
        # Initialize portfolio with existing content
        portfolio_id = await self._create_test_portfolio(test_db)
        
        # Initialize agents
        journey_agent = agent_manager.initialize_agent("JourneyAgent")
        
        # Create update task
        update_task = {
            "type": "content_update",
            "portfolio_id": portfolio_id,
            "changes": {
                "section": "Projects",
                "action": "add",
                "content": {
                    "title": "New Project",
                    "description": "Test project description",
                    "technologies": ["Python", "FastAPI"]
                }
            }
        }
        
        # Execute update
        result = await journey_agent.process_task(update_task)
        
        # Verify updates
        assert result["status"] == "completed"
        updated_portfolio = await agent_manager.get_portfolio(test_db, portfolio_id)
        assert "New Project" in str(updated_portfolio["content"])
        
        # Verify git commits
        commits = await agent_manager.get_repository_commits(portfolio_id)
        assert len(commits) > 0
        assert "Update Projects section" in commits[0]["message"]
    
    @pytest.mark.asyncio
    async def test_deployment_workflow(self, agent_manager, test_db, mock_secrets):
        """
        Tests the end-to-end deployment workflow for a portfolio.
        
        Initializes a test portfolio and relevant agents, coordinates a deployment task to the production environment, and verifies successful completion, deployment URL, check statuses, and the presence of deployment logs indicating success.
        """
        # Initialize portfolio
        portfolio_id = await self._create_test_portfolio(test_db)
        
        # Initialize agents
        super_agent = agent_manager.initialize_agent("SuperAgent")
        test_engineer = agent_manager.initialize_agent("TestEngineer")
        
        # Create deployment task
        deploy_task = {
            "type": "deployment",
            "portfolio_id": portfolio_id,
            "environment": "production",
            "checks": ["lint", "test", "build"]
        }
        
        # Execute deployment
        result = await super_agent.coordinate_deployment(
            deploy_task,
            test_engineer.id
        )
        
        # Verify deployment
        assert result["status"] == "completed"
        assert result["deployment"]["url"].startswith("https://")
        assert result["checks"]["status"] == "passed"
        
        # Verify deployment logs
        logs = await agent_manager.get_deployment_logs(result["deployment"]["id"])
        assert len(logs) > 0
        assert any("Deployment successful" in log["message"] for log in logs)
    
    async def _create_test_portfolio(self, test_db) -> str:
        """
        Creates a draft test portfolio in the database and returns its ID.
        
        Args:
            test_db: The test database session or connection.
        
        Returns:
            The ID of the newly created test portfolio.
        """
        portfolio_data = {
            "title": "Test Portfolio",
            "content": {"About": "Test content"},
            "status": "draft"
        }
        portfolio_id = await agent_manager.create_portfolio(test_db, portfolio_data)
        return portfolio_id

class TestMultiAgentCollaboration:
    """Test advanced multi-agent collaboration scenarios."""
    
    @pytest.mark.asyncio
    async def test_task_handoff_verification(self, agent_manager, test_db):
        """
        Verifies that tasks are correctly handed off and completed across multiple agents in a staged workflow.
        
        This test initializes several agents, creates a multi-stage feature implementation task, executes it through the workflow, and asserts that each stage transition is completed with appropriate handoff metadata.
        """
        # Initialize agents
        super_agent = agent_manager.initialize_agent("SuperAgent")
        journey_agent = agent_manager.initialize_agent("JourneyAgent")
        codifier = agent_manager.initialize_agent("Codifier")
        test_engineer = agent_manager.initialize_agent("TestEngineer")
        
        # Create a multi-stage task
        task = {
            "type": "feature_implementation",
            "stages": [
                {"role": "JourneyAgent", "action": "plan"},
                {"role": "Codifier", "action": "implement"},
                {"role": "TestEngineer", "action": "test"}
            ]
        }
        
        # Execute the workflow
        result = await super_agent.execute_staged_task(task)
        
        # Verify task transitions
        transitions = await agent_manager.get_task_transitions(result["task_id"])
        assert len(transitions) == len(task["stages"])
        for transition in transitions:
            assert transition["status"] == "completed"
            assert "handoff_metadata" in transition
    
    @pytest.mark.asyncio
    async def test_state_synchronization(self, agent_manager, test_db):
        """
        Verifies that shared state updates are synchronized across multiple collaborating agents.
        
        Initializes agents with a shared state, performs updates through each agent, and asserts that all agents observe the latest state changes.
        """
        # Initialize agents with shared state
        agents = [
            agent_manager.initialize_agent("JourneyAgent"),
            agent_manager.initialize_agent("Codifier")
        ]
        
        # Create shared state
        shared_state = {
            "project_config": {"key": "value"},
            "progress": 0
        }
        
        # Update state through different agents
        for i, agent in enumerate(agents):
            update = {"progress": (i + 1) * 50}
            await agent.update_shared_state(shared_state["id"], update)
            
            # Verify all agents see the update
            for other_agent in agents:
                state = await other_agent.get_shared_state(shared_state["id"])
                assert state["progress"] == update["progress"]
    
    @pytest.mark.asyncio
    async def test_error_propagation(self, agent_manager, test_db):
        """
        Tests that errors triggered during multi-agent task processing are correctly handled,
        logged, propagated, and that all agents receive error notifications.
        
        Verifies that an invalid operation causes an exception, error logs are recorded,
        and all participating agents are notified of the error.
        """
        # Initialize agents
        agents = [
            agent_manager.initialize_agent("SuperAgent"),
            agent_manager.initialize_agent("JourneyAgent")
        ]
        
        # Create a task that will trigger an error
        task = {
            "type": "invalid_operation",
            "content": "This should fail"
        }
        
        # Execute task and verify error handling
        with pytest.raises(Exception) as exc_info:
            await agents[1].process_task(task)
        
        # Verify error was logged and propagated
        error_logs = await agent_manager.get_error_logs(task["id"])
        assert len(error_logs) > 0
        assert error_logs[0]["type"] == "InvalidOperationError"
        
        # Verify other agents were notified
        for agent in agents:
            notifications = await agent.get_notifications()
            assert any(n["type"] == "error" for n in notifications)

    @pytest.mark.asyncio
    async def test_concurrent_task_processing(self, agent_manager, test_db):
        """
        Tests that multiple agents can process different tasks concurrently, ensuring each task completes successfully and resources are properly released.
        
        Verifies that all tasks report a completed status and that task resources are unlocked after processing, confirming task isolation and correct resource management.
        """
        # Initialize agents
        agents = [
            agent_manager.initialize_agent("JourneyAgent"),
            agent_manager.initialize_agent("Codifier"),
            agent_manager.initialize_agent("TestEngineer")
        ]
        
        # Create concurrent tasks
        tasks = [
            {"type": "analysis", "content": "Analyze code"},
            {"type": "documentation", "content": "Generate docs"},
            {"type": "testing", "content": "Run tests"}
        ]
        
        # Execute tasks concurrently
        results = await asyncio.gather(*[
            agent.process_task(task)
            for agent, task in zip(agents, tasks)
        ])
        
        # Verify all tasks completed
        assert all(r["status"] == "completed" for r in results)
        
        # Verify task isolation
        for result in results:
            assert "task_resources" in result
            assert result["task_resources"]["locked"] is False
    
    @pytest.mark.asyncio
    async def test_resource_conflict_resolution(self, agent_manager, test_db):
        """
        Tests resolution of resource conflicts when two agents operate on the same resource concurrently.
        
        Verifies that at least one task completes, the resource lock is released after processing, and last access metadata is present in the resource status.
        """
        # Initialize agents
        agent1 = agent_manager.initialize_agent("JourneyAgent")
        agent2 = agent_manager.initialize_agent("Codifier")
        
        # Create tasks that require the same resource
        shared_resource = "test_file.py"
        tasks = [
            {
                "type": "edit",
                "resource": shared_resource,
                "content": "Edit file"
            },
            {
                "type": "analyze",
                "resource": shared_resource,
                "content": "Analyze file"
            }
        ]
        
        # Execute tasks with potential conflict
        results = await asyncio.gather(
            agent1.process_task(tasks[0]),
            agent2.process_task(tasks[1]),
            return_exceptions=True
        )
        
        # Verify conflict handling
        completed_tasks = [r for r in results if isinstance(r, dict)]
        assert len(completed_tasks) > 0
        
        # Check resource lock status
        resource_status = await agent_manager.get_resource_status(shared_resource)
        assert resource_status["locked"] is False
        assert "last_access" in resource_status

class TestToolChainIntegration:
    """Test integration of various tool chains."""
    
    @pytest.mark.asyncio
    async def test_github_workflow_integration(self, agent_manager, mock_secrets):
        """
        Tests end-to-end integration with GitHub workflows by creating a pull request and verifying workflow run completion.
        
        Initializes a journey agent, creates a GitHub workflow task to open a pull request with specified changes, executes the workflow, and asserts that the pull request is created successfully. Also verifies that at least one associated workflow run completes with a successful conclusion.
        """
        # Initialize agents
        journey_agent = agent_manager.initialize_agent("JourneyAgent")
        
        # Create a GitHub workflow task
        task = {
            "type": "github_workflow",
            "action": "create_pr",
            "content": {
                "title": "Test PR",
                "branch": "feature/test",
                "changes": [{"file": "test.md", "content": "Test content"}]
            }
        }
        
        # Execute the workflow
        result = await journey_agent.execute_github_workflow(task)
        
        # Verify PR creation
        assert result["status"] == "completed"
        assert "pr_number" in result
        assert "pr_url" in result
        
        # Verify workflow run
        workflow_runs = await agent_manager.get_github_workflow_runs(
            result["repository"],
            result["pr_number"]
        )
        assert len(workflow_runs) > 0
        assert workflow_runs[0]["conclusion"] == "success"
    
    @pytest.mark.asyncio
    async def test_documentation_generation_pipeline(self, agent_manager):
        """
        Tests the end-to-end documentation generation pipeline using the Codifier agent.
        
        Initializes the Codifier agent, creates a documentation generation task, executes the pipeline, and verifies that documentation files are generated with quality and coverage metrics meeting required thresholds.
        """
        # Initialize agents
        codifier = agent_manager.initialize_agent("Codifier")
        
        # Create documentation task
        task = {
            "type": "generate_docs",
            "source": "src/",
            "output": "docs/",
            "format": "markdown"
        }
        
        # Execute documentation generation
        result = await codifier.generate_documentation(task)
        
        # Verify documentation
        assert result["status"] == "completed"
        assert len(result["generated_files"]) > 0
        
        # Verify documentation quality
        quality_check = await codifier.verify_documentation_quality(
            result["generated_files"]
        )
        assert quality_check["score"] >= 0.8
        assert quality_check["coverage"] >= 0.9
    
    @pytest.mark.asyncio
    async def test_analytics_integration(self, agent_manager, test_db):
        """
        Tests end-to-end analytics pipeline integration, including data collection and processing.
        
        Initializes analytics configuration, executes an analytics collection task via the agent manager, verifies successful data collection, processes the collected metrics, and asserts the presence of insights and recommendations in the processed output.
        """
        # Initialize analytics configuration
        analytics_config = {
            "metrics": ["page_views", "interaction_time"],
            "dimensions": ["page", "user_type"],
            "period": "daily"
        }
        
        # Create analytics task
        task = {
            "type": "analytics_collection",
            "config": analytics_config
        }
        
        # Execute analytics collection
        result = await agent_manager.collect_analytics(task)
        
        # Verify data collection
        assert result["status"] == "completed"
        assert "metrics" in result
        assert len(result["metrics"]) > 0
        
        # Verify data processing
        processed_data = await agent_manager.process_analytics(
            result["metrics"],
            analytics_config
        )
        assert "insights" in processed_data
        assert "recommendations" in processed_data
    
    @pytest.mark.asyncio
    async def test_deployment_pipeline(self, agent_manager, test_db, mock_secrets):
        """
        Tests the end-to-end deployment pipeline workflow, including build, test, deploy steps, rollback strategy, and notifications.
        
        Initializes deployment agents, executes a deployment pipeline with specified configuration, and verifies successful completion, correct step execution, environment health, deployed version, and presence of deployment notifications.
        """
        # Initialize agents
        super_agent = agent_manager.initialize_agent("SuperAgent")
        test_engineer = agent_manager.initialize_agent("TestEngineer")
        
        # Create deployment configuration
        deploy_config = {
            "repository": "test-repo",
            "environment": "staging",
            "steps": [
                {"name": "build", "command": "npm run build"},
                {"name": "test", "command": "npm test"},
                {"name": "deploy", "command": "npm run deploy"}
            ],
            "rollback_strategy": {
                "enabled": True,
                "conditions": ["build_failure", "test_failure"]
            },
            "notifications": {
                "slack": True,
                "email": ["team@example.com"]
            }
        }
        
        # Execute deployment pipeline
        result = await super_agent.execute_deployment_pipeline(
            deploy_config,
            test_engineer.id
        )
        
        # Verify deployment steps
        assert result["status"] == "completed"
        assert len(result["steps"]) == len(deploy_config["steps"])
        for step in result["steps"]:
            assert step["status"] in ["success", "skipped"]
        
        # Verify environment state
        env_state = await agent_manager.get_environment_state(
            deploy_config["environment"]
        )
        assert env_state["status"] == "healthy"
        assert env_state["version"] == result["deployed_version"]
        
        # Verify notifications
        notifications = await agent_manager.get_deployment_notifications(
            result["deployment_id"]
        )
        assert len(notifications) > 0
        assert any(n["type"] == "slack" for n in notifications)
    
    @pytest.mark.asyncio
    async def test_deployment_rollback(self, agent_manager, test_db, mock_secrets):
        """
        Tests that a deployment pipeline triggers a rollback when a failure occurs during execution.
        
        This test initializes agents, configures a deployment pipeline with an intentional failure in the test step, and verifies that the rollback mechanism is activated. It checks that the deployment status is marked as rolled back, the rollback reason matches the failure, the environment is restored to its previous version, and rollback actions are logged.
        """
        # Initialize agents
        super_agent = agent_manager.initialize_agent("SuperAgent")
        test_engineer = agent_manager.initialize_agent("TestEngineer")
        
        # Create deployment with intentional failure
        deploy_config = {
            "repository": "test-repo",
            "environment": "staging",
            "steps": [
                {"name": "build", "command": "npm run build"},
                {"name": "test", "command": "exit 1"},  # Intentional failure
                {"name": "deploy", "command": "npm run deploy"}
            ],
            "rollback_strategy": {
                "enabled": True,
                "conditions": ["test_failure"]
            }
        }
        
        # Execute deployment pipeline
        result = await super_agent.execute_deployment_pipeline(
            deploy_config,
            test_engineer.id
        )
        
        # Verify rollback was triggered
        assert result["status"] == "rolled_back"
        assert result["rollback_reason"] == "test_failure"
        
        # Verify environment returned to previous state
        env_state = await agent_manager.get_environment_state(
            deploy_config["environment"]
        )
        assert env_state["version"] == result["previous_version"]
        
        # Verify rollback was logged
        deployment_logs = await agent_manager.get_deployment_logs(
            result["deployment_id"]
        )
        assert any("Initiating rollback" in log["message"] for log in deployment_logs) 