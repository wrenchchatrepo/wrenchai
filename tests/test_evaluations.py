"""
Tests for the evaluation framework.
"""
import pytest
import asyncio
import os
import json
from unittest.mock import patch, MagicMock

from wrenchai.core.evaluation import (
    AgentEvalCase, AgentPrompt, AgentResponse,
    ResponseAccuracyEvaluator, AgentEvaluationManager,
    EVALS_AVAILABLE
)

class TestEvaluation:
    """Tests for the evaluation framework"""
    
    def setup_method(self):
        """Set up for the tests"""
        # Create a temporary test dir
        self.temp_dir = "test_eval_temp"
        os.makedirs(self.temp_dir, exist_ok=True)
        
    def teardown_method(self):
        """Clean up after tests"""
        # Remove test files if they exist
        if os.path.exists(f"{self.temp_dir}/test_dataset.json"):
            os.remove(f"{self.temp_dir}/test_dataset.json")
            
        # Remove test directory
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_agent_eval_case(self):
        """Test creation and conversion of evaluation cases"""
        # Create a test case
        case = AgentEvalCase(
            name="test_case",
            description="A test case",
            inputs=AgentPrompt(query="What is the capital of France?"),
            expected_output=AgentResponse(content="The capital of France is Paris."),
            tags=["geography", "test"]
        )
        
        # Convert to pydantic case format
        pydantic_case = case.to_pydantic_case()
        
        # Check that conversion worked
        if EVALS_AVAILABLE:
            from pydantic_evals import Case
            assert isinstance(pydantic_case, Case)
        else:
            assert isinstance(pydantic_case, dict)
            assert pydantic_case["name"] == "test_case"
    
    @pytest.mark.asyncio
    async def test_response_evaluator(self):
        """Test the response accuracy evaluator"""
        # Create evaluator
        evaluator = ResponseAccuracyEvaluator()
        
        # Create test case and response
        case = AgentEvalCase(
            name="test_case",
            inputs=AgentPrompt(query="What is the capital of France?"),
            expected_output=AgentResponse(content="The capital of France is Paris. It's known for the Eiffel Tower.")
        )
        
        # Test exact match
        response = AgentResponse(content="The capital of France is Paris. It's known for the Eiffel Tower.")
        result = await evaluator.evaluate(response, case)
        assert result.score > 0.9
        assert result.passed is True
        
        # Test partial match
        response = AgentResponse(content="Paris is the capital of France.")
        result = await evaluator.evaluate(response, case)
        assert 0 < result.score < 1
        
        # Test mismatch
        response = AgentResponse(content="The capital of Italy is Rome.")
        result = await evaluator.evaluate(response, case)
        assert result.score < 0.5
        assert result.passed is False
    
    def test_evaluation_manager_create_dataset(self):
        """Test dataset creation in evaluation manager"""
        # Create manager with custom directory
        manager = AgentEvaluationManager(datasets_dir=self.temp_dir)
        
        # Create a dataset
        dataset = manager.create_dataset("test_dataset", "A test dataset")
        
        # Check in-memory dataset
        assert "test_dataset" in manager.datasets
        assert manager.datasets["test_dataset"]["name"] == "test_dataset"
        
        # Check that file was created
        assert os.path.exists(f"{self.temp_dir}/test_dataset.json")
        
    def test_evaluation_manager_add_case(self):
        """Test adding cases to datasets"""
        # Create manager with custom directory
        manager = AgentEvaluationManager(datasets_dir=self.temp_dir)
        
        # Create a dataset
        manager.create_dataset("test_dataset", "A test dataset")
        
        # Create a test case
        case = AgentEvalCase(
            name="test_case",
            description="A test case",
            inputs=AgentPrompt(query="What is the capital of France?"),
            expected_output=AgentResponse(content="The capital of France is Paris."),
            tags=["geography", "test"]
        )
        
        # Add case to dataset
        manager.add_case("test_dataset", case)
        
        # Check in-memory dataset
        assert len(manager.datasets["test_dataset"]["cases"]) == 1
        assert manager.datasets["test_dataset"]["cases"][0]["name"] == "test_case"
        
        # Load from disk and verify
        manager2 = AgentEvaluationManager(datasets_dir=self.temp_dir)
        dataset = manager2.load_dataset("test_dataset")
        assert len(dataset["cases"]) == 1
        assert dataset["cases"][0]["name"] == "test_case"
    
    @pytest.mark.asyncio
    async def test_agent_evaluation(self):
        """Test full agent evaluation workflow"""
        # Create manager with custom directory
        manager = AgentEvaluationManager(datasets_dir=self.temp_dir)
        
        # Create a dataset
        manager.create_dataset("test_dataset", "A test dataset")
        
        # Add test cases
        cases = [
            AgentEvalCase(
                name="france_capital",
                inputs=AgentPrompt(query="What is the capital of France?"),
                expected_output=AgentResponse(content="The capital of France is Paris.")
            ),
            AgentEvalCase(
                name="italy_capital",
                inputs=AgentPrompt(query="What is the capital of Italy?"),
                expected_output=AgentResponse(content="The capital of Italy is Rome.")
            )
        ]
        
        for case in cases:
            manager.add_case("test_dataset", case)
        
        # Create mock agent function
        async def mock_agent_func(prompt: AgentPrompt) -> AgentResponse:
            """Mock agent function that responds based on the prompt"""
            if "france" in prompt.query.lower():
                return AgentResponse(content="The capital of France is Paris.")
            elif "italy" in prompt.query.lower():
                return AgentResponse(content="The capital of Italy is Rome.")
            else:
                return AgentResponse(content="I don't know.")
        
        # Run evaluation
        results = await manager.evaluate_agent(mock_agent_func, "test_dataset")
        
        # Check results
        assert results["dataset"] == "test_dataset"
        assert results["statistics"]["case_count"] == 2
        assert results["statistics"]["pass_rate"] == 1.0  # All should pass
        assert results["statistics"]["average_score"] > 0.9  # High scores