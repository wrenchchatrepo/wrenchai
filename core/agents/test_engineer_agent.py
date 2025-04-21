# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Any, Optional, Union
import yaml
import logging
import asyncio
import json
from pathlib import Path

from .journey_agent import JourneyAgent

class TestEngineer(JourneyAgent):
    """
    Quality assurance specialist focused on testing.
    
    Core responsibilities:
    1. Develop test plans
    2. Write unit tests
    3. Implement integration tests
    4. Perform system testing
    5. Report test results
    """
    
    def __init__(self, 
                name: str, 
                llm: Any, 
                tools: List[str], 
                playbook_path: str,
                test_frameworks: Optional[Dict[str, str]] = None,
                coverage_targets: Optional[Dict[str, float]] = None):
        """Initialize the TestEngineer agent.
        
        Args:
            name: Agent name
            llm: Language model to use
            tools: List of tool names
            playbook_path: Path to the playbook file
            test_frameworks: Optional map of test frameworks for different languages
            coverage_targets: Optional test coverage targets by type
        """
        super().__init__(name, llm, tools, playbook_path)
        
        self.test_frameworks = test_frameworks or {
            "python": "pytest",
            "javascript": "jest",
            "java": "junit",
            "csharp": "nunit",
            "go": "testing"
        }
        
        self.coverage_targets = coverage_targets or {
            "unit": 85.0,
            "integration": 75.0,
            "system": 60.0,
            "e2e": 50.0
        }
        
        # Check tools availability
        required_tools = ["code_execution", "test_tool"]
        for tool in required_tools:
            if tool not in tools:
                logging.warning(f"TestEngineer agent should have '{tool}' tool")
                
    async def create_test_plan(self, 
                           project: Dict[str, Any], 
                           test_level: str = "all") -> Dict[str, Any]:
        """Create a test plan for a project.
        
        Args:
            project: Project information
            test_level: Test level (unit, integration, system, e2e, all)
            
        Returns:
            Test plan
        """
        test_plan = {
            "project_name": project.get("name", "Unknown Project"),
            "test_types": [],
            "test_scenarios": [],
            "coverage_targets": {},
            "testing_schedule": {}
        }
        
        # Create test plan prompt
        project_text = json.dumps(project, indent=2)
        frameworks_text = json.dumps(self.test_frameworks, indent=2)
        
        plan_prompt = f"""
        Create a comprehensive test plan for {test_level} testing for the following project:
        {project_text}
        
        Test frameworks available:
        {frameworks_text}
        
        Please provide:
        1. Test types and approaches
        2. Detailed test scenarios
        3. Test coverage targets (aim for these or higher: {json.dumps(self.coverage_targets)})
        4. Testing schedule and milestones
        5. Test environment requirements
        
        Format your response as JSON with the following structure:
        {{
            "test_types": [
                {{
                    "type": "unit",
                    "framework": "pytest",
                    "focus_areas": ["data processing", "authentication", "validation"]
                }}
            ],
            "test_scenarios": [
                {{
                    "id": "TS-001",
                    "name": "User Authentication",
                    "type": "integration",
                    "description": "Test complete authentication flow",
                    "test_cases": [
                        {{
                            "id": "TC-001",
                            "name": "Valid Login",
                            "steps": ["Enter valid credentials", "Submit login form"],
                            "expected_result": "User successfully authenticated",
                            "priority": "high"
                        }}
                    ]
                }}
            ],
            "coverage_targets": {{
                "unit": 90,
                "integration": 80,
                "system": 70,
                "overall": 85
            }},
            "testing_schedule": {{
                "unit_testing": {{
                    "start": "Week 1",
                    "duration": "2 weeks",
                    "resources": ["Developer 1", "Developer 2"]
                }}
            }},
            "test_environment": {{
                "requirements": ["Test database", "Mock services", "CI/CD pipeline"],
                "setup_instructions": "Setup instructions..."
            }}
        }}
        """
        
        # Generate test plan using LLM
        plan_result = await self.llm.process({"prompt": plan_prompt})
        
        # Parse response
        if isinstance(plan_result, dict) and "output" in plan_result:
            try:
                parsed_result = json.loads(plan_result["output"])
                test_plan["test_types"] = parsed_result.get("test_types", [])
                test_plan["test_scenarios"] = parsed_result.get("test_scenarios", [])
                test_plan["coverage_targets"] = parsed_result.get("coverage_targets", {})
                test_plan["testing_schedule"] = parsed_result.get("testing_schedule", {})
                test_plan["test_environment"] = parsed_result.get("test_environment", {})
            except json.JSONDecodeError:
                logging.error("Failed to parse test plan result")
                test_plan["error"] = "Failed to parse result"
        
        return test_plan
    
    async def generate_unit_tests(self, 
                             code: Dict[str, Any], 
                             language: str = "python") -> Dict[str, Any]:
        """Generate unit tests for code.
        
        Args:
            code: Code to test
            language: Programming language
            
        Returns:
            Unit tests
        """
        code_text = json.dumps(code, indent=2)
        framework = self.test_frameworks.get(language, "")
        
        unit_test_prompt = f"""
        Generate comprehensive unit tests in {language} using {framework} for the following code:
        {code_text}
        
        Target test coverage: {self.coverage_targets.get("unit", 85)}%
        
        Please include:
        1. Test cases for normal operation
        2. Tests for edge cases
        3. Tests for error conditions
        4. Mock implementations if needed
        5. Parameterized tests for multiple scenarios
        
        Format your response as JSON with test files and descriptions.
        """
        
        # Generate unit tests using LLM
        unit_test_result = await self.llm.process({"prompt": unit_test_prompt})
        
        if isinstance(unit_test_result, dict) and "output" in unit_test_result:
            try:
                return json.loads(unit_test_result["output"])
            except json.JSONDecodeError:
                return {"raw_tests": unit_test_result["output"]}
        
        return {"error": "Failed to generate unit tests"}
    
    async def generate_integration_tests(self, 
                                    components: List[Dict[str, Any]], 
                                    language: str = "python") -> Dict[str, Any]:
        """Generate integration tests for components.
        
        Args:
            components: Components to test
            language: Programming language
            
        Returns:
            Integration tests
        """
        components_text = json.dumps(components, indent=2)
        framework = self.test_frameworks.get(language, "")
        
        integration_test_prompt = f"""
        Generate integration tests in {language} using {framework} for these interacting components:
        {components_text}
        
        Target test coverage: {self.coverage_targets.get("integration", 75)}%
        
        Please include:
        1. Tests for component interactions
        2. Tests for API contracts
        3. Tests for data flows
        4. Tests for state transitions
        5. Tests for error propagation
        
        Format your response as JSON with test files and descriptions.
        """
        
        # Generate integration tests using LLM
        integration_test_result = await self.llm.process({"prompt": integration_test_prompt})
        
        if isinstance(integration_test_result, dict) and "output" in integration_test_result:
            try:
                return json.loads(integration_test_result["output"])
            except json.JSONDecodeError:
                return {"raw_tests": integration_test_result["output"]}
        
        return {"error": "Failed to generate integration tests"}
    
    async def analyze_test_results(self, 
                               test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test results.
        
        Args:
            test_results: Test execution results
            
        Returns:
            Test analysis
        """
        results_text = json.dumps(test_results, indent=2)
        
        analysis_prompt = f"""
        Analyze the following test results:
        {results_text}
        
        Please provide:
        1. Overall test summary
        2. Pass/fail statistics
        3. Coverage analysis
        4. Failed test analysis with root causes
        5. Recommendations for improvements
        
        Format your response as JSON with comprehensive test analysis.
        """
        
        # Generate test analysis using LLM
        analysis_result = await self.llm.process({"prompt": analysis_prompt})
        
        if isinstance(analysis_result, dict) and "output" in analysis_result:
            try:
                return json.loads(analysis_result["output"])
            except json.JSONDecodeError:
                return {"raw_analysis": analysis_result["output"]}
        
        return {"error": "Failed to generate test analysis"}
    
    async def generate_test_report(self, 
                               analysis: Dict[str, Any], 
                               report_type: str = "executive") -> Dict[str, Any]:
        """Generate test report.
        
        Args:
            analysis: Test analysis
            report_type: Report type (executive, technical, detailed)
            
        Returns:
            Test report
        """
        analysis_text = json.dumps(analysis, indent=2)
        
        report_prompt = f"""
        Generate a {report_type} test report based on the following analysis:
        {analysis_text}
        
        Please include:
        1. Executive summary
        2. Test coverage
        3. Quality metrics
        4. Issues and risks
        5. Recommendations
        
        Format your response as JSON with a complete {report_type} test report.
        """
        
        # Generate test report using LLM
        report_result = await self.llm.process({"prompt": report_prompt})
        
        if isinstance(report_result, dict) and "output" in report_result:
            try:
                return json.loads(report_result["output"])
            except json.JSONDecodeError:
                return {
                    "content": report_result["output"],
                    "report_type": report_type
                }
        
        return {"error": "Failed to generate test report"}
    
    async def run_playbook_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific playbook step.
        
        Args:
            step: Playbook step definition
            context: Execution context
            
        Returns:
            Step execution results
        """
        action = step.get("action", "")
        
        if action == "create_test_plan":
            project = step.get("project", context.get("project", {}))
            test_level = step.get("test_level", "all")
            
            test_plan = await self.create_test_plan(project, test_level)
            return {"test_plan": test_plan}
            
        elif action == "generate_unit_tests":
            code = step.get("code", context.get("code", {}))
            language = step.get("language", "python")
            
            unit_tests = await self.generate_unit_tests(code, language)
            return {"unit_tests": unit_tests}
            
        elif action == "generate_integration_tests":
            components = step.get("components", context.get("components", []))
            language = step.get("language", "python")
            
            integration_tests = await self.generate_integration_tests(components, language)
            return {"integration_tests": integration_tests}
            
        elif action == "analyze_test_results":
            test_results = step.get("test_results", context.get("test_results", {}))
            
            analysis = await self.analyze_test_results(test_results)
            return {"test_analysis": analysis}
            
        elif action == "generate_test_report":
            analysis = step.get("analysis", context.get("test_analysis", {}))
            report_type = step.get("report_type", "executive")
            
            report = await self.generate_test_report(analysis, report_type)
            return {"test_report": report}
            
        else:
            return await super().run_playbook_step(step, context)
    
    async def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the TestEngineer agent with the specified playbook.
        
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
        
        # Add final test artifacts
        if "test_plan" in context:
            results["test_plan"] = context["test_plan"]
            
        if "unit_tests" in context:
            results["unit_tests"] = context["unit_tests"]
            
        if "integration_tests" in context:
            results["integration_tests"] = context["integration_tests"]
            
        if "test_analysis" in context:
            results["test_analysis"] = context["test_analysis"]
            
        if "test_report" in context:
            results["test_report"] = context["test_report"]
            
        return results