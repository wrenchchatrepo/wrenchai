# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Any, Optional, Union
import yaml
import logging
import asyncio
import json
from pathlib import Path

from .journey_agent import JourneyAgent

class Codifier(JourneyAgent):
    """
    Documentation specialist focused on technical writing.
    
    Core responsibilities:
    1. Create technical documentation
    2. Maintain documentation accuracy
    3. Generate API documentation
    4. Write user guides
    5. Document system architecture
    """
    
    def __init__(self, 
                name: str, 
                llm: Any, 
                tools: List[str], 
                playbook_path: str,
                doc_standards: Optional[Dict[str, Any]] = None,
                templates: Optional[Dict[str, str]] = None):
        """Initialize the Codifier agent.
        
        Args:
            name: Agent name
            llm: Language model to use
            tools: List of tool names
            playbook_path: Path to the playbook file
            doc_standards: Optional documentation standards
            templates: Optional document templates
        """
        super().__init__(name, llm, tools, playbook_path)
        
        self.doc_standards = doc_standards or {
            "structure": {
                "overview": "High-level description of the component/system",
                "prerequisites": "Required knowledge, software, or resources",
                "installation": "Step-by-step installation instructions",
                "usage": "How to use the component/system",
                "api_reference": "Detailed API documentation",
                "examples": "Code examples and use cases",
                "troubleshooting": "Common issues and solutions"
            },
            "styling": {
                "headers": "Use Markdown headers (# for top level)",
                "code_blocks": "Use triple backticks with language specification",
                "diagrams": "Use Mermaid diagrams for technical flows",
                "links": "Use descriptive link text",
                "images": "Include alt text for accessibility"
            },
            "frequency": {
                "api_docs": "Update with every API change",
                "user_guides": "Update with every release",
                "architecture": "Update with significant design changes"
            }
        }
        
        self.templates = templates or {}
        
        # Check tools availability
        required_tools = ["document_tool"]
        for tool in required_tools:
            if tool not in tools:
                logging.warning(f"Codifier agent should have '{tool}' tool")
                
    async def generate_technical_docs(self, 
                                   codebase: Dict[str, Any], 
                                   doc_type: str = "api") -> Dict[str, Any]:
        """Generate technical documentation.
        
        Args:
            codebase: Codebase information (files, structure, etc.)
            doc_type: Type of documentation (api, user_guide, architecture)
            
        Returns:
            Generated documentation
        """
        docs = {
            "content": "",
            "sections": [],
            "examples": [],
            "diagrams": []
        }
        
        # Create documentation prompt
        doc_prompt = f"""
        Generate {doc_type} documentation for the following codebase:
        {json.dumps(codebase, indent=2)}
        
        Documentation standards:
        {json.dumps(self.doc_standards, indent=2)}
        
        Please provide:
        1. Complete documentation content in Markdown format
        2. Section structure with headings
        3. Code examples
        4. Diagrams (described in text/Mermaid format)
        
        Format your response as JSON with the following structure:
        {{
            "content": "# Full Documentation\\n\\n... complete Markdown content ...",
            "sections": [
                {{
                    "title": "Overview",
                    "content": "This is an overview of the system..."
                }}
            ],
            "examples": [
                {{
                    "title": "Basic Usage",
                    "language": "python",
                    "code": "import example\\n\\nexample.run()"
                }}
            ],
            "diagrams": [
                {{
                    "title": "System Architecture",
                    "type": "mermaid",
                    "content": "graph TD;\\n    A-->B;\\n    A-->C;"
                }}
            ]
        }}
        """
        
        # Generate documentation using LLM
        doc_result = await self.llm.process({"prompt": doc_prompt})
        
        # Parse response
        if isinstance(doc_result, dict) and "output" in doc_result:
            try:
                parsed_result = json.loads(doc_result["output"])
                docs["content"] = parsed_result.get("content", "")
                docs["sections"] = parsed_result.get("sections", [])
                docs["examples"] = parsed_result.get("examples", [])
                docs["diagrams"] = parsed_result.get("diagrams", [])
            except json.JSONDecodeError:
                logging.error("Failed to parse documentation result")
                docs["error"] = "Failed to parse result"
                docs["content"] = doc_result.get("output", "")
        
        return docs
    
    async def generate_api_docs(self, 
                           api_definition: Dict[str, Any], 
                           format: str = "markdown") -> Dict[str, Any]:
        """Generate API documentation.
        
        Args:
            api_definition: API definition (endpoints, methods, etc.)
            format: Output format (markdown, openapi, html)
            
        Returns:
            API documentation
        """
        api_text = json.dumps(api_definition, indent=2)
        
        api_prompt = f"""
        Generate API documentation in {format} format for the following API:
        {api_text}
        
        Documentation standards:
        {json.dumps(self.doc_standards, indent=2)}
        
        Please include:
        1. Endpoint descriptions
        2. Request parameters
        3. Response formats
        4. Error codes
        5. Example requests and responses
        
        Format your response as JSON with comprehensive API documentation.
        """
        
        # Generate API docs using LLM
        api_result = await self.llm.process({"prompt": api_prompt})
        
        if isinstance(api_result, dict) and "output" in api_result:
            try:
                return json.loads(api_result["output"])
            except json.JSONDecodeError:
                return {
                    "content": api_result["output"],
                    "format": format
                }
        
        return {"error": "Failed to generate API documentation"}
    
    async def create_user_guide(self, 
                           system_info: Dict[str, Any], 
                           audience: str = "technical") -> Dict[str, Any]:
        """Create user guide.
        
        Args:
            system_info: System information
            audience: Target audience (technical, non-technical, admin)
            
        Returns:
            User guide
        """
        system_text = json.dumps(system_info, indent=2)
        
        guide_prompt = f"""
        Create a user guide for a {audience} audience for the following system:
        {system_text}
        
        Documentation standards:
        {json.dumps(self.doc_standards, indent=2)}
        
        Please include:
        1. System overview
        2. Installation instructions
        3. Configuration steps
        4. Usage instructions
        5. Troubleshooting
        
        Format your response as JSON with complete user guide content.
        """
        
        # Generate user guide using LLM
        guide_result = await self.llm.process({"prompt": guide_prompt})
        
        if isinstance(guide_result, dict) and "output" in guide_result:
            try:
                return json.loads(guide_result["output"])
            except json.JSONDecodeError:
                return {
                    "content": guide_result["output"],
                    "audience": audience
                }
        
        return {"error": "Failed to generate user guide"}
    
    async def document_architecture(self, 
                               system_architecture: Dict[str, Any], 
                               detail_level: str = "high") -> Dict[str, Any]:
        """Document system architecture.
        
        Args:
            system_architecture: System architecture information
            detail_level: Level of detail (high, medium, low)
            
        Returns:
            Architecture documentation
        """
        arch_text = json.dumps(system_architecture, indent=2)
        
        arch_prompt = f"""
        Create {detail_level}-detail architecture documentation for the following system:
        {arch_text}
        
        Documentation standards:
        {json.dumps(self.doc_standards, indent=2)}
        
        Please include:
        1. Architecture overview
        2. Component descriptions
        3. Data flow diagrams
        4. Technology stack
        5. Deployment architecture
        
        Format your response as JSON with architecture documentation including diagrams.
        """
        
        # Generate architecture documentation using LLM
        arch_result = await self.llm.process({"prompt": arch_prompt})
        
        if isinstance(arch_result, dict) and "output" in arch_result:
            try:
                return json.loads(arch_result["output"])
            except json.JSONDecodeError:
                return {
                    "content": arch_result["output"],
                    "detail_level": detail_level
                }
        
        return {"error": "Failed to generate architecture documentation"}
    
    async def run_playbook_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific playbook step.
        
        Args:
            step: Playbook step definition
            context: Execution context
            
        Returns:
            Step execution results
        """
        action = step.get("action", "")
        
        if action == "generate_technical_docs":
            codebase = step.get("codebase", context.get("codebase", {}))
            doc_type = step.get("doc_type", "api")
            
            docs = await self.generate_technical_docs(codebase, doc_type)
            return {"technical_docs": docs}
            
        elif action == "generate_api_docs":
            api_definition = step.get("api_definition", context.get("api_definition", {}))
            format = step.get("format", "markdown")
            
            api_docs = await self.generate_api_docs(api_definition, format)
            return {"api_docs": api_docs}
            
        elif action == "create_user_guide":
            system_info = step.get("system_info", context.get("system_info", {}))
            audience = step.get("audience", "technical")
            
            user_guide = await self.create_user_guide(system_info, audience)
            return {"user_guide": user_guide}
            
        elif action == "document_architecture":
            system_architecture = step.get("system_architecture", context.get("system_architecture", {}))
            detail_level = step.get("detail_level", "high")
            
            arch_docs = await self.document_architecture(system_architecture, detail_level)
            return {"architecture_docs": arch_docs}
            
        else:
            return await super().run_playbook_step(step, context)
    
    async def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the Codifier agent with the specified playbook.
        
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
        
        # Add final documents
        if "technical_docs" in context:
            results["technical_docs"] = context["technical_docs"]
            
        if "api_docs" in context:
            results["api_docs"] = context["api_docs"]
            
        if "user_guide" in context:
            results["user_guide"] = context["user_guide"]
            
        if "architecture_docs" in context:
            results["architecture_docs"] = context["architecture_docs"]
            
        return results