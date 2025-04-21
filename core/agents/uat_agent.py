# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Any, Optional, Union
import yaml
import logging
import asyncio
import json
from pathlib import Path

from .journey_agent import JourneyAgent

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
        """Initialize the UAT agent.
        
        Args:
            name: Agent name
            llm: Language model to use
            tools: List of tool names
            playbook_path: Path to the playbook file
            acceptance_criteria_template: Optional template for acceptance criteria
            stakeholders: Optional list of stakeholders
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
                
    async def create_uat_plan(self, 
                          project: Dict[str, Any], 
                          features: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a UAT plan.
        
        Args:
            project: Project information
            features: List of features to test
            
        Returns:
            UAT plan
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
        """Execute a specific playbook step.
        
        Args:
            step: Playbook step definition
            context: Execution context
            
        Returns:
            Step execution results
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
            
        else:
            return await super().run_playbook_step(step, context)
    
    async def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the UAT agent with the specified playbook.
        
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