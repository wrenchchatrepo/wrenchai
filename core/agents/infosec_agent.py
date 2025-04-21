# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Any, Optional, Union
import yaml
import logging
import asyncio
import json
from pathlib import Path

from .journey_agent import JourneyAgent

class InfoSec(JourneyAgent):
    """
    Information security specialist focused on system security.
    
    Core responsibilities:
    1. Implement security measures
    2. Conduct security audits
    3. Monitor security threats
    4. Manage incident response
    5. Ensure compliance
    """
    
    def __init__(self, 
                name: str, 
                llm: Any, 
                tools: List[str], 
                playbook_path: str,
                security_standards: Optional[List[str]] = None,
                risk_thresholds: Optional[Dict[str, Any]] = None):
        """Initialize the InfoSec agent.
        
        Args:
            name: Agent name
            llm: Language model to use
            tools: List of tool names
            playbook_path: Path to the playbook file
            security_standards: Optional list of security standards to enforce
            risk_thresholds: Optional risk thresholds for different threat types
        """
        super().__init__(name, llm, tools, playbook_path)
        
        self.security_standards = security_standards or [
            "NIST 800-53",
            "CIS Controls",
            "OWASP Top 10",
            "ISO 27001",
            "SOC 2"
        ]
        
        self.risk_thresholds = risk_thresholds or {
            "critical": 80,
            "high": 60,
            "medium": 40,
            "low": 20
        }
        
        # Check tools availability
        required_tools = ["security_tool", "monitoring_tool"]
        for tool in required_tools:
            if tool not in tools:
                logging.warning(f"InfoSec agent should have '{tool}' tool")
                
    async def conduct_security_audit(self, 
                                  system: Dict[str, Any], 
                                  standards: Optional[List[str]] = None) -> Dict[str, Any]:
        """Conduct a security audit on a system.
        
        Args:
            system: System information
            standards: Optional list of security standards to audit against
            
        Returns:
            Security audit results
        """
        audit = {
            "timestamp": asyncio.get_event_loop().time(),
            "standards": standards or self.security_standards,
            "findings": [],
            "risk_score": 0,
            "recommendations": []
        }
        
        # Create audit prompt
        system_text = json.dumps(system, indent=2)
        standards_text = ", ".join(standards or self.security_standards)
        
        audit_prompt = f"""
        Conduct a comprehensive security audit on the following system:
        {system_text}
        
        Security standards to audit against:
        {standards_text}
        
        Please provide:
        1. Security findings with severity ratings
        2. Overall risk score (0-100)
        3. Detailed recommendations
        4. Compliance status for each standard
        
        Format your response as JSON with the following structure:
        {{
            "findings": [
                {{
                    "id": "SEC-001",
                    "title": "Weak password policy",
                    "description": "Password policy does not enforce complexity requirements",
                    "severity": "high",
                    "standard_reference": "NIST 800-53 IA-5",
                    "affected_components": ["authentication-service", "user-management"]
                }}
            ],
            "risk_score": 65,
            "recommendations": [
                {{
                    "id": "REC-001",
                    "title": "Strengthen password policy",
                    "description": "Update password policy to require minimum 12 characters with complexity",
                    "priority": "high",
                    "effort": "medium",
                    "related_findings": ["SEC-001"]
                }}
            ],
            "compliance": [
                {{
                    "standard": "NIST 800-53",
                    "status": "partial",
                    "compliant_controls": 76,
                    "non_compliant_controls": 24,
                    "not_applicable_controls": 12
                }}
            ]
        }}
        """
        
        # Generate audit using LLM
        audit_result = await self.llm.process({"prompt": audit_prompt})
        
        # Parse response
        if isinstance(audit_result, dict) and "output" in audit_result:
            try:
                parsed_result = json.loads(audit_result["output"])
                audit["findings"] = parsed_result.get("findings", [])
                audit["risk_score"] = parsed_result.get("risk_score", 0)
                audit["recommendations"] = parsed_result.get("recommendations", [])
                audit["compliance"] = parsed_result.get("compliance", [])
            except json.JSONDecodeError:
                logging.error("Failed to parse audit result")
                audit["error"] = "Failed to parse result"
        
        return audit
    
    async def develop_security_controls(self, 
                                     system: Dict[str, Any], 
                                     audit_results: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Develop security controls for a system.
        
        Args:
            system: System information
            audit_results: Optional audit results to base controls on
            
        Returns:
            Security controls
        """
        system_text = json.dumps(system, indent=2)
        audit_text = json.dumps(audit_results, indent=2) if audit_results else "No previous audit results"
        
        controls_prompt = f"""
        Develop comprehensive security controls for the following system:
        {system_text}
        
        Previous audit results:
        {audit_text}
        
        Security standards:
        {", ".join(self.security_standards)}
        
        Please include:
        1. Identity and access management controls
        2. Data protection controls
        3. Network security controls
        4. Application security controls
        5. Monitoring and incident response controls
        
        Format your response as JSON with detailed security controls.
        """
        
        # Generate security controls using LLM
        controls_result = await self.llm.process({"prompt": controls_prompt})
        
        if isinstance(controls_result, dict) and "output" in controls_result:
            try:
                return json.loads(controls_result["output"])
            except json.JSONDecodeError:
                return {"raw_controls": controls_result["output"]}
        
        return {"error": "Failed to generate security controls"}
    
    async def create_incident_response_plan(self, 
                                        system: Dict[str, Any]) -> Dict[str, Any]:
        """Create an incident response plan.
        
        Args:
            system: System information
            
        Returns:
            Incident response plan
        """
        system_text = json.dumps(system, indent=2)
        
        plan_prompt = f"""
        Create a comprehensive incident response plan for the following system:
        {system_text}
        
        Please include:
        1. Incident classification criteria
        2. Response team roles and responsibilities
        3. Detection procedures
        4. Containment strategies
        5. Eradication and recovery processes
        6. Post-incident analysis
        
        Format your response as JSON with a detailed incident response plan.
        """
        
        # Generate incident response plan using LLM
        plan_result = await self.llm.process({"prompt": plan_prompt})
        
        if isinstance(plan_result, dict) and "output" in plan_result:
            try:
                return json.loads(plan_result["output"])
            except json.JSONDecodeError:
                return {"raw_plan": plan_result["output"]}
        
        return {"error": "Failed to generate incident response plan"}
    
    async def analyze_security_threat(self, 
                                   threat: Dict[str, Any], 
                                   system: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a security threat.
        
        Args:
            threat: Threat information
            system: System information
            
        Returns:
            Threat analysis
        """
        threat_text = json.dumps(threat, indent=2)
        system_text = json.dumps(system, indent=2)
        
        analysis_prompt = f"""
        Analyze the following security threat for the system:
        
        Threat:
        {threat_text}
        
        System:
        {system_text}
        
        Please provide:
        1. Threat assessment
        2. Potential impact
        3. Risk score
        4. Recommended mitigations
        5. Detection strategies
        
        Format your response as JSON with comprehensive threat analysis.
        """
        
        # Generate threat analysis using LLM
        analysis_result = await self.llm.process({"prompt": analysis_prompt})
        
        if isinstance(analysis_result, dict) and "output" in analysis_result:
            try:
                return json.loads(analysis_result["output"])
            except json.JSONDecodeError:
                return {"raw_analysis": analysis_result["output"]}
        
        return {"error": "Failed to generate threat analysis"}
    
    async def generate_compliance_report(self, 
                                     system: Dict[str, Any], 
                                     standards: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate a compliance report.
        
        Args:
            system: System information
            standards: Optional list of standards to report on
            
        Returns:
            Compliance report
        """
        system_text = json.dumps(system, indent=2)
        standards_text = ", ".join(standards or self.security_standards)
        
        report_prompt = f"""
        Generate a compliance report for the following system against these standards:
        {standards_text}
        
        System:
        {system_text}
        
        Please include:
        1. Compliance summary
        2. Detailed compliance status for each standard
        3. Gap analysis
        4. Remediation plan
        5. Timeline recommendations
        
        Format your response as JSON with a comprehensive compliance report.
        """
        
        # Generate compliance report using LLM
        report_result = await self.llm.process({"prompt": report_prompt})
        
        if isinstance(report_result, dict) and "output" in report_result:
            try:
                return json.loads(report_result["output"])
            except json.JSONDecodeError:
                return {"raw_report": report_result["output"]}
        
        return {"error": "Failed to generate compliance report"}
    
    async def run_playbook_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific playbook step.
        
        Args:
            step: Playbook step definition
            context: Execution context
            
        Returns:
            Step execution results
        """
        action = step.get("action", "")
        
        if action == "conduct_security_audit":
            system = step.get("system", context.get("system", {}))
            standards = step.get("standards", self.security_standards)
            
            audit = await self.conduct_security_audit(system, standards)
            return {"security_audit": audit}
            
        elif action == "develop_security_controls":
            system = step.get("system", context.get("system", {}))
            audit_results = step.get("audit_results", context.get("security_audit", None))
            
            controls = await self.develop_security_controls(system, audit_results)
            return {"security_controls": controls}
            
        elif action == "create_incident_response_plan":
            system = step.get("system", context.get("system", {}))
            
            plan = await self.create_incident_response_plan(system)
            return {"incident_response_plan": plan}
            
        elif action == "analyze_security_threat":
            threat = step.get("threat", context.get("threat", {}))
            system = step.get("system", context.get("system", {}))
            
            analysis = await self.analyze_security_threat(threat, system)
            return {"threat_analysis": analysis}
            
        elif action == "generate_compliance_report":
            system = step.get("system", context.get("system", {}))
            standards = step.get("standards", self.security_standards)
            
            report = await self.generate_compliance_report(system, standards)
            return {"compliance_report": report}
            
        else:
            return await super().run_playbook_step(step, context)
    
    async def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the InfoSec agent with the specified playbook.
        
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
        
        # Add final security documents
        if "security_audit" in context:
            results["security_audit"] = context["security_audit"]
            
        if "security_controls" in context:
            results["security_controls"] = context["security_controls"]
            
        if "incident_response_plan" in context:
            results["incident_response_plan"] = context["incident_response_plan"]
            
        if "threat_analysis" in context:
            results["threat_analysis"] = context["threat_analysis"]
            
        if "compliance_report" in context:
            results["compliance_report"] = context["compliance_report"]
            
        return results