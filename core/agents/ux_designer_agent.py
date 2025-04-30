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
from core.tools.memory_manager import MemoryManager

from .journey_agent import JourneyAgent

logger = logging.getLogger(__name__)

class DesignSpec(BaseModel):
    """Specification for design tasks"""
    theme: str = Field(..., description="Design theme (e.g., modern, minimal, corporate)")
    color_scheme: Dict[str, str] = Field(..., description="Color palette for the design")
    typography: Dict[str, str] = Field(..., description="Typography specifications")
    spacing: Dict[str, str] = Field(..., description="Spacing and layout rules")
    components: List[str] = Field(default_factory=list, description="Required components")
    responsive_breakpoints: Dict[str, int] = Field(..., description="Responsive design breakpoints")

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

class UXDesignerAgent:
    def __init__(self):
        self.memory_manager = MemoryManager()
        self.design_systems = {
            "modern": {
                "color_scheme": {
                    "primary": "#1B03A3",  # Neon Blue
                    "secondary": "#9D00FF",  # Neon Purple
                    "accent": "#FF10F0",  # Neon Pink
                    "background": "#FFFFFF",
                    "text": "#000000"
                },
                "typography": {
                    "heading": "Inter",
                    "body": "Inter",
                    "code": "JetBrains Mono"
                },
                "spacing": {
                    "base": "1rem",
                    "large": "2rem",
                    "small": "0.5rem"
                }
            },
            "minimal": {
                "color_scheme": {
                    "primary": "#000000",
                    "secondary": "#333333",
                    "accent": "#666666",
                    "background": "#FFFFFF",
                    "text": "#000000"
                },
                "typography": {
                    "heading": "SF Pro Display",
                    "body": "SF Pro Text",
                    "code": "SF Mono"
                },
                "spacing": {
                    "base": "1.5rem",
                    "large": "3rem",
                    "small": "0.75rem"
                }
            }
        }
        
    async def create_design_system(self, spec: DesignSpec) -> Dict[str, Any]:
        """Create a comprehensive design system based on specifications"""
        try:
            design_system = {
                "theme": spec.theme,
                "color_scheme": self._generate_color_scheme(spec),
                "typography": self._generate_typography(spec),
                "spacing": self._generate_spacing_system(spec),
                "components": await self._generate_component_library(spec),
                "responsive": self._generate_responsive_rules(spec)
            }
            
            # Store design system in memory
            await self.memory_manager.store_design_system(design_system)
            
            return design_system
        except Exception as e:
            logger.error(f"Design system creation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Design system creation failed: {str(e)}"
            )
            
    def _generate_color_scheme(self, spec: DesignSpec) -> Dict[str, str]:
        """Generate a complete color scheme with variations"""
        base_colors = spec.color_scheme
        return {
            **base_colors,
            "primary-light": self._lighten_color(base_colors["primary"]),
            "primary-dark": self._darken_color(base_colors["primary"]),
            "secondary-light": self._lighten_color(base_colors["secondary"]),
            "secondary-dark": self._darken_color(base_colors["secondary"]),
            "accent-light": self._lighten_color(base_colors["accent"]),
            "accent-dark": self._darken_color(base_colors["accent"])
        }
        
    def _generate_typography(self, spec: DesignSpec) -> Dict[str, Any]:
        """Generate typography system with scale and variants"""
        return {
            "fonts": spec.typography,
            "scale": {
                "h1": "2.5rem",
                "h2": "2rem",
                "h3": "1.75rem",
                "h4": "1.5rem",
                "body": "1rem",
                "small": "0.875rem"
            },
            "weights": {
                "light": 300,
                "regular": 400,
                "medium": 500,
                "bold": 700
            },
            "line-heights": {
                "tight": 1.2,
                "normal": 1.5,
                "loose": 1.8
            }
        }
        
    def _generate_spacing_system(self, spec: DesignSpec) -> Dict[str, Any]:
        """Generate comprehensive spacing system"""
        base = int(spec.spacing["base"].replace("rem", ""))
        return {
            "space": {
                "xxs": f"{base * 0.25}rem",
                "xs": f"{base * 0.5}rem",
                "sm": f"{base * 0.75}rem",
                "md": f"{base}rem",
                "lg": f"{base * 1.5}rem",
                "xl": f"{base * 2}rem",
                "xxl": f"{base * 3}rem"
            },
            "layout": {
                "container": "1200px",
                "content": "800px"
            }
        }
        
    async def _generate_component_library(self, spec: DesignSpec) -> Dict[str, Any]:
        """Generate component library specifications"""
        components = {
            "buttons": {
                "primary": {
                    "background": spec.color_scheme["primary"],
                    "color": "#FFFFFF",
                    "padding": "0.75rem 1.5rem",
                    "border-radius": "0.375rem"
                },
                "secondary": {
                    "background": spec.color_scheme["secondary"],
                    "color": "#FFFFFF",
                    "padding": "0.75rem 1.5rem",
                    "border-radius": "0.375rem"
                }
            },
            "cards": {
                "default": {
                    "background": "#FFFFFF",
                    "border-radius": "0.5rem",
                    "shadow": "0 4px 6px rgba(0, 0, 0, 0.1)"
                }
            },
            "navigation": {
                "header": {
                    "height": "4rem",
                    "background": "#FFFFFF"
                },
                "sidebar": {
                    "width": "16rem",
                    "background": "#F8F9FA"
                }
            }
        }
        
        # Add custom components based on spec
        for component in spec.components:
            if component not in components:
                components[component] = await self._generate_component_spec(component, spec)
                
        return components
        
    def _generate_responsive_rules(self, spec: DesignSpec) -> Dict[str, Any]:
        """Generate responsive design rules"""
        return {
            "breakpoints": spec.responsive_breakpoints,
            "containers": {
                "sm": "540px",
                "md": "720px",
                "lg": "960px",
                "xl": "1140px"
            },
            "grid": {
                "columns": 12,
                "gap": "1rem"
            }
        }
        
    async def _generate_component_spec(self, component: str, spec: DesignSpec) -> Dict[str, Any]:
        """Generate specification for a custom component"""
        # Implementation would depend on specific component requirements
        return {
            "background": spec.color_scheme["background"],
            "color": spec.color_scheme["text"],
            "padding": spec.spacing["base"],
            "border-radius": "0.375rem"
        }
        
    def _lighten_color(self, color: str, amount: float = 0.2) -> str:
        """Lighten a hex color"""
        # Implementation of color lightening logic
        return color  # Placeholder
        
    def _darken_color(self, color: str, amount: float = 0.2) -> str:
        """Darken a hex color"""
        # Implementation of color darkening logic
        return color  # Placeholder
        
    async def generate_design_tokens(self, spec: DesignSpec) -> Dict[str, Any]:
        """Generate design tokens for the design system"""
        try:
            design_system = await self.create_design_system(spec)
            
            tokens = {
                "colors": self._generate_color_tokens(design_system),
                "typography": self._generate_typography_tokens(design_system),
                "spacing": self._generate_spacing_tokens(design_system),
                "shadows": self._generate_shadow_tokens(),
                "animations": self._generate_animation_tokens()
            }
            
            return tokens
        except Exception as e:
            logger.error(f"Design token generation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Design token generation failed: {str(e)}"
            )
            
    def _generate_color_tokens(self, design_system: Dict[str, Any]) -> Dict[str, str]:
        """Generate color design tokens"""
        colors = design_system["color_scheme"]
        return {
            "--color-primary": colors["primary"],
            "--color-primary-light": colors["primary-light"],
            "--color-primary-dark": colors["primary-dark"],
            "--color-secondary": colors["secondary"],
            "--color-secondary-light": colors["secondary-light"],
            "--color-secondary-dark": colors["secondary-dark"],
            "--color-accent": colors["accent"],
            "--color-accent-light": colors["accent-light"],
            "--color-accent-dark": colors["accent-dark"],
            "--color-background": colors["background"],
            "--color-text": colors["text"]
        }
        
    def _generate_typography_tokens(self, design_system: Dict[str, Any]) -> Dict[str, str]:
        """Generate typography design tokens"""
        typography = design_system["typography"]
        return {
            "--font-family-heading": typography["fonts"]["heading"],
            "--font-family-body": typography["fonts"]["body"],
            "--font-family-code": typography["fonts"]["code"],
            "--font-size-h1": typography["scale"]["h1"],
            "--font-size-h2": typography["scale"]["h2"],
            "--font-size-h3": typography["scale"]["h3"],
            "--font-size-body": typography["scale"]["body"],
            "--font-weight-light": str(typography["weights"]["light"]),
            "--font-weight-regular": str(typography["weights"]["regular"]),
            "--font-weight-bold": str(typography["weights"]["bold"])
        }
        
    def _generate_spacing_tokens(self, design_system: Dict[str, Any]) -> Dict[str, str]:
        """Generate spacing design tokens"""
        spacing = design_system["spacing"]
        return {
            "--space-xxs": spacing["space"]["xxs"],
            "--space-xs": spacing["space"]["xs"],
            "--space-sm": spacing["space"]["sm"],
            "--space-md": spacing["space"]["md"],
            "--space-lg": spacing["space"]["lg"],
            "--space-xl": spacing["space"]["xl"],
            "--space-xxl": spacing["space"]["xxl"]
        }
        
    def _generate_shadow_tokens(self) -> Dict[str, str]:
        """Generate shadow design tokens"""
        return {
            "--shadow-sm": "0 1px 2px rgba(0, 0, 0, 0.05)",
            "--shadow-md": "0 4px 6px rgba(0, 0, 0, 0.1)",
            "--shadow-lg": "0 10px 15px rgba(0, 0, 0, 0.1)",
            "--shadow-xl": "0 20px 25px rgba(0, 0, 0, 0.15)"
        }
        
    def _generate_animation_tokens(self) -> Dict[str, str]:
        """Generate animation design tokens"""
        return {
            "--transition-fast": "150ms ease-in-out",
            "--transition-normal": "300ms ease-in-out",
            "--transition-slow": "500ms ease-in-out",
            "--ease-in-out": "cubic-bezier(0.4, 0, 0.2, 1)",
            "--ease-in": "cubic-bezier(0.4, 0, 1, 1)",
            "--ease-out": "cubic-bezier(0, 0, 0.2, 1)"
        }