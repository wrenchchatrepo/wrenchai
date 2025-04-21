# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Any, Optional, Union
import yaml
import logging
import asyncio
import json
from pathlib import Path

from .journey_agent import JourneyAgent

class DataScientist(JourneyAgent):
    """
    AI/ML specialist focused on data analysis and model development.
    
    Core responsibilities:
    1. Develop ML models
    2. Analyze data patterns
    3. Optimize model performance
    4. Implement AI solutions
    5. Evaluate model metrics
    """
    
    def __init__(self, 
                name: str, 
                llm: Any, 
                tools: List[str], 
                playbook_path: str,
                experiment_tracking: Optional[Dict[str, Any]] = None,
                model_registry: Optional[str] = None):
        """Initialize the DataScientist agent.
        
        Args:
            name: Agent name
            llm: Language model to use
            tools: List of tool names
            playbook_path: Path to the playbook file
            experiment_tracking: Optional experiment tracking configuration
            model_registry: Optional model registry location
        """
        super().__init__(name, llm, tools, playbook_path)
        
        self.experiment_tracking = experiment_tracking or {
            "platform": "mlflow",
            "tracking_uri": "http://localhost:5000",
            "artifacts_location": "gs://mlflow-artifacts"
        }
        
        self.model_registry = model_registry or "models"
        
        # Check tools availability
        required_tools = ["data_analysis", "ml_tool"]
        for tool in required_tools:
            if tool not in tools:
                logging.warning(f"DataScientist agent should have '{tool}' tool")
                
    async def analyze_data(self, 
                        dataset: Dict[str, Any], 
                        analysis_type: str = "exploratory") -> Dict[str, Any]:
        """Analyze dataset.
        
        Args:
            dataset: Dataset information
            analysis_type: Type of analysis (exploratory, statistical, etc.)
            
        Returns:
            Data analysis results
        """
        analysis = {
            "summary_statistics": {},
            "data_quality": {},
            "feature_importance": [],
            "visualizations": [],
            "insights": []
        }
        
        # Create analysis prompt
        analysis_prompt = f"""
        Perform {analysis_type} data analysis on the following dataset:
        {json.dumps(dataset, indent=2)}
        
        Please provide:
        1. Summary statistics
        2. Data quality assessment
        3. Feature importance
        4. Recommended visualizations
        5. Key insights
        
        Format your response as JSON with the following structure:
        {{
            "summary_statistics": {{
                "num_samples": 10000,
                "features": [
                    {{
                        "name": "age",
                        "mean": 34.5,
                        "median": 32,
                        "std": 12.3,
                        "min": 18,
                        "max": 80
                    }}
                ]
            }},
            "data_quality": {{
                "missing_values": [
                    {{
                        "feature": "income",
                        "percent_missing": 2.5
                    }}
                ],
                "outliers": [
                    {{
                        "feature": "age",
                        "outlier_count": 15,
                        "percent_outliers": 0.15
                    }}
                ]
            }},
            "feature_importance": [
                {{
                    "feature": "income",
                    "importance": 0.7
                }}
            ],
            "visualizations": [
                {{
                    "type": "histogram",
                    "feature": "age",
                    "description": "Age distribution shows most customers between 25-40"
                }}
            ],
            "insights": [
                "Customers with higher income are more likely to convert",
                "Age and location are strong predictors of customer behavior"
            ]
        }}
        """
        
        # Generate analysis using LLM
        analysis_result = await self.llm.process({"prompt": analysis_prompt})
        
        # Parse response
        if isinstance(analysis_result, dict) and "output" in analysis_result:
            try:
                parsed_result = json.loads(analysis_result["output"])
                analysis["summary_statistics"] = parsed_result.get("summary_statistics", {})
                analysis["data_quality"] = parsed_result.get("data_quality", {})
                analysis["feature_importance"] = parsed_result.get("feature_importance", [])
                analysis["visualizations"] = parsed_result.get("visualizations", [])
                analysis["insights"] = parsed_result.get("insights", [])
            except json.JSONDecodeError:
                logging.error("Failed to parse analysis result")
                analysis["error"] = "Failed to parse result"
        
        return analysis
    
    async def design_ml_solution(self, 
                              problem_description: Dict[str, Any], 
                              data_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Design machine learning solution.
        
        Args:
            problem_description: Problem description
            data_analysis: Data analysis results
            
        Returns:
            ML solution design
        """
        problem_text = json.dumps(problem_description, indent=2)
        analysis_text = json.dumps(data_analysis, indent=2)
        
        design_prompt = f"""
        Design a machine learning solution for the following problem:
        {problem_text}
        
        Based on this data analysis:
        {analysis_text}
        
        Please provide:
        1. Problem formulation (classification, regression, etc.)
        2. Feature engineering approach
        3. Model selection with justification
        4. Evaluation strategy
        5. Implementation plan
        
        Format your response as JSON with a comprehensive ML solution design.
        """
        
        # Generate ML design using LLM
        design_result = await self.llm.process({"prompt": design_prompt})
        
        if isinstance(design_result, dict) and "output" in design_result:
            try:
                return json.loads(design_result["output"])
            except json.JSONDecodeError:
                return {"raw_design": design_result["output"]}
        
        return {"error": "Failed to generate ML solution design"}
    
    async def create_model_code(self, 
                           solution_design: Dict[str, Any], 
                           framework: str = "tensorflow") -> Dict[str, Any]:
        """Create model implementation code.
        
        Args:
            solution_design: ML solution design
            framework: ML framework to use
            
        Returns:
            Model implementation code
        """
        design_text = json.dumps(solution_design, indent=2)
        
        code_prompt = f"""
        Create {framework} model implementation code for the following ML solution design:
        {design_text}
        
        Experiment tracking configuration:
        {json.dumps(self.experiment_tracking, indent=2)}
        
        Please provide:
        1. Data preprocessing code
        2. Feature engineering code
        3. Model architecture code
        4. Training code with experiment tracking
        5. Evaluation code
        
        Format your response as JSON with Python code files.
        """
        
        # Generate model code using LLM
        code_result = await self.llm.process({"prompt": code_prompt})
        
        if isinstance(code_result, dict) and "output" in code_result:
            try:
                return json.loads(code_result["output"])
            except json.JSONDecodeError:
                return {"raw_code": code_result["output"]}
        
        return {"error": "Failed to generate model code"}
    
    async def create_evaluation_plan(self, 
                                  solution_design: Dict[str, Any], 
                                  metrics: List[str] = None) -> Dict[str, Any]:
        """Create model evaluation plan.
        
        Args:
            solution_design: ML solution design
            metrics: List of evaluation metrics
            
        Returns:
            Evaluation plan
        """
        metrics = metrics or ["accuracy", "precision", "recall", "f1"]
        design_text = json.dumps(solution_design, indent=2)
        
        eval_prompt = f"""
        Create a comprehensive evaluation plan for the following ML solution:
        {design_text}
        
        Evaluation metrics: {', '.join(metrics)}
        
        Please include:
        1. Evaluation methodology
        2. Data splitting strategy
        3. Baseline models
        4. Statistical tests
        5. Visualization of results
        
        Format your response as JSON with a detailed evaluation plan.
        """
        
        # Generate evaluation plan using LLM
        eval_result = await self.llm.process({"prompt": eval_prompt})
        
        if isinstance(eval_result, dict) and "output" in eval_result:
            try:
                return json.loads(eval_result["output"])
            except json.JSONDecodeError:
                return {"raw_plan": eval_result["output"]}
        
        return {"error": "Failed to generate evaluation plan"}
    
    async def run_playbook_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific playbook step.
        
        Args:
            step: Playbook step definition
            context: Execution context
            
        Returns:
            Step execution results
        """
        action = step.get("action", "")
        
        if action == "analyze_data":
            dataset = step.get("dataset", context.get("dataset", {}))
            analysis_type = step.get("analysis_type", "exploratory")
            
            analysis = await self.analyze_data(dataset, analysis_type)
            return {"data_analysis": analysis}
            
        elif action == "design_ml_solution":
            problem = step.get("problem", context.get("problem", {}))
            analysis = step.get("analysis", context.get("data_analysis", {}))
            
            solution = await self.design_ml_solution(problem, analysis)
            return {"solution_design": solution}
            
        elif action == "create_model_code":
            design = step.get("design", context.get("solution_design", {}))
            framework = step.get("framework", "tensorflow")
            
            code = await self.create_model_code(design, framework)
            return {"model_code": code}
            
        elif action == "create_evaluation_plan":
            design = step.get("design", context.get("solution_design", {}))
            metrics = step.get("metrics", ["accuracy", "precision", "recall", "f1"])
            
            plan = await self.create_evaluation_plan(design, metrics)
            return {"evaluation_plan": plan}
            
        else:
            return await super().run_playbook_step(step, context)
    
    async def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the DataScientist agent with the specified playbook.
        
        Args:
            context: Optional execution context
            
        Returns:
            Execution results
        """
        context = context or {}
        
        # Initialize results
        results = {
            "agent": self.name,
            "playbook": self.playbook.get("name", "Unknown"),
            "steps_results": []
        }
        
        # Execute each step in the playbook
        for step in self.playbook.get("steps", []):
            step_result = await self.run_playbook_step(step, context)
            results["steps_results"].append({
                "step_id": step.get("step_id", "unknown"),
                "description": step.get("description", ""),
                "result": step_result
            })
            
            # Update context with step results
            context.update(step_result)
        
        # Add final analysis, design, and code if available
        if "data_analysis" in context:
            results["data_analysis"] = context["data_analysis"]
            
        if "solution_design" in context:
            results["solution_design"] = context["solution_design"]
            
        if "model_code" in context:
            results["model_code"] = context["model_code"]
            
        if "evaluation_plan" in context:
            results["evaluation_plan"] = context["evaluation_plan"]
            
        return results