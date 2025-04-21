# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union, Callable, TypeVar, Generic
from pydantic import BaseModel, Field

# Try to import evaluation components
try:
    from pydantic_evals import Case, Dataset, BaseEvaluator
    EVALS_AVAILABLE = True
except ImportError:
    EVALS_AVAILABLE = False
    logging.warning("Evaluation framework not available. Install with 'pip install pydantic-evals'")
    
    # Create stub classes for type checking
    class Case: pass
    class Dataset: pass
    class BaseEvaluator: pass

class AgentPrompt(BaseModel):
    """Model for agent input prompts"""
    query: str
    context: Optional[Dict[str, Any]] = None

class AgentResponse(BaseModel):
    """Model for agent output responses"""
    content: str
    metadata: Optional[Dict[str, Any]] = None

class EvaluationResult(BaseModel):
    """Model for evaluation results"""
    score: float
    reasoning: str
    passed: bool
    metadata: Optional[Dict[str, Any]] = None

class AgentEvalCase(BaseModel):
    """Model for a single agent evaluation case"""
    name: str
    description: Optional[str] = None
    inputs: AgentPrompt
    expected_output: Optional[AgentResponse] = None
    tags: List[str] = Field(default_factory=list)

    def to_pydantic_case(self) -> Union[Case, Dict]:
        """Convert to a pydantic-evals Case if available"""
        if not EVALS_AVAILABLE:
            return {
                "name": self.name,
                "description": self.description,
                "inputs": self.inputs.model_dump(),
                "expected_output": self.expected_output.model_dump() if self.expected_output else None,
                "tags": self.tags
            }
        return Case(
            name=self.name,
            description=self.description,
            inputs=self.inputs,
            expected_output=self.expected_output,
            tags=self.tags
        )

class ResponseAccuracyEvaluator:
    """Evaluator for measuring accuracy of agent responses"""
    
    def __init__(self, model_name: str = "openai:gpt-4o-mini"):
        """Initialize the evaluator with a specified model"""
        self.model_name = model_name
        
    async def evaluate(self, response: AgentResponse, case: AgentEvalCase) -> EvaluationResult:
        """Evaluate agent response against expected output
        
        In a real implementation, this would use the specified model to evaluate
        the response. For now, we'll implement a simple comparison.
        """
        if not case.expected_output:
            raise ValueError("Cannot evaluate without expected output")
            
        # Simple content comparison (in real impl, would use semantic comparison)
        expected = case.expected_output.content.lower()
        actual = response.content.lower()
        
        # Check if key points from expected are in actual
        key_points = [p.strip() for p in expected.split('.') if p.strip()]
        points_found = sum(1 for p in key_points if p in actual)
        points_ratio = points_found / len(key_points) if key_points else 0
        
        # Calculate score (0-1)
        score = points_ratio
        passed = score >= 0.7  # 70% threshold for passing
        
        return EvaluationResult(
            score=score,
            reasoning=f"Found {points_found}/{len(key_points)} expected points in response.",
            passed=passed,
            metadata={
                "points_checked": len(key_points),
                "points_found": points_found,
                "raw_score": score
            }
        )

