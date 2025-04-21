# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Any, Optional, Union
import yaml
import logging
import asyncio
import json
from pathlib import Path

from .journey_agent import JourneyAgent

class UXDesigner(JourneyAgent):
    """
    User experience design specialist focused on frontend interfaces.
    
    Core responsibilities:
    1. Create user-centered designs
    2. Develop wireframes and prototypes
    3. Implement responsive layouts
    4. Ensure accessibility compliance
    5. Conduct usability testing
    """
    
    def __init__(self, 
                name: str, 
                llm: Any, 
                tools: List[str], 
                playbook_path: str,
                design_system: Optional[Dict[str, Any]] = None,
                accessibility_standards: Optional[List[str]] = None):
        """Initialize the UXDesigner agent.
        
        Args:
            name: Agent name
            llm: Language model to use
            tools: List of tool names
            playbook_path: Path to the playbook file
            design_system: Optional design system configuration
            accessibility_standards: Optional list of accessibility standards to follow
        """
        super().__init__(name, llm, tools, playbook_path)
        
        self.design_system = design_system or {
            "typography": {
                "heading_font": "Inter",
                "body_font": "Inter",
                "scale": "1.25"
            },
            "colors": {
                "primary": "#0066CC",
                "secondary": "#6C757D",
                "success": "#28A745",
                "warning": "#FFC107",
                "danger": "#DC3545",
                "info": "#17A2B8",
                "background": "#FFFFFF",
                "text": "#212529"
            },
            "spacing": {
                "base": "16px",
                "scale": "1.5"
            }
        }
        
        self.accessibility_standards = accessibility_standards or ["WCAG 2.1 AA"]
        
        # Check tools availability
        required_tools = ["design_tool"]
        for tool in required_tools:
            if tool not in tools:
                logging.warning(f"UXDesigner agent should have '{tool}' tool")
                
    async def create_wireframe(self, 
                             requirements: Dict[str, Any], 
                             platform: str = "web", 
                             fidelity: str = "medium") -> Dict[str, Any]:
        """Create wireframe based on requirements.
        
        Args:
            requirements: Design requirements
            platform: Target platform (web, mobile, etc.)
            fidelity: Wireframe fidelity level (low, medium, high)
            
        Returns:
            Wireframe specifications
        """
        wireframe = {
            "screens": [],
            "components": [],
            "description": "",
            "user_flows": []
        }
        
        # Create wireframe prompt
        wireframe_prompt = f"""
        Create a {fidelity}-fidelity wireframe for {platform} platform based on the following requirements:
        {json.dumps(requirements, indent=2)}
        
        Design system:
        {json.dumps(self.design_system, indent=2)}
        
        Accessibility standards:
        {', '.join(self.accessibility_standards)}
        
        Please provide:
        1. Screen layouts with component placement
        2. Component descriptions and interactions
        3. User flows showing screen connections
        4. Design rationale
        
        Format your response as JSON with the following structure:
        {{
            "screens": [
                {{
                    "name": "Home",
                    "layout": "Detailed layout description...",
                    "components": ["Header", "Hero", "Footer"]
                }}
            ],
            "components": [
                {{
                    "name": "Header",
                    "description": "Navigation header with logo and links",
                    "interactions": ["Click on logo returns to home", "Hover on links shows dropdown"]
                }}
            ],
            "description": "Overall wireframe description...",
            "user_flows": [
                {{
                    "name": "User Registration",
                    "steps": ["Landing -> Registration Form -> Confirmation"]
                }}
            ]
        }}
        """
        
        # Generate wireframe using LLM
        wireframe_result = await self.llm.process({"prompt": wireframe_prompt})
        
        # Parse response
        if isinstance(wireframe_result, dict) and "output" in wireframe_result:
            try:
                parsed_result = json.loads(wireframe_result["output"])
                wireframe["screens"] = parsed_result.get("screens", [])
                wireframe["components"] = parsed_result.get("components", [])
                wireframe["description"] = parsed_result.get("description", "")
                wireframe["user_flows"] = parsed_result.get("user_flows", [])
            except json.JSONDecodeError:
                logging.error("Failed to parse wireframe result")
                wireframe["error"] = "Failed to parse result"
        
        return wireframe
    
    async def evaluate_accessibility(self, design: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate design for accessibility compliance.
        
        Args:
            design: Design specification
            
        Returns:
            Accessibility evaluation results
        """
        screens_text = "\n\n".join([
            f"Screen: {screen['name']}\nLayout: {screen['layout']}"
            for screen in design.get("screens", [])
        ])
        
        components_text = "\n\n".join([
            f"Component: {component['name']}\nDescription: {component['description']}"
            for component in design.get("components", [])
        ])
        
        accessibility_prompt = f"""
        Evaluate the following design for accessibility compliance with {', '.join(self.accessibility_standards)}:
        
        Screens:
        {screens_text}
        
        Components:
        {components_text}
        
        Please provide:
        1. Overall accessibility assessment
        2. Issues found (if any)
        3. Recommendations for improvement
        
        Format your response as JSON with severity levels (critical, major, minor) for each issue.
        """
        
        # Generate evaluation using LLM
        evaluation_result = await self.llm.process({"prompt": accessibility_prompt})
        
        # Parse response
        if isinstance(evaluation_result, dict) and "output" in evaluation_result:
            try:
                return json.loads(evaluation_result["output"])
            except json.JSONDecodeError:
                return {"error": "Failed to parse evaluation result"}
        
        return {"error": "Failed to generate evaluation"}
    
    async def create_responsive_design(self, 
                                 wireframe: Dict[str, Any], 
                                 breakpoints: List[str] = None) -> Dict[str, Any]:
        """Create responsive design variations based on wireframe.
        
        Args:
            wireframe: Base wireframe
            breakpoints: Design breakpoints (sm, md, lg, xl)
            
        Returns:
            Responsive design specifications
        """
        breakpoints = breakpoints or ["sm", "md", "lg", "xl"]
        
        wireframe_text = json.dumps(wireframe, indent=2)
        
        responsive_prompt = f"""
        Create responsive design variations for the following wireframe:
        {wireframe_text}
        
        Design system:
        {json.dumps(self.design_system, indent=2)}
        
        Breakpoints: {', '.join(breakpoints)}
        
        For each breakpoint, describe:
        1. Layout adjustments
        2. Component sizing changes
        3. Typography adaptations
        4. Navigation behavior
        
        Format your response as JSON with breakpoint-specific variations.
        """
        
        # Generate responsive design using LLM
        responsive_result = await self.llm.process({"prompt": responsive_prompt})
        
        if isinstance(responsive_result, dict) and "output" in responsive_result:
            try:
                return json.loads(responsive_result["output"])
            except json.JSONDecodeError:
                return {"raw_design": responsive_result["output"]}
        
        return {"error": "Failed to generate responsive design"}
    
    async def create_usability_test(self, design: Dict[str, Any]) -> Dict[str, Any]:
        """Create usability test plan for design.
        
        Args:
            design: Design specification
            
        Returns:
            Usability test plan
        """
        design_text = json.dumps(design, indent=2)
        
        test_prompt = f"""
        Create a usability test plan for the following design:
        {design_text}
        
        Please include:
        1. Test objectives
        2. Participant profiles
        3. Test scenarios
        4. Task instructions
        5. Evaluation metrics
        6. Data collection methods
        
        Format your response as JSON with a comprehensive test structure.
        """
        
        # Generate test plan using LLM
        test_result = await self.llm.process({"prompt": test_prompt})
        
        if isinstance(test_result, dict) and "output" in test_result:
            try:
                return json.loads(test_result["output"])
            except json.JSONDecodeError:
                return {"raw_plan": test_result["output"]}
        
        return {"error": "Failed to generate test plan"}
    
    async def run_playbook_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific playbook step.
        
        Args:
            step: Playbook step definition
            context: Execution context
            
        Returns:
            Step execution results
        """
        action = step.get("action", "")
        
        if action == "create_wireframe":
            requirements = step.get("requirements", context.get("requirements", {}))
            platform = step.get("platform", "web")
            fidelity = step.get("fidelity", "medium")
            
            wireframe = await self.create_wireframe(requirements, platform, fidelity)
            return {"wireframe": wireframe}
            
        elif action == "evaluate_accessibility":
            design = step.get("design", context.get("wireframe", {}))
            evaluation = await self.evaluate_accessibility(design)
            return {"accessibility_evaluation": evaluation}
            
        elif action == "create_responsive_design":
            wireframe = step.get("wireframe", context.get("wireframe", {}))
            breakpoints = step.get("breakpoints", ["sm", "md", "lg", "xl"])
            
            responsive_design = await self.create_responsive_design(wireframe, breakpoints)
            return {"responsive_design": responsive_design}
            
        elif action == "create_usability_test":
            design = step.get("design", context.get("wireframe", {}))
            test_plan = await self.create_usability_test(design)
            return {"usability_test": test_plan}
            
        else:
            return await super().run_playbook_step(step, context)
    
    async def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the UXDesigner agent with the specified playbook.
        
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
        
        # Add final design if available
        if "wireframe" in context:
            results["design"] = context["wireframe"]
            
        if "responsive_design" in context:
            results["responsive_variations"] = context["responsive_design"]
            
        return results