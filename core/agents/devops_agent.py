# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Any, Optional, Union
import yaml
import logging
import asyncio
import json
from pathlib import Path

from .journey_agent import JourneyAgent

class DevOps(JourneyAgent):
    """
    DevOps specialist focused on system reliability and automation.
    
    Core responsibilities:
    1. Monitor system performance
    2. Implement automation solutions
    3. Manage deployment pipelines
    4. Handle incident response
    5. Optimize infrastructure
    """
    
    def __init__(self, 
                name: str, 
                llm: Any, 
                tools: List[str], 
                playbook_path: str,
                infrastructure: Optional[Dict[str, Any]] = None,
                monitoring_config: Optional[Dict[str, Any]] = None):
        """Initialize the DevOps agent.
        
        Args:
            name: Agent name
            llm: Language model to use
            tools: List of tool names
            playbook_path: Path to the playbook file
            infrastructure: Optional infrastructure configuration
            monitoring_config: Optional monitoring configuration
        """
        super().__init__(name, llm, tools, playbook_path)
        
        self.infrastructure = infrastructure or {}
        self.monitoring_config = monitoring_config or {
            "metrics": ["cpu", "memory", "disk", "network"],
            "log_retention_days": 30,
            "alert_thresholds": {
                "cpu": 80,
                "memory": 80,
                "disk": 85,
                "error_rate": 5
            }
        }
        
        # Check tools availability
        required_tools = ["code_execution", "cloud_tool"]
        for tool in required_tools:
            if tool not in tools:
                logging.warning(f"DevOps agent should have '{tool}' tool")
                
    async def create_infrastructure_as_code(self, 
                                         requirements: Dict[str, Any], 
                                         platform: str = "terraform", 
                                         cloud_provider: str = "aws") -> Dict[str, Any]:
        """Create infrastructure as code (IaC) configuration.
        
        Args:
            requirements: Infrastructure requirements
            platform: IaC platform (terraform, cloudformation, etc.)
            cloud_provider: Cloud provider (aws, gcp, azure)
            
        Returns:
            Infrastructure as code configuration
        """
        infrastructure = {
            "files": [],
            "documentation": "",
            "deployment_steps": []
        }
        
        # Create IaC prompt
        iac_prompt = f"""
        Create {platform} infrastructure as code configuration for {cloud_provider} based on the following requirements:
        {json.dumps(requirements, indent=2)}
        
        Please provide:
        1. Infrastructure code files
        2. Documentation
        3. Deployment steps
        
        Format your response as JSON with the following structure:
        {{
            "files": [
                {{
                    "filename": "main.tf",
                    "content": "terraform {{\\n  required_providers {{\\n    aws = {{\\n      source = \\"hashicorp/aws\\"\\n    }}\\n  }}\\n}}"
                }}
            ],
            "documentation": "# Infrastructure Documentation\\n...",
            "deployment_steps": [
                "Initialize Terraform: terraform init",
                "Plan deployment: terraform plan",
                "Apply changes: terraform apply"
            ]
        }}
        """
        
        # Generate IaC using LLM
        iac_result = await self.llm.process({"prompt": iac_prompt})
        
        # Parse response
        if isinstance(iac_result, dict) and "output" in iac_result:
            try:
                parsed_result = json.loads(iac_result["output"])
                infrastructure["files"] = parsed_result.get("files", [])
                infrastructure["documentation"] = parsed_result.get("documentation", "")
                infrastructure["deployment_steps"] = parsed_result.get("deployment_steps", [])
            except json.JSONDecodeError:
                logging.error("Failed to parse IaC result")
                infrastructure["error"] = "Failed to parse result"
        
        return infrastructure
    
    async def create_monitoring_setup(self, 
                                    services: List[Dict[str, Any]], 
                                    monitoring_tool: str = "prometheus") -> Dict[str, Any]:
        """Create monitoring configuration for services.
        
        Args:
            services: List of services to monitor
            monitoring_tool: Monitoring tool to use
            
        Returns:
            Monitoring setup configuration
        """
        services_text = json.dumps(services, indent=2)
        
        monitoring_prompt = f"""
        Create {monitoring_tool} monitoring configuration for the following services:
        {services_text}
        
        Monitoring requirements:
        {json.dumps(self.monitoring_config, indent=2)}
        
        Please provide:
        1. Monitoring configuration files
        2. Dashboard configurations
        3. Alert rules
        4. Installation/setup instructions
        
        Format your response as JSON with comprehensive monitoring setup.
        """
        
        # Generate monitoring config using LLM
        monitoring_result = await self.llm.process({"prompt": monitoring_prompt})
        
        if isinstance(monitoring_result, dict) and "output" in monitoring_result:
            try:
                return json.loads(monitoring_result["output"])
            except json.JSONDecodeError:
                return {"raw_config": monitoring_result["output"]}
        
        return {"error": "Failed to generate monitoring configuration"}
    
    async def create_ci_cd_pipeline(self, 
                                 repository: Dict[str, Any], 
                                 pipeline_tool: str = "github-actions") -> Dict[str, Any]:
        """Create CI/CD pipeline configuration.
        
        Args:
            repository: Repository information
            pipeline_tool: CI/CD tool to use
            
        Returns:
            CI/CD pipeline configuration
        """
        repo_text = json.dumps(repository, indent=2)
        
        pipeline_prompt = f"""
        Create {pipeline_tool} CI/CD pipeline configuration for the following repository:
        {repo_text}
        
        Please include:
        1. Build steps
        2. Test execution
        3. Code quality checks
        4. Deployment stages
        5. Approval processes (if needed)
        
        Format your response as JSON with pipeline configuration files and documentation.
        """
        
        # Generate pipeline config using LLM
        pipeline_result = await self.llm.process({"prompt": pipeline_prompt})
        
        if isinstance(pipeline_result, dict) and "output" in pipeline_result:
            try:
                return json.loads(pipeline_result["output"])
            except json.JSONDecodeError:
                return {"raw_config": pipeline_result["output"]}
        
        return {"error": "Failed to generate pipeline configuration"}
    
    async def create_incident_response_plan(self, 
                                         services: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create incident response plan for services.
        
        Args:
            services: List of services
            
        Returns:
            Incident response plan
        """
        services_text = json.dumps(services, indent=2)
        
        plan_prompt = f"""
        Create an incident response plan for the following services:
        {services_text}
        
        Please include:
        1. Severity levels and definitions
        2. Response procedures for each severity
        3. Escalation paths
        4. Communication templates
        5. Post-incident review process
        
        Format your response as JSON with a comprehensive incident response plan.
        """
        
        # Generate plan using LLM
        plan_result = await self.llm.process({"prompt": plan_prompt})
        
        if isinstance(plan_result, dict) and "output" in plan_result:
            try:
                return json.loads(plan_result["output"])
            except json.JSONDecodeError:
                return {"raw_plan": plan_result["output"]}
        
        return {"error": "Failed to generate incident response plan"}
    
    async def run_playbook_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific playbook step.
        
        Args:
            step: Playbook step definition
            context: Execution context
            
        Returns:
            Step execution results
        """
        action = step.get("action", "")
        
        if action == "create_infrastructure":
            requirements = step.get("requirements", context.get("requirements", {}))
            platform = step.get("platform", "terraform")
            cloud_provider = step.get("cloud_provider", "aws")
            
            infrastructure = await self.create_infrastructure_as_code(
                requirements, platform, cloud_provider
            )
            return {"infrastructure": infrastructure}
            
        elif action == "create_monitoring":
            services = step.get("services", context.get("services", []))
            monitoring_tool = step.get("monitoring_tool", "prometheus")
            
            monitoring = await self.create_monitoring_setup(services, monitoring_tool)
            return {"monitoring": monitoring}
            
        elif action == "create_pipeline":
            repository = step.get("repository", context.get("repository", {}))
            pipeline_tool = step.get("pipeline_tool", "github-actions")
            
            pipeline = await self.create_ci_cd_pipeline(repository, pipeline_tool)
            return {"pipeline": pipeline}
            
        elif action == "create_incident_plan":
            services = step.get("services", context.get("services", []))
            incident_plan = await self.create_incident_response_plan(services)
            return {"incident_plan": incident_plan}
            
        else:
            return await super().run_playbook_step(step, context)
    
    async def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the DevOps agent with the specified playbook.
        
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
        
        # Add final infrastructure, monitoring, and pipeline if available
        if "infrastructure" in context:
            results["infrastructure"] = context["infrastructure"]
            
        if "monitoring" in context:
            results["monitoring"] = context["monitoring"]
            
        if "pipeline" in context:
            results["pipeline"] = context["pipeline"]
            
        if "incident_plan" in context:
            results["incident_plan"] = context["incident_plan"]
            
        return results