class AgentEvaluationManager:
    """Manager for agent evaluation datasets and runs"""
    
    def __init__(self, datasets_dir: str = "evaluation/datasets"):
        """Initialize the evaluation manager"""
        self.datasets_dir = datasets_dir
        self.evaluators = {}
        self.datasets = {}
        
        # Create datasets directory if it doesn't exist
        os.makedirs(datasets_dir, exist_ok=True)
        
        # Register default evaluators
        self.register_evaluator("accuracy", ResponseAccuracyEvaluator())
        
    def register_evaluator(self, name: str, evaluator: Any) -> None:
        """Register an evaluator for use in evaluations"""
        self.evaluators[name] = evaluator
        
    def create_dataset(self, name: str, description: str = "") -> Dict[str, Any]:
        """Create a new evaluation dataset"""
        dataset_info = {
            "name": name,
            "description": description,
            "cases": []
        }
        
        # Store in memory
        self.datasets[name] = dataset_info
        
        # Save to disk
        self._save_dataset(name, dataset_info)
        
        return dataset_info
    
    def add_case(self, dataset_name: str, case: AgentEvalCase) -> None:
        """Add a case to an existing dataset"""
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset '{dataset_name}' not found")
            
        # Add to in-memory dataset
        self.datasets[dataset_name]["cases"].append(case.model_dump())
        
        # Save to disk
        self._save_dataset(dataset_name, self.datasets[dataset_name])
        
    def load_dataset(self, dataset_name: str) -> Dict[str, Any]:
        """Load a dataset from disk"""
        dataset_path = os.path.join(self.datasets_dir, f"{dataset_name}.json")
        
        if not os.path.exists(dataset_path):
            raise ValueError(f"Dataset '{dataset_name}' not found")
            
        with open(dataset_path, 'r') as f:
            dataset = json.load(f)
            
        # Store in memory
        self.datasets[dataset_name] = dataset
        
        return dataset
    
    def _save_dataset(self, dataset_name: str, dataset: Dict[str, Any]) -> None:
        """Save a dataset to disk"""
        dataset_path = os.path.join(self.datasets_dir, f"{dataset_name}.json")
        
        with open(dataset_path, 'w') as f:
            json.dump(dataset, f, indent=2)
    
    async def evaluate_agent(self, agent_func: Callable, dataset_name: str, 
                         evaluator_name: str = "accuracy") -> Dict[str, Any]:
        """Evaluate an agent against a dataset
        
        Args:
            agent_func: Async function that takes AgentPrompt and returns AgentResponse
            dataset_name: Name of the dataset to use
            evaluator_name: Name of the evaluator to use
            
        Returns:
            Evaluation results with scores and statistics
        """
        if dataset_name not in self.datasets:
            self.load_dataset(dataset_name)
            
        if evaluator_name not in self.evaluators:
            raise ValueError(f"Evaluator '{evaluator_name}' not found")
            
        dataset = self.datasets[dataset_name]
        evaluator = self.evaluators[evaluator_name]
        
        results = []
        passed_count = 0
        total_score = 0.0
        
        # Process each case
        for case_data in dataset["cases"]:
            # Convert to AgentEvalCase
            case = AgentEvalCase(**case_data)
            
            # Call the agent function with the input prompt
            response = await agent_func(case.inputs)
            
            # Evaluate the response
            eval_result = await evaluator.evaluate(response, case)
            
            # Track results
            results.append({
                "case": case.name,
                "evaluation": eval_result.model_dump()
            })
            
            if eval_result.passed:
                passed_count += 1
                
            total_score += eval_result.score
        
        # Calculate statistics
        case_count = len(dataset["cases"])
        pass_rate = passed_count / case_count if case_count > 0 else 0
        avg_score = total_score / case_count if case_count > 0 else 0
        
        # Return evaluation summary
        return {
            "dataset": dataset_name,
            "evaluator": evaluator_name,
            "statistics": {
                "case_count": case_count,
                "passed_count": passed_count,
                "pass_rate": pass_rate,
                "average_score": avg_score
            },
            "results": results
        }
        
    def get_pydantic_dataset(self, dataset_name: str) -> Optional[Dataset]:
        """Get a dataset in pydantic-evals format if available"""
        if not EVALS_AVAILABLE:
            return None
            
        if dataset_name not in self.datasets:
            self.load_dataset(dataset_name)
            
        dataset = self.datasets[dataset_name]
        cases = []
        
        for case_data in dataset["cases"]:
            case = AgentEvalCase(**case_data)
            cases.append(case.to_pydantic_case())
            
        return Dataset(
            name=dataset["name"],
            description=dataset["description"],
            cases=cases
        )