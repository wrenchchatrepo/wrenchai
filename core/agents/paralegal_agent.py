# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Any, Optional, Union
import yaml
import logging
import asyncio
import json
from pathlib import Path
from datetime import datetime

from .journey_agent import JourneyAgent

class ParaLegal(JourneyAgent):
    """
    Legal documentation specialist.
    
    Core responsibilities:
    1. Review legal documents
    2. Draft legal agreements
    3. Ensure compliance
    4. Maintain legal records
    5. Support approval processes
    """
    
    def __init__(self, 
                name: str, 
                llm: Any, 
                tools: List[str], 
                playbook_path: str,
                document_templates: Optional[Dict[str, str]] = None,
                legal_requirements: Optional[Dict[str, List[str]]] = None):
        """Initialize the ParaLegal agent.
        
        Args:
            name: Agent name
            llm: Language model to use
            tools: List of tool names
            playbook_path: Path to the playbook file
            document_templates: Optional dictionary of document templates
            legal_requirements: Optional dictionary of legal requirements
        """
        super().__init__(name, llm, tools, playbook_path)
        
        self.document_templates = document_templates or {}
        
        self.legal_requirements = legal_requirements or {
            "privacy_policy": [
                "Data collection description",
                "Data use explanation",
                "User rights enumeration",
                "Opt-out procedures",
                "Contact information"
            ],
            "terms_of_service": [
                "Service description",
                "User obligations",
                "Prohibited activities",
                "Termination conditions",
                "Limitation of liability"
            ],
            "data_processing_agreement": [
                "Parties identification",
                "Processing scope",
                "Security measures",
                "Data breach procedures",
                "Audit rights"
            ]
        }
        
        # Check tools availability
        required_tools = ["document_tool", "legal_tool"]
        for tool in required_tools:
            if tool not in tools:
                logging.warning(f"ParaLegal agent should have '{tool}' tool")
                
    async def review_legal_document(self, 
                                document: Dict[str, Any], 
                                requirements: Optional[List[str]] = None) -> Dict[str, Any]:
        """Review a legal document.
        
        Args:
            document: Document to review
            requirements: Optional specific requirements to check
            
        Returns:
            Document review
        """
        review = {
            "timestamp": asyncio.get_event_loop().time(),
            "document_name": document.get("name", "Unnamed Document"),
            "document_type": document.get("type", "Unknown"),
            "compliance_status": "",
            "findings": [],
            "recommendations": []
        }
        
        # Create review prompt
        document_text = json.dumps(document, indent=2)
        
        # Get requirements for document type
        doc_type = document.get("type", "").lower()
        specific_requirements = requirements or self.legal_requirements.get(doc_type, [])
        requirements_text = json.dumps(specific_requirements, indent=2)
        
        review_prompt = f"""
        Review the following legal document:
        {document_text}
        
        Check compliance with these requirements:
        {requirements_text}
        
        Please provide:
        1. Overall compliance status
        2. Detailed findings
        3. Specific recommendations
        4. Risk assessment
        5. Required updates
        
        Format your response as JSON with the following structure:
        {{
            "compliance_status": "compliant|partially_compliant|non_compliant",
            "findings": [
                {{
                    "id": "F001",
                    "section": "Data Collection",
                    "requirement": "Data collection description",
                    "status": "compliant|partially_compliant|non_compliant",
                    "details": "The data collection section is incomplete...",
                    "risk_level": "high|medium|low"
                }}
            ],
            "recommendations": [
                {{
                    "id": "R001",
                    "finding_id": "F001",
                    "description": "Add a detailed description of all data types collected",
                    "priority": "high|medium|low",
                    "suggested_text": "We collect the following types of data: ..."
                }}
            ],
            "risk_assessment": {{
                "overall_risk": "high|medium|low",
                "critical_issues": 2,
                "potential_legal_exposure": "Significant exposure to regulatory penalties..."
            }},
            "required_updates": [
                {{
                    "section": "Data Collection",
                    "current_text": "We collect user data.",
                    "suggested_text": "We collect the following types of personal data: name, email, IP address, and usage analytics."
                }}
            ]
        }}
        """
        
        # Generate review using LLM
        review_result = await self.llm.process({"prompt": review_prompt})
        
        # Parse response
        if isinstance(review_result, dict) and "output" in review_result:
            try:
                parsed_result = json.loads(review_result["output"])
                review["compliance_status"] = parsed_result.get("compliance_status", "")
                review["findings"] = parsed_result.get("findings", [])
                review["recommendations"] = parsed_result.get("recommendations", [])
                review["risk_assessment"] = parsed_result.get("risk_assessment", {})
                review["required_updates"] = parsed_result.get("required_updates", [])
            except json.JSONDecodeError:
                logging.error("Failed to parse document review result")
                review["error"] = "Failed to parse result"
        
        return review
    
    async def draft_legal_document(self, 
                               document_type: str, 
                               requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Draft a legal document.
        
        Args:
            document_type: Type of document to draft
            requirements: Document requirements
            
        Returns:
            Drafted document
        """
        document = {
            "name": f"{document_type.title()} - {datetime.now().strftime('%Y-%m-%d')}",
            "type": document_type,
            "content": "",
            "sections": []
        }
        
        # Get template if available
        template = self.document_templates.get(document_type, "")
        
        # Get requirements for document type
        specific_requirements = self.legal_requirements.get(document_type, [])
        
        # Create draft prompt
        requirements_text = json.dumps(requirements, indent=2)
        specific_requirements_text = json.dumps(specific_requirements, indent=2)
        
        draft_prompt = f"""
        Draft a {document_type} document based on these requirements:
        {requirements_text}
        
        This document must include:
        {specific_requirements_text}
        
        Template to follow (if available):
        {template}
        
        Please provide:
        1. Complete document content
        2. Document structured in sections
        3. Any required legal disclaimers
        4. Variables/placeholders clearly marked
        5. Comments on customization areas
        
        Format your response as JSON with the following structure:
        {{
            "content": "Full document text with all sections...",
            "sections": [
                {{
                    "title": "Introduction",
                    "content": "This Agreement is entered into between...",
                    "requirements_addressed": ["Parties identification"]
                }}
            ],
            "customization_notes": [
                {{
                    "section": "Introduction",
                    "note": "Company name and address should be updated"
                }}
            ],
            "legal_disclaimers": [
                {{
                    "title": "Limitation of Liability",
                    "content": "To the maximum extent permitted by law..."
                }}
            ],
            "variables": [
                {{
                    "name": "COMPANY_NAME",
                    "description": "Full legal name of the company",
                    "sample_value": "Acme Corporation"
                }}
            ]
        }}
        """
        
        # Generate draft using LLM
        draft_result = await self.llm.process({"prompt": draft_prompt})
        
        if isinstance(draft_result, dict) and "output" in draft_result:
            try:
                parsed_result = json.loads(draft_result["output"])
                document["content"] = parsed_result.get("content", "")
                document["sections"] = parsed_result.get("sections", [])
                document["customization_notes"] = parsed_result.get("customization_notes", [])
                document["legal_disclaimers"] = parsed_result.get("legal_disclaimers", [])
                document["variables"] = parsed_result.get("variables", [])
            except json.JSONDecodeError:
                logging.error("Failed to parse document draft result")
                document["error"] = "Failed to parse result"
                document["content"] = draft_result.get("output", "")
        
        return document
    
    async def check_compliance(self, 
                          document: Dict[str, Any], 
                          regulations: List[str]) -> Dict[str, Any]:
        """Check document compliance with regulations.
        
        Args:
            document: Document to check
            regulations: List of regulations to check against
            
        Returns:
            Compliance check results
        """
        document_text = json.dumps(document, indent=2)
        regulations_text = json.dumps(regulations, indent=2)
        
        compliance_prompt = f"""
        Check compliance of the following document against these regulations:
        {regulations_text}
        
        Document:
        {document_text}
        
        Please provide:
        1. Compliance status for each regulation
        2. Identified issues
        3. Recommended remediation
        4. Overall compliance assessment
        5. Risk exposure analysis
        
        Format your response as JSON with comprehensive compliance analysis.
        """
        
        # Generate compliance check using LLM
        compliance_result = await self.llm.process({"prompt": compliance_prompt})
        
        if isinstance(compliance_result, dict) and "output" in compliance_result:
            try:
                return json.loads(compliance_result["output"])
            except json.JSONDecodeError:
                return {"raw_check": compliance_result["output"]}
        
        return {"error": "Failed to generate compliance check"}
    
    async def create_amendment(self, 
                          original_document: Dict[str, Any], 
                          changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create an amendment to a legal document.
        
        Args:
            original_document: Original document
            changes: List of changes to make
            
        Returns:
            Amendment document
        """
        document_text = json.dumps(original_document, indent=2)
        changes_text = json.dumps(changes, indent=2)
        
        amendment_prompt = f"""
        Create an amendment for the following document based on these changes:
        
        Original Document:
        {document_text}
        
        Requested Changes:
        {changes_text}
        
        Please provide:
        1. Complete amendment document
        2. Reference to original agreement
        3. Effective date clause
        4. Clear description of modifications
        5. Signatures block
        
        Format your response as JSON with a complete amendment document.
        """
        
        # Generate amendment using LLM
        amendment_result = await self.llm.process({"prompt": amendment_prompt})
        
        if isinstance(amendment_result, dict) and "output" in amendment_result:
            try:
                return json.loads(amendment_result["output"])
            except json.JSONDecodeError:
                return {
                    "content": amendment_result["output"],
                    "document_type": "amendment"
                }
        
        return {"error": "Failed to generate amendment"}
    
    async def generate_approval_workflow(self, 
                                    document: Dict[str, Any]) -> Dict[str, Any]:
        """Generate approval workflow for a document.
        
        Args:
            document: Document requiring approval
            
        Returns:
            Approval workflow
        """
        document_text = json.dumps(document, indent=2)
        
        workflow_prompt = f"""
        Generate an approval workflow for the following legal document:
        {document_text}
        
        Please include:
        1. Required approvers
        2. Approval sequence
        3. Review criteria for each approver
        4. Escalation procedures
        5. Timeline recommendations
        
        Format your response as JSON with a comprehensive approval workflow.
        """
        
        # Generate workflow using LLM
        workflow_result = await self.llm.process({"prompt": workflow_prompt})
        
        if isinstance(workflow_result, dict) and "output" in workflow_result:
            try:
                return json.loads(workflow_result["output"])
            except json.JSONDecodeError:
                return {"raw_workflow": workflow_result["output"]}
        
        return {"error": "Failed to generate approval workflow"}
    
    async def run_playbook_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific playbook step.
        
        Args:
            step: Playbook step definition
            context: Execution context
            
        Returns:
            Step execution results
        """
        action = step.get("action", "")
        
        if action == "review_legal_document":
            document = step.get("document", context.get("document", {}))
            requirements = step.get("requirements", None)
            
            review = await self.review_legal_document(document, requirements)
            return {"document_review": review}
            
        elif action == "draft_legal_document":
            document_type = step.get("document_type", context.get("document_type", ""))
            requirements = step.get("requirements", context.get("requirements", {}))
            
            document = await self.draft_legal_document(document_type, requirements)
            return {"drafted_document": document}
            
        elif action == "check_compliance":
            document = step.get("document", context.get("document", {}))
            regulations = step.get("regulations", context.get("regulations", []))
            
            compliance = await self.check_compliance(document, regulations)
            return {"compliance_check": compliance}
            
        elif action == "create_amendment":
            original_document = step.get("original_document", context.get("original_document", {}))
            changes = step.get("changes", context.get("changes", []))
            
            amendment = await self.create_amendment(original_document, changes)
            return {"amendment": amendment}
            
        elif action == "generate_approval_workflow":
            document = step.get("document", context.get("document", {}))
            
            workflow = await self.generate_approval_workflow(document)
            return {"approval_workflow": workflow}
            
        else:
            return await super().run_playbook_step(step, context)
    
    async def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the ParaLegal agent with the specified playbook.
        
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
        
        # Add final legal documents
        if "document_review" in context:
            results["document_review"] = context["document_review"]
            
        if "drafted_document" in context:
            results["drafted_document"] = context["drafted_document"]
            
        if "compliance_check" in context:
            results["compliance_check"] = context["compliance_check"]
            
        if "amendment" in context:
            results["amendment"] = context["amendment"]
            
        if "approval_workflow" in context:
            results["approval_workflow"] = context["approval_workflow"]
            
        return results