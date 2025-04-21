# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Any, Optional, Union
import yaml
import logging
import asyncio
import json
from pathlib import Path

from .journey_agent import JourneyAgent

class DBA(JourneyAgent):
    """
    Database administration specialist.
    
    Core responsibilities:
    1. Manage database operations
    2. Optimize performance
    3. Ensure data integrity
    4. Handle backup/recovery
    5. Monitor database health
    """
    
    def __init__(self, 
                name: str, 
                llm: Any, 
                tools: List[str], 
                playbook_path: str,
                db_technologies: Optional[List[str]] = None,
                performance_targets: Optional[Dict[str, Any]] = None):
        """Initialize the DBA agent.
        
        Args:
            name: Agent name
            llm: Language model to use
            tools: List of tool names
            playbook_path: Path to the playbook file
            db_technologies: Optional list of database technologies to support
            performance_targets: Optional performance targets
        """
        super().__init__(name, llm, tools, playbook_path)
        
        self.db_technologies = db_technologies or [
            "PostgreSQL",
            "MySQL",
            "MongoDB",
            "SQLite",
            "Redis",
            "Elasticsearch"
        ]
        
        self.performance_targets = performance_targets or {
            "query_response_time": "< 100ms",
            "database_cpu_usage": "< 70%",
            "database_memory_usage": "< 80%",
            "connection_pool_usage": "< 80%",
            "index_hit_ratio": "> 95%"
        }
        
        # Check tools availability
        required_tools = ["database_tool", "monitoring_tool"]
        for tool in required_tools:
            if tool not in tools:
                logging.warning(f"DBA agent should have '{tool}' tool")
                
    async def design_database_schema(self, 
                                 requirements: Dict[str, Any], 
                                 db_type: str = "postgresql") -> Dict[str, Any]:
        """Design database schema.
        
        Args:
            requirements: Database requirements
            db_type: Database type
            
        Returns:
            Database schema design
        """
        schema = {
            "db_type": db_type,
            "entities": [],
            "relationships": [],
            "indexes": [],
            "constraints": [],
            "diagram": ""
        }
        
        # Create schema design prompt
        requirements_text = json.dumps(requirements, indent=2)
        
        schema_prompt = f"""
        Design a {db_type} database schema based on the following requirements:
        {requirements_text}
        
        Please provide:
        1. Entity definitions with attributes and data types
        2. Relationship definitions
        3. Index recommendations
        4. Constraint definitions
        5. Schema diagram (as text representation)
        
        Format your response as JSON with the following structure:
        {{
            "entities": [
                {{
                    "name": "users",
                    "description": "User accounts",
                    "attributes": [
                        {{
                            "name": "id",
                            "data_type": "SERIAL",
                            "description": "Unique identifier",
                            "is_primary_key": true,
                            "is_nullable": false
                        }},
                        {{
                            "name": "email",
                            "data_type": "VARCHAR(255)",
                            "description": "User email address",
                            "is_unique": true,
                            "is_nullable": false
                        }}
                    ]
                }}
            ],
            "relationships": [
                {{
                    "name": "user_orders",
                    "type": "one-to-many",
                    "source_entity": "users",
                    "target_entity": "orders",
                    "source_key": "id",
                    "target_key": "user_id"
                }}
            ],
            "indexes": [
                {{
                    "entity": "users",
                    "attributes": ["email"],
                    "type": "unique",
                    "name": "idx_users_email"
                }}
            ],
            "constraints": [
                {{
                    "entity": "orders",
                    "type": "check",
                    "name": "chk_order_amount_positive",
                    "definition": "amount > 0"
                }}
            ],
            "creation_sql": "CREATE TABLE users (\\n  id SERIAL PRIMARY KEY,\\n  email VARCHAR(255) NOT NULL UNIQUE\\n);",
            "diagram": "users 1--* orders\\norders *--* products"
        }}
        """
        
        # Generate schema using LLM
        schema_result = await self.llm.process({"prompt": schema_prompt})
        
        # Parse response
        if isinstance(schema_result, dict) and "output" in schema_result:
            try:
                parsed_result = json.loads(schema_result["output"])
                schema["entities"] = parsed_result.get("entities", [])
                schema["relationships"] = parsed_result.get("relationships", [])
                schema["indexes"] = parsed_result.get("indexes", [])
                schema["constraints"] = parsed_result.get("constraints", [])
                schema["creation_sql"] = parsed_result.get("creation_sql", "")
                schema["diagram"] = parsed_result.get("diagram", "")
            except json.JSONDecodeError:
                logging.error("Failed to parse schema result")
                schema["error"] = "Failed to parse result"
        
        return schema
    
    async def optimize_database_performance(self, 
                                       database_info: Dict[str, Any], 
                                       performance_issues: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Optimize database performance.
        
        Args:
            database_info: Database information
            performance_issues: Optional list of performance issues
            
        Returns:
            Performance optimization recommendations
        """
        database_text = json.dumps(database_info, indent=2)
        issues_text = json.dumps(performance_issues or [], indent=2)
        performance_targets_text = json.dumps(self.performance_targets, indent=2)
        
        optimization_prompt = f"""
        Recommend database performance optimizations for:
        {database_text}
        
        Known issues:
        {issues_text}
        
        Target performance metrics:
        {performance_targets_text}
        
        Please provide:
        1. Query optimization recommendations
        2. Index recommendations
        3. Configuration parameter adjustments
        4. Hardware scaling recommendations
        5. Caching strategies
        
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
    
    async def create_backup_strategy(self, 
                                 database_info: Dict[str, Any], 
                                 requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Create backup and recovery strategy.
        
        Args:
            database_info: Database information
            requirements: Backup requirements
            
        Returns:
            Backup strategy
        """
        database_text = json.dumps(database_info, indent=2)
        requirements_text = json.dumps(requirements, indent=2)
        
        backup_prompt = f"""
        Create a comprehensive backup and recovery strategy for:
        {database_text}
        
        Requirements:
        {requirements_text}
        
        Please include:
        1. Backup schedule and retention policy
        2. Backup types (full, incremental, differential)
        3. Recovery procedures for various scenarios
        4. Testing procedures
        5. Monitoring and alerting
        
        Format your response as JSON with a detailed backup strategy.
        """
        
        # Generate backup strategy using LLM
        backup_result = await self.llm.process({"prompt": backup_prompt})
        
        if isinstance(backup_result, dict) and "output" in backup_result:
            try:
                return json.loads(backup_result["output"])
            except json.JSONDecodeError:
                return {"raw_strategy": backup_result["output"]}
        
        return {"error": "Failed to generate backup strategy"}
    
    async def analyze_database_health(self, 
                                  metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze database health.
        
        Args:
            metrics: Database metrics
            
        Returns:
            Health analysis
        """
        metrics_text = json.dumps(metrics, indent=2)
        performance_targets_text = json.dumps(self.performance_targets, indent=2)
        
        health_prompt = f"""
        Analyze the following database metrics:
        {metrics_text}
        
        Target performance metrics:
        {performance_targets_text}
        
        Please provide:
        1. Overall health assessment
        2. Key metrics analysis
        3. Identified issues
        4. Recommendations
        5. Monitoring adjustments
        
        Format your response as JSON with comprehensive database health analysis.
        """
        
        # Generate health analysis using LLM
        health_result = await self.llm.process({"prompt": health_prompt})
        
        if isinstance(health_result, dict) and "output" in health_result:
            try:
                return json.loads(health_result["output"])
            except json.JSONDecodeError:
                return {"raw_analysis": health_result["output"]}
        
        return {"error": "Failed to generate health analysis"}
    
    async def create_migration_plan(self, 
                                source_db: Dict[str, Any], 
                                target_db: Dict[str, Any]) -> Dict[str, Any]:
        """Create database migration plan.
        
        Args:
            source_db: Source database information
            target_db: Target database information
            
        Returns:
            Migration plan
        """
        source_text = json.dumps(source_db, indent=2)
        target_text = json.dumps(target_db, indent=2)
        
        migration_prompt = f"""
        Create a comprehensive database migration plan from:
        {source_text}
        
        To:
        {target_text}
        
        Please include:
        1. Migration approach (big bang vs. phased)
        2. Schema conversion steps
        3. Data migration procedures
        4. Testing strategy
        5. Rollback procedures
        6. Cutover plan
        
        Format your response as JSON with a detailed migration plan.
        """
        
        # Generate migration plan using LLM
        migration_result = await self.llm.process({"prompt": migration_prompt})
        
        if isinstance(migration_result, dict) and "output" in migration_result:
            try:
                return json.loads(migration_result["output"])
            except json.JSONDecodeError:
                return {"raw_plan": migration_result["output"]}
        
        return {"error": "Failed to generate migration plan"}
    
    async def run_playbook_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific playbook step.
        
        Args:
            step: Playbook step definition
            context: Execution context
            
        Returns:
            Step execution results
        """
        action = step.get("action", "")
        
        if action == "design_database_schema":
            requirements = step.get("requirements", context.get("requirements", {}))
            db_type = step.get("db_type", "postgresql")
            
            schema = await self.design_database_schema(requirements, db_type)
            return {"database_schema": schema}
            
        elif action == "optimize_database":
            database_info = step.get("database_info", context.get("database_info", {}))
            performance_issues = step.get("performance_issues", context.get("performance_issues", []))
            
            optimizations = await self.optimize_database_performance(database_info, performance_issues)
            return {"optimization_recommendations": optimizations}
            
        elif action == "create_backup_strategy":
            database_info = step.get("database_info", context.get("database_info", {}))
            requirements = step.get("requirements", context.get("backup_requirements", {}))
            
            strategy = await self.create_backup_strategy(database_info, requirements)
            return {"backup_strategy": strategy}
            
        elif action == "analyze_database_health":
            metrics = step.get("metrics", context.get("database_metrics", {}))
            
            analysis = await self.analyze_database_health(metrics)
            return {"health_analysis": analysis}
            
        elif action == "create_migration_plan":
            source_db = step.get("source_db", context.get("source_db", {}))
            target_db = step.get("target_db", context.get("target_db", {}))
            
            plan = await self.create_migration_plan(source_db, target_db)
            return {"migration_plan": plan}
            
        else:
            return await super().run_playbook_step(step, context)
    
    async def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the DBA agent with the specified playbook.
        
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
        
        # Add final database artifacts
        if "database_schema" in context:
            results["database_schema"] = context["database_schema"]
            
        if "optimization_recommendations" in context:
            results["optimization_recommendations"] = context["optimization_recommendations"]
            
        if "backup_strategy" in context:
            results["backup_strategy"] = context["backup_strategy"]
            
        if "health_analysis" in context:
            results["health_analysis"] = context["health_analysis"]
            
        if "migration_plan" in context:
            results["migration_plan"] = context["migration_plan"]
            
        return results