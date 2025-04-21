# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Any, Optional, Union
import yaml
import logging
import asyncio
import json
from pathlib import Path

from .journey_agent import JourneyAgent

class GCPArchitect(JourneyAgent):
    """
    Google Cloud Platform architecture specialist.
    
    Core responsibilities:
    1. Design cloud infrastructure
    2. Optimize resource utilization
    3. Implement security best practices
    4. Manage cloud costs
    5. Ensure scalability
    """
    
    def __init__(self, 
                name: str, 
                llm: Any, 
                tools: List[str], 
                playbook_path: str,
                project_config: Optional[Dict[str, Any]] = None,
                security_standards: Optional[List[str]] = None):
        """Initialize the GCPArchitect agent.
        
        Args:
            name: Agent name
            llm: Language model to use
            tools: List of tool names
            playbook_path: Path to the playbook file
            project_config: Optional GCP project configuration
            security_standards: Optional security standards to follow
        """
        super().__init__(name, llm, tools, playbook_path)
        
        self.project_config = project_config or {}
        self.security_standards = security_standards or [
            "CIS Google Cloud Computing Foundations Benchmark",
            "NIST 800-53",
            "ISO 27001"
        ]
        
        # Check tools availability
        required_tools = ["gcp_tool"]
        for tool in required_tools:
            if tool not in tools:
                logging.warning(f"GCPArchitect agent should have '{tool}' tool")
                
    async def design_architecture(self, 
                               requirements: Dict[str, Any], 
                               deployment_type: str = "production") -> Dict[str, Any]:
        """Design GCP architecture based on requirements.
        
        Args:
            requirements: Architecture requirements
            deployment_type: Deployment type (production, staging, development)
            
        Returns:
            Architecture design
        """
        architecture = {
            "services": [],
            "network": {},
            "security": {},
            "estimated_costs": {},
            "diagrams": []
        }
        
        # Create architecture prompt
        arch_prompt = f"""
        Design a Google Cloud Platform architecture for {deployment_type} environment based on the following requirements:
        {json.dumps(requirements, indent=2)}
        
        Project configuration:
        {json.dumps(self.project_config, indent=2)}
        
        Security standards:
        {', '.join(self.security_standards)}
        
        Please provide:
        1. GCP services to use with configuration details
        2. Network architecture
        3. Security controls
        4. Estimated costs
        5. Architecture diagrams (descriptive text)
        
        Format your response as JSON with the following structure:
        {{
            "services": [
                {{
                    "name": "Google Kubernetes Engine",
                    "purpose": "Container orchestration",
                    "configuration": {{
                        "version": "1.24",
                        "node_type": "e2-standard-4",
                        "autoscaling": true,
                        "multi_zone": true
                    }}
                }}
            ],
            "network": {{
                "vpc_design": "Hub and spoke with shared VPC",
                "subnets": ["10.0.0.0/24", "10.0.1.0/24"],
                "firewall_rules": ["Allow 443 from Internet", "Deny all other inbound"]
            }},
            "security": {{
                "iam_policies": ["Least privilege access", "Service accounts for each component"],
                "data_protection": ["Cloud KMS for encryption", "Secret Manager for secrets"],
                "compliance_controls": ["Audit logging enabled", "VPC Service Controls"]
            }},
            "estimated_costs": {{
                "monthly": 4500,
                "breakdown": [
                    {{
                        "service": "GKE",
                        "cost": 2000
                    }}
                ]
            }},
            "diagrams": [
                {{
                    "title": "High-level Architecture",
                    "description": "Detailed text description of the architecture diagram..."
                }}
            ]
        }}
        """
        
        # Generate architecture using LLM
        arch_result = await self.llm.process({"prompt": arch_prompt})
        
        # Parse response
        if isinstance(arch_result, dict) and "output" in arch_result:
            try:
                parsed_result = json.loads(arch_result["output"])
                architecture["services"] = parsed_result.get("services", [])
                architecture["network"] = parsed_result.get("network", {})
                architecture["security"] = parsed_result.get("security", {})
                architecture["estimated_costs"] = parsed_result.get("estimated_costs", {})
                architecture["diagrams"] = parsed_result.get("diagrams", [])
            except json.JSONDecodeError:
                logging.error("Failed to parse architecture result")
                architecture["error"] = "Failed to parse result"
        
        return architecture
    
    async def create_terraform_config(self, architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Create Terraform configuration for GCP architecture.
        
        Args:
            architecture: Architecture design
            
        Returns:
            Terraform configuration
        """
        arch_text = json.dumps(architecture, indent=2)
        
        terraform_prompt = f"""
        Create Terraform configuration for the following GCP architecture:
        {arch_text}
        
        Please provide:
        1. Terraform module structure
        2. Main configuration files
        3. Variable definitions
        4. Output values
        5. Required providers
        
        Format your response as JSON with terraform file contents.
        """
        
        # Generate terraform config using LLM
        terraform_result = await self.llm.process({"prompt": terraform_prompt})
        
        if isinstance(terraform_result, dict) and "output" in terraform_result:
            try:
                return json.loads(terraform_result["output"])
            except json.JSONDecodeError:
                return {"raw_config": terraform_result["output"]}
        
        return {"error": "Failed to generate Terraform configuration"}
    
    async def create_security_controls(self, architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Create security controls for GCP architecture.
        
        Args:
            architecture: Architecture design
            
        Returns:
            Security controls configuration
        """
        arch_text = json.dumps(architecture, indent=2)
        
        security_prompt = f"""
        Create security controls for the following GCP architecture:
        {arch_text}
        
        Security standards:
        {', '.join(self.security_standards)}
        
        Please provide:
        1. IAM policies and roles
        2. VPC Service Controls
        3. Data security measures
        4. Monitoring and logging
        5. Compliance controls
        
        Format your response as JSON with security configuration details.
        """
        
        # Generate security controls using LLM
        security_result = await self.llm.process({"prompt": security_prompt})
        
        if isinstance(security_result, dict) and "output" in security_result:
            try:
                return json.loads(security_result["output"])
            except json.JSONDecodeError:
                return {"raw_controls": security_result["output"]}
        
        return {"error": "Failed to generate security controls"}
    
    async def optimize_costs(self, architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize costs for GCP architecture.
        
        Args:
            architecture: Architecture design
            
        Returns:
            Cost optimization recommendations
        """
        arch_text = json.dumps(architecture, indent=2)
        
        cost_prompt = f"""
        Provide cost optimization recommendations for the following GCP architecture:
        {arch_text}
        
        Please include:
        1. Service-specific optimizations
        2. Commitment discounts (CUDs)
        3. Rightsizing recommendations
        4. Auto-scaling strategies
        5. Storage tier optimization
        
        Format your response as JSON with detailed cost optimization strategies.
        """
        
        # Generate cost optimizations using LLM
        cost_result = await self.llm.process({"prompt": cost_prompt})
        
        if isinstance(cost_result, dict) and "output" in cost_result:
            try:
                return json.loads(cost_result["output"])
            except json.JSONDecodeError:
                return {"raw_recommendations": cost_result["output"]}
        
        return {"error": "Failed to generate cost optimizations"}
    
    async def run_playbook_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific playbook step.
        
        Args:
            step: Playbook step definition
            context: Execution context
            
        Returns:
            Step execution results
        """
        action = step.get("action", "")
        
        if action == "design_architecture":
            requirements = step.get("requirements", context.get("requirements", {}))
            deployment_type = step.get("deployment_type", "production")
            
            architecture = await self.design_architecture(requirements, deployment_type)
            return {"architecture": architecture}
            
        elif action == "create_terraform":
            architecture = step.get("architecture", context.get("architecture", {}))
            terraform = await self.create_terraform_config(architecture)
            return {"terraform": terraform}
            
        elif action == "create_security":
            architecture = step.get("architecture", context.get("architecture", {}))
            security = await self.create_security_controls(architecture)
            return {"security": security}
            
        elif action == "optimize_costs":
            architecture = step.get("architecture", context.get("architecture", {}))
            optimizations = await self.optimize_costs(architecture)
            return {"cost_optimizations": optimizations}
            
        else:
            return await super().run_playbook_step(step, context)
    
    async def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the GCPArchitect agent with the specified playbook.
        
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
        
        # Add final architecture, terraform, and security if available
        if "architecture" in context:
            results["architecture"] = context["architecture"]
            
        if "terraform" in context:
            results["terraform"] = context["terraform"]
            
        if "security" in context:
            results["security"] = context["security"]
            
        if "cost_optimizations" in context:
            results["cost_optimizations"] = context["cost_optimizations"]
            
        return results