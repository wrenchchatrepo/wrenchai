# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Any, Optional, Union
import yaml
import logging
import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta

from .journey_agent import JourneyAgent

class Comptroller(JourneyAgent):
    """
    Financial control specialist for system costs.
    
    Core responsibilities:
    1. Track system costs
    2. Optimize resource usage
    3. Generate cost reports
    4. Forecast expenses
    5. Recommend cost savings
    """
    
    def __init__(self, 
                name: str, 
                llm: Any, 
                tools: List[str], 
                playbook_path: str,
                budget: Optional[Dict[str, Any]] = None,
                cost_center_mappings: Optional[Dict[str, str]] = None):
        """Initialize the Comptroller agent.
        
        Args:
            name: Agent name
            llm: Language model to use
            tools: List of tool names
            playbook_path: Path to the playbook file
            budget: Optional budget information
            cost_center_mappings: Optional cost center mappings
        """
        super().__init__(name, llm, tools, playbook_path)
        
        self.budget = budget or {
            "total": 100000,
            "allocated": {
                "compute": 40000,
                "storage": 20000,
                "network": 10000,
                "licenses": 15000,
                "support": 10000,
                "misc": 5000
            },
            "period": "annual"
        }
        
        self.cost_center_mappings = cost_center_mappings or {}
        
        # Check tools availability
        required_tools = ["cost_tool", "reporting_tool"]
        for tool in required_tools:
            if tool not in tools:
                logging.warning(f"Comptroller agent should have '{tool}' tool")
                
    async def analyze_cost_data(self, 
                             usage_data: Dict[str, Any], 
                             period: str = "monthly") -> Dict[str, Any]:
        """Analyze cost and usage data.
        
        Args:
            usage_data: Resource usage data
            period: Analysis period (daily, weekly, monthly, quarterly, annual)
            
        Returns:
            Cost analysis
        """
        analysis = {
            "timestamp": asyncio.get_event_loop().time(),
            "period": period,
            "total_cost": 0,
            "breakdown": {},
            "trends": [],
            "anomalies": []
        }
        
        # Create analysis prompt
        usage_text = json.dumps(usage_data, indent=2)
        budget_text = json.dumps(self.budget, indent=2)
        
        analysis_prompt = f"""
        Analyze the following {period} cost and usage data:
        {usage_text}
        
        Budget information:
        {budget_text}
        
        Please provide:
        1. Total cost calculation
        2. Cost breakdown by service/resource
        3. Cost trends (increasing, decreasing, stable)
        4. Anomalies or unexpected costs
        5. Budget variance analysis
        
        Format your response as JSON with the following structure:
        {{
            "total_cost": 8245.67,
            "breakdown": {{
                "compute": 3621.45,
                "storage": 1825.30,
                "network": 952.10,
                "licenses": 1250.00,
                "support": 416.67,
                "misc": 180.15
            }},
            "trends": [
                {{
                    "category": "compute",
                    "trend": "increasing",
                    "rate": "+5.2% month-over-month",
                    "details": "Increase primarily due to new development environment"
                }}
            ],
            "anomalies": [
                {{
                    "category": "storage",
                    "description": "Unexpected 200GB storage increase on Oct 15",
                    "estimated_cost": 35.40,
                    "recommendation": "Investigate large storage increase, may be log files"
                }}
            ],
            "budget_variance": {{
                "total": {{
                    "budget": 8333.33,
                    "actual": 8245.67,
                    "variance": -87.66,
                    "variance_percent": -1.05,
                    "status": "under budget"
                }},
                "categories": [
                    {{
                        "category": "compute",
                        "budget": 3333.33,
                        "actual": 3621.45,
                        "variance": 288.12,
                        "variance_percent": 8.64,
                        "status": "over budget"
                    }}
                ]
            }}
        }}
        """
        
        # Generate analysis using LLM
        analysis_result = await self.llm.process({"prompt": analysis_prompt})
        
        # Parse response
        if isinstance(analysis_result, dict) and "output" in analysis_result:
            try:
                parsed_result = json.loads(analysis_result["output"])
                analysis["total_cost"] = parsed_result.get("total_cost", 0)
                analysis["breakdown"] = parsed_result.get("breakdown", {})
                analysis["trends"] = parsed_result.get("trends", [])
                analysis["anomalies"] = parsed_result.get("anomalies", [])
                analysis["budget_variance"] = parsed_result.get("budget_variance", {})
            except json.JSONDecodeError:
                logging.error("Failed to parse cost analysis result")
                analysis["error"] = "Failed to parse result"
        
        return analysis
    
    async def generate_cost_report(self, 
                               analysis: Dict[str, Any], 
                               report_type: str = "executive") -> Dict[str, Any]:
        """Generate cost report.
        
        Args:
            analysis: Cost analysis data
            report_type: Report type (executive, detailed, technical)
            
        Returns:
            Cost report
        """
        analysis_text = json.dumps(analysis, indent=2)
        
        report_prompt = f"""
        Generate a {report_type} cost report based on the following analysis:
        {analysis_text}
        
        Budget information:
        {json.dumps(self.budget, indent=2)}
        
        Please include:
        1. Executive summary
        2. Cost breakdown
        3. Budget variance
        4. Key trends
        5. Recommendations
        
        Format your response as JSON with a complete {report_type} report.
        """
        
        # Generate report using LLM
        report_result = await self.llm.process({"prompt": report_prompt})
        
        if isinstance(report_result, dict) and "output" in report_result:
            try:
                return json.loads(report_result["output"])
            except json.JSONDecodeError:
                return {
                    "content": report_result["output"],
                    "report_type": report_type
                }
        
        return {"error": "Failed to generate cost report"}
    
    async def forecast_costs(self, 
                        historical_data: Dict[str, Any], 
                        forecast_period: str = "quarterly") -> Dict[str, Any]:
        """Forecast future costs.
        
        Args:
            historical_data: Historical cost data
            forecast_period: Forecast period (monthly, quarterly, annual)
            
        Returns:
            Cost forecast
        """
        historical_text = json.dumps(historical_data, indent=2)
        
        forecast_prompt = f"""
        Forecast {forecast_period} costs based on the following historical data:
        {historical_text}
        
        Please include:
        1. Total cost forecast
        2. Category breakdowns
        3. Growth trends
        4. Confidence intervals
        5. Assumptions made
        
        Format your response as JSON with detailed cost forecasts.
        """
        
        # Generate forecast using LLM
        forecast_result = await self.llm.process({"prompt": forecast_prompt})
        
        if isinstance(forecast_result, dict) and "output" in forecast_result:
            try:
                return json.loads(forecast_result["output"])
            except json.JSONDecodeError:
                return {"raw_forecast": forecast_result["output"]}
        
        return {"error": "Failed to generate cost forecast"}
    
    async def recommend_optimizations(self, 
                                  analysis: Dict[str, Any], 
                                  target_savings: Optional[float] = None) -> Dict[str, Any]:
        """Recommend cost optimizations.
        
        Args:
            analysis: Cost analysis data
            target_savings: Optional target savings amount
            
        Returns:
            Optimization recommendations
        """
        analysis_text = json.dumps(analysis, indent=2)
        target = f"{target_savings}" if target_savings else "maximum possible"
        
        optimization_prompt = f"""
        Recommend cost optimizations to achieve {target} savings based on:
        {analysis_text}
        
        Please include:
        1. Prioritized optimization recommendations
        2. Estimated savings for each recommendation
        3. Implementation difficulty
        4. Risk assessment
        5. Implementation timeline
        
        Format your response as JSON with detailed optimization recommendations.
        """
        
        # Generate optimizations using LLM
        optimization_result = await self.llm.process({"prompt": optimization_prompt})
        
        if isinstance(optimization_result, dict) and "output" in optimization_result:
            try:
                return json.loads(optimization_result["output"])
            except json.JSONDecodeError:
                return {"raw_recommendations": optimization_result["output"]}
        
        return {"error": "Failed to generate optimization recommendations"}
    
    async def run_playbook_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific playbook step.
        
        Args:
            step: Playbook step definition
            context: Execution context
            
        Returns:
            Step execution results
        """
        action = step.get("action", "")
        
        if action == "analyze_costs":
            usage_data = step.get("usage_data", context.get("usage_data", {}))
            period = step.get("period", "monthly")
            
            analysis = await self.analyze_cost_data(usage_data, period)
            return {"cost_analysis": analysis}
            
        elif action == "generate_report":
            analysis = step.get("analysis", context.get("cost_analysis", {}))
            report_type = step.get("report_type", "executive")
            
            report = await self.generate_cost_report(analysis, report_type)
            return {"cost_report": report}
            
        elif action == "forecast_costs":
            historical_data = step.get("historical_data", context.get("historical_data", {}))
            forecast_period = step.get("forecast_period", "quarterly")
            
            forecast = await self.forecast_costs(historical_data, forecast_period)
            return {"cost_forecast": forecast}
            
        elif action == "recommend_optimizations":
            analysis = step.get("analysis", context.get("cost_analysis", {}))
            target_savings = step.get("target_savings", None)
            
            optimizations = await self.recommend_optimizations(analysis, target_savings)
            return {"optimizations": optimizations}
            
        else:
            return await super().run_playbook_step(step, context)
    
    async def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the Comptroller agent with the specified playbook.
        
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
        
        # Add final cost documents
        if "cost_analysis" in context:
            results["cost_analysis"] = context["cost_analysis"]
            
        if "cost_report" in context:
            results["cost_report"] = context["cost_report"]
            
        if "cost_forecast" in context:
            results["cost_forecast"] = context["cost_forecast"]
            
        if "optimizations" in context:
            results["optimizations"] = context["optimizations"]
            
        return results