# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Any, Optional, Union
import yaml
import logging
import asyncio
import json
from pathlib import Path

from .journey_agent import JourneyAgent

class CodeGenerator(JourneyAgent):
    """
    Comprehensive development agent covering frontend, backend, and integration.
    
    Core responsibilities:
    1. Develop and maintain frontend applications
    2. Implement backend services and APIs
    3. Handle database interactions
    4. Manage system integrations
    5. Ensure code quality and best practices
    """
    
    def __init__(self, 
                name: str, 
                llm: Any, 
                tools: List[str], 
                playbook_path: str,
                code_standards: Optional[Dict[str, Any]] = None,
                frameworks: Optional[List[str]] = None):
        """Initialize the CodeGenerator agent.
        
        Args:
            name: Agent name
            llm: Language model to use
            tools: List of tool names
            playbook_path: Path to the playbook file
            code_standards: Optional dict of code standards to enforce
            frameworks: Optional list of frameworks to use
        """
        super().__init__(name, llm, tools, playbook_path)
        
        self.code_standards = code_standards or {
            "indentation": 4,
            "line_length": 100,
            "documentation_required": True,
            "testing_required": True
        }
        
        self.frameworks = frameworks or []
        
        # Check tools availability
        required_tools = ["code_execution", "github_tool"]
        for tool in required_tools:
            if tool not in tools:
                logging.warning(f"CodeGenerator agent should have '{tool}' tool")
                
    async def generate_code(self, 
                          specification: Dict[str, Any], 
                          language: str, 
                          framework: Optional[str] = None) -> Dict[str, Any]:
        """Generate code based on specification.
        
        Args:
            specification: Code specification dictionary
            language: Programming language to use
            framework: Optional framework to use
            
        Returns:
            Generated code files and documentation
        """
        result = {
            "files": [],
            "documentation": "",
            "tests": []
        }
        
        # Create specification prompt
        spec_prompt = f"""
        Generate code based on the following specification:
        {json.dumps(specification, indent=2)}
        
        Language: {language}
        Framework: {framework or "None"}
        
        Code standards:
        {json.dumps(self.code_standards, indent=2)}
        
        Please provide:
        1. Code files with implementation
        2. Documentation
        3. Tests (if required by standards)
        
        Format your response as JSON with the following structure:
        {{
            "files": [
                {{
                    "filename": "example.py",
                    "content": "def example():\\n    return True"
                }}
            ],
            "documentation": "# Documentation\\n...",
            "tests": [
                {{
                    "filename": "test_example.py",
                    "content": "def test_example():\\n    assert example() is True"
                }}
            ]
        }}
        """
        
        # Generate code using LLM
        generation_result = await self.llm.process({"prompt": spec_prompt})
        
        # Parse response
        if isinstance(generation_result, dict) and "output" in generation_result:
            try:
                parsed_result = json.loads(generation_result["output"])
                result["files"] = parsed_result.get("files", [])
                result["documentation"] = parsed_result.get("documentation", "")
                result["tests"] = parsed_result.get("tests", [])
            except json.JSONDecodeError:
                logging.error("Failed to parse code generation result")
                result["error"] = "Failed to parse result"
        
        return result
    
    async def review_code(self, files: List[Dict[str, str]]) -> Dict[str, Any]:
        """Review code for quality and standards compliance.
        
        Args:
            files: List of files to review
            
        Returns:
            Code review results
        """
        files_content = "\n\n".join([
            f"File: {file['filename']}\n```\n{file['content']}\n```"
            for file in files
        ])
        
        review_prompt = f"""
        Review the following code for quality and standards compliance:
        
        {files_content}
        
        Code standards:
        {json.dumps(self.code_standards, indent=2)}
        
        Please provide:
        1. Overall code quality assessment
        2. Issues found (if any)
        3. Recommendations for improvement
        
        Format your response as JSON.
        """
        
        # Generate review using LLM
        review_result = await self.llm.process({"prompt": review_prompt})
        
        # Parse response
        if isinstance(review_result, dict) and "output" in review_result:
            try:
                return json.loads(review_result["output"])
            except json.JSONDecodeError:
                return {"error": "Failed to parse review result"}
        
        return {"error": "Failed to generate review"}
    
    async def create_api_docs(self, 
                           files: List[Dict[str, str]], 
                           format: str = "markdown") -> str:
        """Generate API documentation.
        
        Args:
            files: List of files to document
            format: Documentation format (markdown, openapi, etc.)
            
        Returns:
            Generated API documentation
        """
        files_content = "\n\n".join([
            f"File: {file['filename']}\n```\n{file['content']}\n```"
            for file in files
        ])
        
        docs_prompt = f"""
        Generate API documentation for the following code:
        
        {files_content}
        
        Format: {format}
        
        Please extract all API endpoints, parameters, return values, and provide
        clear descriptions for each.
        """
        
        # Generate docs using LLM
        docs_result = await self.llm.process({"prompt": docs_prompt})
        
        if isinstance(docs_result, dict) and "output" in docs_result:
            return docs_result["output"]
        
        return "Error generating API documentation"
    
    async def integrate_code(self, 
                          new_files: List[Dict[str, str]], 
                          existing_files: List[Dict[str, str]]) -> Dict[str, Any]:
        """Plan integration of new code with existing codebase.
        
        Args:
            new_files: List of new files
            existing_files: List of existing files
            
        Returns:
            Integration plan
        """
        new_content = "\n\n".join([
            f"New File: {file['filename']}\n```\n{file['content']}\n```"
            for file in new_files
        ])
        
        existing_content = "\n\n".join([
            f"Existing File: {file['filename']}\n```\n{file['content']}\n```"
            for file in existing_files
        ])
        
        integration_prompt = f"""
        Plan the integration of new code with the existing codebase:
        
        {new_content}
        
        Existing codebase:
        {existing_content}
        
        Please provide:
        1. Integration steps
        2. Potential conflicts
        3. Required modifications
        4. Testing approach
        
        Format your response as JSON.
        """
        
        # Generate integration plan using LLM
        integration_result = await self.llm.process({"prompt": integration_prompt})
        
        if isinstance(integration_result, dict) and "output" in integration_result:
            try:
                return json.loads(integration_result["output"])
            except json.JSONDecodeError:
                return {"raw_plan": integration_result["output"]}
        
        return {"error": "Failed to generate integration plan"}
    
    async def run_playbook_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific playbook step.
        
        Args:
            step: Playbook step definition
            context: Execution context
            
        Returns:
            Step execution results
        """
        action = step.get("action", "")
        
        if action == "generate_code":
            specification = step.get("specification", context.get("specification", {}))
            language = step.get("language", context.get("language", "python"))
            framework = step.get("framework", context.get("framework"))
            
            code_result = await self.generate_code(specification, language, framework)
            return {"code_result": code_result}
            
        elif action == "review_code":
            files = step.get("files", context.get("code_result", {}).get("files", []))
            review = await self.review_code(files)
            return {"review": review}
            
        elif action == "create_api_docs":
            files = step.get("files", context.get("code_result", {}).get("files", []))
            format = step.get("format", "markdown")
            docs = await self.create_api_docs(files, format)
            return {"api_docs": docs}
            
        elif action == "integrate_code":
            new_files = step.get("new_files", context.get("code_result", {}).get("files", []))
            existing_files = step.get("existing_files", [])
            integration = await self.integrate_code(new_files, existing_files)
            return {"integration": integration}
            
        else:
            return await super().run_playbook_step(step, context)
    
    async def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the CodeGenerator agent with the specified playbook.
        
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
        
        # Add final code and documentation if available
        if "code_result" in context:
            results["code"] = context["code_result"]
            
        if "api_docs" in context:
            results["documentation"] = context["api_docs"]
            
        return results