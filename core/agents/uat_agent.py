# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Any, Optional, Union
import yaml
import logging
import asyncio
import json
from pathlib import Path
from pydantic import BaseModel, Field
from fastapi import HTTPException, status
from datetime import datetime
from core.tools.browser_tools import BrowserTools
from core.tools.memory_manager import MemoryManager

from .journey_agent import JourneyAgent

logger = logging.getLogger(__name__)

class TestCase(BaseModel):
    """Test case specification"""
    id: str
    title: str
    description: str
    steps: List[Dict[str, str]]
    expected_result: str
    priority: str = "medium"
    category: str
    prerequisites: Optional[List[str]] = None

class TestResult(BaseModel):
    """Test execution result"""
    test_case_id: str
    status: str
    actual_result: str
    screenshots: Optional[List[str]] = None
    logs: Optional[List[str]] = None
    execution_time: float
    executed_at: datetime

class UAT(JourneyAgent):
    """
    User acceptance testing specialist.
    
    Core responsibilities:
    1. Plan UAT sessions
    2. Coordinate with stakeholders
    3. Document test scenarios
    4. Track user feedback
    5. Report UAT results
    """
    
    def __init__(self, 
                name: str, 
                llm: Any, 
                tools: List[str], 
                playbook_path: str,
                acceptance_criteria_template: Optional[Dict[str, Any]] = None,
                stakeholders: Optional[List[Dict[str, Any]]] = None):
        """
                Initializes the UAT agent with configuration, acceptance criteria, stakeholders, and required tools.
                
                Args:
                    name: The name of the agent.
                    llm: The language model used for generating plans, scenarios, and reports.
                    tools: List of tool names available to the agent.
                    playbook_path: Path to the playbook file for orchestrating UAT steps.
                    acceptance_criteria_template: Optional custom template for acceptance criteria; defaults to a standard set if not provided.
                    stakeholders: Optional list of stakeholder information relevant to the UAT process.
                """
        super().__init__(name, llm, tools, playbook_path)
        
        self.acceptance_criteria_template = acceptance_criteria_template or {
            "functional": [
                "Feature completes its intended task",
                "Feature handles expected edge cases",
                "Feature integrates with other systems as expected"
            ],
            "usability": [
                "Feature is intuitive and easy to use",
                "Feature follows established design patterns",
                "Feature provides helpful feedback to users"
            ],
            "performance": [
                "Feature responds within acceptable time limits",
                "Feature handles expected load without degradation",
                "Feature efficiently uses system resources"
            ],
            "security": [
                "Feature properly authenticates users",
                "Feature properly authorizes actions",
                "Feature protects sensitive data"
            ]
        }
        
        self.stakeholders = stakeholders or []
        
        # Check tools availability
        required_tools = ["uat_tool", "reporting_tool"]
        for tool in required_tools:
            if tool not in tools:
                logging.warning(f"UAT agent should have '{tool}' tool")
                
        self.browser_tools = BrowserTools()
        self.memory_manager = MemoryManager()
        self.test_results: Dict[str, TestResult] = {}
        
    async def create_uat_plan(self, 
                          project: Dict[str, Any], 
                          features: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
                          Generates a comprehensive User Acceptance Testing (UAT) plan for a project and its features.
                          
                          The plan includes an overview, objectives, stakeholders, test scenarios, schedule, and acceptance criteria. Prompts a language model to produce the plan and parses the structured JSON response. If parsing fails, returns an error message in the result.
                          
                          Args:
                              project: Dictionary containing project information.
                              features: List of dictionaries describing features to be tested.
                          
                          Returns:
                              A dictionary representing the UAT plan, including overview, objectives, stakeholders, test scenarios, schedule, and acceptance criteria. If parsing fails, includes an "error" key with details.
                          """
        uat_plan = {
            "project_name": project.get("name", "Unknown Project"),
            "overview": "",
            "objectives": [],
            "stakeholders": [],
            "test_scenarios": [],
            "schedule": {},
            "acceptance_criteria": {}
        }
        
        # Create UAT plan prompt
        project_text = json.dumps(project, indent=2)
        features_text = json.dumps(features, indent=2)
        stakeholders_text = json.dumps(self.stakeholders, indent=2)
        
        plan_prompt = f"""
        Create a comprehensive User Acceptance Testing (UAT) plan for the following project and features:
        
        Project:
        {project_text}
        
        Features to test:
        {features_text}
        
        Stakeholders:
        {stakeholders_text}
        
        Acceptance criteria template:
        {json.dumps(self.acceptance_criteria_template, indent=2)}
        
        Please provide:
        1. UAT overview and objectives
        2. Stakeholders and their roles
        3. Test scenarios mapped to features
        4. UAT schedule and logistics
        5. Specific acceptance criteria for each feature
        
        Format your response as JSON with the following structure:
        {{
            "overview": "This UAT plan outlines the approach for validating...",
            "objectives": [
                "Verify that features meet business requirements",
                "Ensure the system is ready for production"
            ],
            "stakeholders": [
                {{
                    "name": "John Smith",
                    "role": "Product Owner",
                    "responsibilities": ["Define acceptance criteria", "Approve test results"]
                }}
            ],
            "test_scenarios": [
                {{
                    "id": "UAT-001",
                    "name": "User Registration",
                    "feature_id": "F-123",
                    "description": "Verify user registration flow",
                    "test_cases": [
                        {{
                            "id": "TC-001",
                            "name": "Valid Registration",
                            "steps": ["Enter valid data", "Submit registration form"],
                            "expected_result": "User account created and confirmation email sent",
                            "acceptance_criteria": ["Feature completes its intended task", "Feature is intuitive and easy to use"]
                        }}
                    ]
                }}
            ],
            "schedule": {{
                "start_date": "2023-01-15",
                "end_date": "2023-01-30",
                "sessions": [
                    {{
                        "date": "2023-01-15",
                        "duration": "2 hours",
                        "focus": "User Management Features",
                        "participants": ["Product Owner", "Business Analyst", "End Users"]
                    }}
                ]
            }},
            "acceptance_criteria": {{
                "F-123": [
                    "User can successfully register with valid information",
                    "System validates email format",
                    "System prevents duplicate registrations"
                ]
            }}
        }}
        """
        
        # Generate UAT plan using LLM
        plan_result = await self.llm.process({"prompt": plan_prompt})
        
        # Parse response
        if isinstance(plan_result, dict) and "output" in plan_result:
            try:
                parsed_result = json.loads(plan_result["output"])
                uat_plan["overview"] = parsed_result.get("overview", "")
                uat_plan["objectives"] = parsed_result.get("objectives", [])
                uat_plan["stakeholders"] = parsed_result.get("stakeholders", [])
                uat_plan["test_scenarios"] = parsed_result.get("test_scenarios", [])
                uat_plan["schedule"] = parsed_result.get("schedule", {})
                uat_plan["acceptance_criteria"] = parsed_result.get("acceptance_criteria", {})
            except json.JSONDecodeError:
                logging.error("Failed to parse UAT plan result")
                uat_plan["error"] = "Failed to parse result"
        
        return uat_plan
    
    async def create_test_scenarios(self, 
                               features: List[Dict[str, Any]], 
                               user_personas: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Create detailed test scenarios for UAT.
        
        Args:
            features: List of features to test
            user_personas: Optional list of user personas
            
        Returns:
            Test scenarios
        """
        features_text = json.dumps(features, indent=2)
        personas_text = json.dumps(user_personas or [], indent=2)
        
        scenarios_prompt = f"""
        Create detailed UAT test scenarios for the following features and user personas:
        
        Features:
        {features_text}
        
        User Personas:
        {personas_text}
        
        Please include:
        1. Test scenario name and description
        2. User persona for each scenario
        3. Detailed test steps
        4. Expected results
        5. Acceptance criteria
        
        Format your response as JSON with comprehensive test scenarios.
        """
        
        # Generate test scenarios using LLM
        scenarios_result = await self.llm.process({"prompt": scenarios_prompt})
        
        if isinstance(scenarios_result, dict) and "output" in scenarios_result:
            try:
                return json.loads(scenarios_result["output"])
            except json.JSONDecodeError:
                return {"raw_scenarios": scenarios_result["output"]}
        
        return {"error": "Failed to generate test scenarios"}
    
    async def create_feedback_form(self, 
                              features: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create UAT feedback form.
        
        Args:
            features: List of features to test
            
        Returns:
            UAT feedback form
        """
        features_text = json.dumps(features, indent=2)
        
        form_prompt = f"""
        Create a UAT feedback form for collecting structured feedback on the following features:
        {features_text}
        
        Please include:
        1. Introduction and instructions
        2. Feature-specific questions
        3. Usability rating scales
        4. Open-ended feedback sections
        5. Issues reporting format
        
        Format your response as JSON with a comprehensive feedback form.
        """
        
        # Generate feedback form using LLM
        form_result = await self.llm.process({"prompt": form_prompt})
        
        if isinstance(form_result, dict) and "output" in form_result:
            try:
                return json.loads(form_result["output"])
            except json.JSONDecodeError:
                return {"raw_form": form_result["output"]}
        
        return {"error": "Failed to generate feedback form"}
    
    async def analyze_feedback(self, 
                          feedback: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze UAT feedback.
        
        Args:
            feedback: List of feedback entries
            
        Returns:
            Feedback analysis
        """
        feedback_text = json.dumps(feedback, indent=2)
        
        analysis_prompt = f"""
        Analyze the following UAT feedback:
        {feedback_text}
        
        Please provide:
        1. Key findings summary
        2. Issue categorization
        3. Priority recommendations
        4. Sentiment analysis
        5. Acceptance status by feature
        
        Format your response as JSON with comprehensive feedback analysis.
        """
        
        # Generate feedback analysis using LLM
        analysis_result = await self.llm.process({"prompt": analysis_prompt})
        
        if isinstance(analysis_result, dict) and "output" in analysis_result:
            try:
                return json.loads(analysis_result["output"])
            except json.JSONDecodeError:
                return {"raw_analysis": analysis_result["output"]}
        
        return {"error": "Failed to generate feedback analysis"}
    
    async def generate_uat_report(self, 
                             uat_plan: Dict[str, Any], 
                             feedback_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate UAT report.
        
        Args:
            uat_plan: UAT plan
            feedback_analysis: Feedback analysis
            
        Returns:
            UAT report
        """
        plan_text = json.dumps(uat_plan, indent=2)
        analysis_text = json.dumps(feedback_analysis, indent=2)
        
        report_prompt = f"""
        Generate a comprehensive UAT report based on the following UAT plan and feedback analysis:
        
        UAT Plan:
        {plan_text}
        
        Feedback Analysis:
        {analysis_text}
        
        Please include:
        1. Executive summary
        2. Test coverage and participation
        3. Acceptance status by feature
        4. Key issues and recommendations
        5. Next steps
        
        Format your response as JSON with a complete UAT report.
        """
        
        # Generate UAT report using LLM
        report_result = await self.llm.process({"prompt": report_prompt})
        
        if isinstance(report_result, dict) and "output" in report_result:
            try:
                return json.loads(report_result["output"])
            except json.JSONDecodeError:
                return {"raw_report": report_result["output"]}
        
        return {"error": "Failed to generate UAT report"}
    
    async def run_playbook_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a single playbook step based on its action and updates the execution context.
        
        Depending on the action specified in the step, this method delegates to the appropriate UAT agent method to generate plans, scenarios, feedback forms, analyses, reports, or test suites. For unrecognized actions, it defers execution to the superclass implementation.
        
        Args:
            step: The playbook step definition containing the action and relevant parameters.
            context: The current execution context with accumulated data.
        
        Returns:
            A dictionary containing the result of the executed step, keyed by the artifact type (e.g., "uat_plan", "test_scenarios", "feedback_form", "feedback_analysis", "uat_report", or "test_suite").
        """
        action = step.get("action", "")
        
        if action == "create_uat_plan":
            project = step.get("project", context.get("project", {}))
            features = step.get("features", context.get("features", []))
            
            uat_plan = await self.create_uat_plan(project, features)
            return {"uat_plan": uat_plan}
            
        elif action == "create_test_scenarios":
            features = step.get("features", context.get("features", []))
            user_personas = step.get("user_personas", context.get("user_personas", []))
            
            scenarios = await self.create_test_scenarios(features, user_personas)
            return {"test_scenarios": scenarios}
            
        elif action == "create_feedback_form":
            features = step.get("features", context.get("features", []))
            
            form = await self.create_feedback_form(features)
            return {"feedback_form": form}
            
        elif action == "analyze_feedback":
            feedback = step.get("feedback", context.get("feedback", []))
            
            analysis = await self.analyze_feedback(feedback)
            return {"feedback_analysis": analysis}
            
        elif action == "generate_uat_report":
            uat_plan = step.get("uat_plan", context.get("uat_plan", {}))
            feedback_analysis = step.get("feedback_analysis", context.get("feedback_analysis", {}))
            
            report = await self.generate_uat_report(uat_plan, feedback_analysis)
            return {"uat_report": report}
            
        elif action == "create_test_suite":
            features = step.get("features", context.get("features", []))
            
            test_suite = await self.create_test_suite(features)
            return {"test_suite": test_suite}
            
        else:
            return await super().run_playbook_step(step, context)
    
    async def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executes the UAT agent's playbook, running each step sequentially and aggregating results.
        
        Args:
            context: Optional dictionary providing initial execution context.
        
        Returns:
            A dictionary containing the agent name, playbook name, step results, and any generated UAT artifacts such as the plan, test scenarios, feedback form, feedback analysis, and report.
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
        
        # Add final UAT artifacts
        if "uat_plan" in context:
            results["uat_plan"] = context["uat_plan"]
            
        if "test_scenarios" in context:
            results["test_scenarios"] = context["test_scenarios"]
            
        if "feedback_form" in context:
            results["feedback_form"] = context["feedback_form"]
            
        if "feedback_analysis" in context:
            results["feedback_analysis"] = context["feedback_analysis"]
            
        if "uat_report" in context:
            results["uat_report"] = context["uat_report"]
            
        return results
    
    async def create_test_suite(self, features: List[str]) -> Dict[str, Any]:
        """
        Asynchronously creates and stores a test suite for the specified features.
        
        Generates test cases for each feature, aggregates them into a test suite with metadata, and stores the suite in memory. Returns the created test suite dictionary.
        
        Args:
            features: A list of feature names to generate test cases for.
        
        Returns:
            A dictionary representing the created test suite, including its ID, features, test cases, and creation timestamp.
        
        Raises:
            HTTPException: If test suite creation fails due to an error.
        """
        try:
            test_cases = []
            
            for feature in features:
                feature_tests = await self._generate_test_cases(feature)
                test_cases.extend(feature_tests)
            
            test_suite = {
                "id": f"suite_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "features": features,
                "test_cases": test_cases,
                "created_at": datetime.now().isoformat()
            }
            
            # Store test suite in memory
            await self.memory_manager.store_test_suite(test_suite)
            
            return test_suite
        except Exception as e:
            logger.error(f"Test suite creation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Test suite creation failed: {str(e)}"
            )
            
    async def _generate_test_cases(self, feature: str) -> List[TestCase]:
        """
        Generates a list of test cases for a specified feature.
        
        Args:
            feature: The feature name for which to generate test cases (e.g., "documentation", "navigation", "search", "responsive").
        
        Returns:
            A list of TestCase objects relevant to the given feature.
        """
        test_cases = []
        
        if feature == "documentation":
            test_cases.extend(self._generate_documentation_tests())
        elif feature == "navigation":
            test_cases.extend(self._generate_navigation_tests())
        elif feature == "search":
            test_cases.extend(self._generate_search_tests())
        elif feature == "responsive":
            test_cases.extend(self._generate_responsive_tests())
            
        return test_cases
        
    def _generate_documentation_tests(self) -> List[TestCase]:
        """
        Creates test cases to validate documentation structure and code example formatting.
        
        Returns:
            A list of TestCase objects covering documentation hierarchy and code example usability.
        """
        return [
            TestCase(
                id="DOC_001",
                title="Documentation Structure",
                description="Verify documentation hierarchy and organization",
                steps=[
                    {"step": "1", "action": "Navigate to documentation home"},
                    {"step": "2", "action": "Check sidebar navigation"},
                    {"step": "3", "action": "Verify section organization"}
                ],
                expected_result="Documentation is properly organized with clear hierarchy",
                category="documentation",
                priority="high"
            ),
            TestCase(
                id="DOC_002",
                title="Code Examples",
                description="Verify code examples are properly formatted and copyable",
                steps=[
                    {"step": "1", "action": "Navigate to code example section"},
                    {"step": "2", "action": "Check code block formatting"},
                    {"step": "3", "action": "Test copy functionality"}
                ],
                expected_result="Code examples are well-formatted and can be copied",
                category="documentation",
                priority="medium"
            )
        ]
        
    def _generate_navigation_tests(self) -> List[TestCase]:
        """
        Creates a list of navigation-related test cases for verifying main and breadcrumb navigation functionality.
        
        Returns:
            A list of TestCase objects covering main navigation and breadcrumb navigation scenarios.
        """
        return [
            TestCase(
                id="NAV_001",
                title="Main Navigation",
                description="Verify main navigation functionality",
                steps=[
                    {"step": "1", "action": "Click each navigation item"},
                    {"step": "2", "action": "Verify correct page loads"},
                    {"step": "3", "action": "Check active state indication"}
                ],
                expected_result="Navigation works correctly with proper state indication",
                category="navigation",
                priority="high"
            ),
            TestCase(
                id="NAV_002",
                title="Breadcrumb Navigation",
                description="Verify breadcrumb navigation functionality",
                steps=[
                    {"step": "1", "action": "Navigate to deep page"},
                    {"step": "2", "action": "Check breadcrumb trail"},
                    {"step": "3", "action": "Test breadcrumb links"}
                ],
                expected_result="Breadcrumb navigation is accurate and functional",
                category="navigation",
                priority="medium"
            )
        ]
        
    def _generate_search_tests(self) -> List[TestCase]:
        """
        Creates predefined test cases for verifying search functionality and performance.
        
        Returns:
            A list of TestCase objects covering search correctness and response time.
        """
        return [
            TestCase(
                id="SEARCH_001",
                title="Search Functionality",
                description="Verify search feature works correctly",
                steps=[
                    {"step": "1", "action": "Enter search term"},
                    {"step": "2", "action": "Check search results"},
                    {"step": "3", "action": "Verify result relevance"}
                ],
                expected_result="Search returns relevant results",
                category="search",
                priority="high"
            ),
            TestCase(
                id="SEARCH_002",
                title="Search Performance",
                description="Verify search response time",
                steps=[
                    {"step": "1", "action": "Perform multiple searches"},
                    {"step": "2", "action": "Measure response times"},
                    {"step": "3", "action": "Check result caching"}
                ],
                expected_result="Search responds within acceptable time limits",
                category="search",
                priority="medium"
            )
        ]
        
    def _generate_responsive_tests(self) -> List[TestCase]:
        """
        Creates test cases to verify the application's responsiveness on mobile and tablet devices.
        
        Returns:
            A list of TestCase objects covering mobile and tablet compatibility, including viewport adaptation and touch interaction checks.
        """
        return [
            TestCase(
                id="RESP_001",
                title="Mobile Responsiveness",
                description="Verify mobile device compatibility",
                steps=[
                    {"step": "1", "action": "Set viewport to mobile size"},
                    {"step": "2", "action": "Check layout adaptation"},
                    {"step": "3", "action": "Test touch interactions"}
                ],
                expected_result="Site works properly on mobile devices",
                category="responsive",
                priority="high"
            ),
            TestCase(
                id="RESP_002",
                title="Tablet Responsiveness",
                description="Verify tablet device compatibility",
                steps=[
                    {"step": "1", "action": "Set viewport to tablet size"},
                    {"step": "2", "action": "Check layout adaptation"},
                    {"step": "3", "action": "Test touch interactions"}
                ],
                expected_result="Site works properly on tablet devices",
                category="responsive",
                priority="medium"
            )
        ]
        
    async def execute_test_case(self, test_case: TestCase) -> TestResult:
        """
        Executes a single test case by running each step and recording the outcome.
        
        If any step fails, returns a failed TestResult immediately with collected logs and screenshots. On success, returns a passed TestResult and stores it in the agent's test results.
        """
        try:
            start_time = datetime.now()
            
            # Execute test steps
            logs = []
            screenshots = []
            
            for step in test_case.steps:
                step_result = await self._execute_test_step(step)
                logs.extend(step_result["logs"])
                screenshots.extend(step_result["screenshots"])
                
                if step_result["status"] == "failed":
                    return TestResult(
                        test_case_id=test_case.id,
                        status="failed",
                        actual_result=step_result["message"],
                        screenshots=screenshots,
                        logs=logs,
                        execution_time=(datetime.now() - start_time).total_seconds(),
                        executed_at=datetime.now()
                    )
            
            # Test passed if all steps completed
            result = TestResult(
                test_case_id=test_case.id,
                status="passed",
                actual_result="All steps completed successfully",
                screenshots=screenshots,
                logs=logs,
                execution_time=(datetime.now() - start_time).total_seconds(),
                executed_at=datetime.now()
            )
            
            # Store result
            self.test_results[test_case.id] = result
            
            return result
        except Exception as e:
            logger.error(f"Test case execution failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Test case execution failed: {str(e)}"
            )
            
    async def _execute_test_step(self, step: Dict[str, str]) -> Dict[str, Any]:
        """
        Executes a single test step by interpreting its action and interacting with the browser.
        
        Supports navigation, clicking elements, checking element existence, and setting viewport size.
        Returns a dictionary with the step's status, message, logs, and screenshots.
        """
        try:
            action = step["action"]
            logs = []
            screenshots = []
            
            # Navigate
            if action.startswith("Navigate"):
                await self.browser_tools.navigate(action.split(" to ")[1])
                screenshots.append(await self.browser_tools.take_screenshot())
                
            # Click
            elif action.startswith("Click"):
                element = action.split("Click ")[1]
                await self.browser_tools.click(f"[data-testid='{element}']")
                
            # Check
            elif action.startswith("Check"):
                element = action.split("Check ")[1]
                exists = await self.browser_tools.element_exists(f"[data-testid='{element}']")
                if not exists:
                    return {
                        "status": "failed",
                        "message": f"Element {element} not found",
                        "logs": logs,
                        "screenshots": screenshots
                    }
                
            # Set viewport
            elif action.startswith("Set viewport"):
                size = action.split("to ")[1]
                await self.browser_tools.set_viewport(size)
                screenshots.append(await self.browser_tools.take_screenshot())
                
            return {
                "status": "passed",
                "message": f"Step '{action}' completed successfully",
                "logs": logs,
                "screenshots": screenshots
            }
        except Exception as e:
            logger.error(f"Test step execution failed: {str(e)}")
            return {
                "status": "failed",
                "message": str(e),
                "logs": logs,
                "screenshots": screenshots
            }
            
    async def generate_test_report(self, test_results: List[TestResult]) -> Dict[str, Any]:
        """
        Generates a summary report from a list of test results.
        
        The report includes total, passed, and failed test counts, pass rate, detailed results, total execution time, and a generation timestamp. The report is stored in memory and returned as a dictionary.
        
        Args:
            test_results: List of TestResult objects to summarize.
        
        Returns:
            A dictionary containing the test report summary, detailed results, execution time, and timestamp.
        
        Raises:
            HTTPException: If report generation or storage fails.
        """
        try:
            total_tests = len(test_results)
            passed_tests = len([r for r in test_results if r.status == "passed"])
            failed_tests = len([r for r in test_results if r.status == "failed"])
            
            report = {
                "summary": {
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "failed_tests": failed_tests,
                    "pass_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0
                },
                "results": [result.dict() for result in test_results],
                "execution_time": sum(r.execution_time for r in test_results),
                "generated_at": datetime.now().isoformat()
            }
            
            # Store report in memory
            await self.memory_manager.store_test_report(report)
            
            return report
        except Exception as e:
            logger.error(f"Test report generation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Test report generation failed: {str(e)}"
            )