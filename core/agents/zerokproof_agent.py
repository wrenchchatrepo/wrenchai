# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Any, Optional, Union
import yaml
import logging
import asyncio
import json
from pathlib import Path

from .journey_agent import JourneyAgent

class ZeroKProof(JourneyAgent):
    """
    Zero-knowledge proof specialist.
    
    Core responsibilities:
    1. Design ZK proof systems
    2. Implement proof protocols
    3. Optimize proof generation
    4. Ensure security properties
    5. Validate proof systems
    """
    
    def __init__(self, 
                name: str, 
                llm: Any, 
                tools: List[str], 
                playbook_path: str,
                zk_frameworks: Optional[List[str]] = None,
                security_properties: Optional[Dict[str, str]] = None):
        """Initialize the ZeroKProof agent.
        
        Args:
            name: Agent name
            llm: Language model to use
            tools: List of tool names
            playbook_path: Path to the playbook file
            zk_frameworks: Optional list of ZK frameworks to use
            security_properties: Optional security properties to ensure
        """
        super().__init__(name, llm, tools, playbook_path)
        
        self.zk_frameworks = zk_frameworks or [
            "zkSNARK",
            "zkSTARK",
            "Bulletproofs",
            "ZK-Rollups",
            "Circom",
            "Gnark",
            "zk-Nexus"
        ]
        
        self.security_properties = security_properties or {
            "completeness": "If the statement is true and the prover and verifier are honest, the verifier will be convinced",
            "soundness": "If the statement is false, no cheating prover can convince an honest verifier (except with negligible probability)",
            "zero_knowledge": "The verifier learns nothing besides the validity of the statement",
            "succinctness": "The proof is small in size and quick to verify",
            "transparency": "No trusted setup is required",
            "post_quantum_security": "Secure against quantum computer attacks"
        }
        
        # Check tools availability
        required_tools = ["crypto_tool", "zk_tool"]
        for tool in required_tools:
            if tool not in tools:
                logging.warning(f"ZeroKProof agent should have '{tool}' tool")
                
    async def design_zk_system(self, 
                           requirements: Dict[str, Any], 
                           framework: Optional[str] = None) -> Dict[str, Any]:
        """Design a zero-knowledge proof system.
        
        Args:
            requirements: ZK system requirements
            framework: Optional specific ZK framework to use
            
        Returns:
            ZK system design
        """
        design = {
            "framework": framework or self.select_framework(requirements),
            "protocol": {},
            "security_analysis": {},
            "performance_estimates": {},
            "implementation_plan": {}
        }
        
        # Create design prompt
        requirements_text = json.dumps(requirements, indent=2)
        frameworks_text = json.dumps(self.zk_frameworks, indent=2)
        security_text = json.dumps(self.security_properties, indent=2)
        
        target_framework = framework or "appropriate ZK framework"
        
        design_prompt = f"""
        Design a zero-knowledge proof system using {target_framework} based on the following requirements:
        {requirements_text}
        
        Available ZK frameworks:
        {frameworks_text}
        
        Required security properties:
        {security_text}
        
        Please provide:
        1. Detailed protocol design
        2. Security analysis
        3. Performance estimates
        4. Implementation plan
        5. Limitations and trade-offs
        
        Format your response as JSON with the following structure:
        {{
            "framework": "zkSNARK",
            "protocol": {{
                "overview": "High-level description of the protocol...",
                "setup_phase": "Description of the setup phase...",
                "prover_algorithm": "Details of the prover algorithm...",
                "verifier_algorithm": "Details of the verifier algorithm...",
                "mathematical_foundation": "Description of the mathematical foundation..."
            }},
            "security_analysis": {{
                "completeness": {{
                    "satisfied": true,
                    "justification": "The protocol satisfies completeness because..."
                }},
                "soundness": {{
                    "satisfied": true,
                    "justification": "The protocol satisfies soundness because..."
                }},
                "zero_knowledge": {{
                    "satisfied": true,
                    "justification": "The protocol satisfies zero-knowledge because..."
                }}
            }},
            "performance_estimates": {{
                "proof_size": "256 bytes",
                "proving_time": "5 seconds",
                "verification_time": "10 milliseconds",
                "setup_time": "1 minute",
                "memory_requirements": "4 GB RAM for proving"
            }},
            "implementation_plan": {{
                "phases": [
                    {{
                        "name": "Circuit Design",
                        "duration": "2 weeks",
                        "description": "Design and implement the arithmetic circuit..."
                    }}
                ],
                "tools": ["Circom", "SnarkJS"],
                "testing_strategy": "Description of the testing strategy..."
            }},
            "limitations_and_tradeoffs": [
                "Requires trusted setup",
                "Not post-quantum secure",
                "Higher proving time than zkSTARKs"
            ]
        }}
        """
        
        # Generate design using LLM
        design_result = await self.llm.process({"prompt": design_prompt})
        
        # Parse response
        if isinstance(design_result, dict) and "output" in design_result:
            try:
                parsed_result = json.loads(design_result["output"])
                design["framework"] = parsed_result.get("framework", design["framework"])
                design["protocol"] = parsed_result.get("protocol", {})
                design["security_analysis"] = parsed_result.get("security_analysis", {})
                design["performance_estimates"] = parsed_result.get("performance_estimates", {})
                design["implementation_plan"] = parsed_result.get("implementation_plan", {})
                design["limitations_and_tradeoffs"] = parsed_result.get("limitations_and_tradeoffs", [])
            except json.JSONDecodeError:
                logging.error("Failed to parse ZK design result")
                design["error"] = "Failed to parse result"
        
        return design
    
    def select_framework(self, requirements: Dict[str, Any]) -> str:
        """Select the most appropriate ZK framework based on requirements.
        
        Args:
            requirements: ZK system requirements
            
        Returns:
            Selected ZK framework
        """
        # Simple framework selection logic
        if requirements.get("post_quantum", False):
            return "zkSTARK"
        elif requirements.get("no_trusted_setup", False):
            return "Bulletproofs"
        elif requirements.get("small_proof_size", False):
            return "zkSNARK"
        else:
            return self.zk_frameworks[0]  # Default to first framework
    
    async def generate_circuit(self, 
                          problem_definition: Dict[str, Any], 
                          framework: str) -> Dict[str, Any]:
        """Generate ZK circuit design.
        
        Args:
            problem_definition: Problem definition
            framework: ZK framework to use
            
        Returns:
            ZK circuit design
        """
        problem_text = json.dumps(problem_definition, indent=2)
        
        circuit_prompt = f"""
        Generate a {framework} circuit design for the following problem:
        {problem_text}
        
        Please provide:
        1. Circuit overview
        2. Input/output signals
        3. Constraints
        4. Optimization considerations
        5. Implementation code
        
        Format your response as JSON with comprehensive circuit design.
        """
        
        # Generate circuit using LLM
        circuit_result = await self.llm.process({"prompt": circuit_prompt})
        
        if isinstance(circuit_result, dict) and "output" in circuit_result:
            try:
                return json.loads(circuit_result["output"])
            except json.JSONDecodeError:
                return {"raw_design": circuit_result["output"]}
        
        return {"error": "Failed to generate circuit design"}
    
    async def analyze_security(self, 
                          system_design: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze security of a ZK system.
        
        Args:
            system_design: ZK system design
            
        Returns:
            Security analysis
        """
        design_text = json.dumps(system_design, indent=2)
        security_text = json.dumps(self.security_properties, indent=2)
        
        security_prompt = f"""
        Perform a comprehensive security analysis on the following ZK system design:
        {design_text}
        
        Security properties to analyze:
        {security_text}
        
        Please include:
        1. Analysis of each security property
        2. Potential vulnerabilities
        3. Attack vectors
        4. Suggested mitigations
        5. Overall security assessment
        
        Format your response as JSON with detailed security analysis.
        """
        
        # Generate security analysis using LLM
        security_result = await self.llm.process({"prompt": security_prompt})
        
        if isinstance(security_result, dict) and "output" in security_result:
            try:
                return json.loads(security_result["output"])
            except json.JSONDecodeError:
                return {"raw_analysis": security_result["output"]}
        
        return {"error": "Failed to generate security analysis"}
    
    async def optimize_performance(self, 
                              circuit_design: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize performance of a ZK circuit.
        
        Args:
            circuit_design: ZK circuit design
            
        Returns:
            Optimized circuit design
        """
        circuit_text = json.dumps(circuit_design, indent=2)
        
        optimization_prompt = f"""
        Optimize the performance of the following ZK circuit design:
        {circuit_text}
        
        Please provide:
        1. Optimization techniques
        2. Constraint reduction strategies
        3. Proving time improvements
        4. Memory usage optimizations
        5. Before/after performance comparison
        
        Format your response as JSON with detailed optimization approach.
        """
        
        # Generate optimizations using LLM
        optimization_result = await self.llm.process({"prompt": optimization_prompt})
        
        if isinstance(optimization_result, dict) and "output" in optimization_result:
            try:
                return json.loads(optimization_result["output"])
            except json.JSONDecodeError:
                return {"raw_optimizations": optimization_result["output"]}
        
        return {"error": "Failed to generate optimizations"}
    
    async def create_implementation_guide(self, 
                                     system_design: Dict[str, Any]) -> Dict[str, Any]:
        """Create an implementation guide for a ZK system.
        
        Args:
            system_design: ZK system design
            
        Returns:
            Implementation guide
        """
        design_text = json.dumps(system_design, indent=2)
        
        guide_prompt = f"""
        Create a comprehensive implementation guide for the following ZK system design:
        {design_text}
        
        Please include:
        1. Step-by-step implementation instructions
        2. Required dependencies
        3. Code templates
        4. Testing procedures
        5. Performance benchmarking guidelines
        
        Format your response as JSON with a detailed implementation guide.
        """
        
        # Generate implementation guide using LLM
        guide_result = await self.llm.process({"prompt": guide_prompt})
        
        if isinstance(guide_result, dict) and "output" in guide_result:
            try:
                return json.loads(guide_result["output"])
            except json.JSONDecodeError:
                return {"raw_guide": guide_result["output"]}
        
        return {"error": "Failed to generate implementation guide"}
    
    async def run_playbook_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific playbook step.
        
        Args:
            step: Playbook step definition
            context: Execution context
            
        Returns:
            Step execution results
        """
        action = step.get("action", "")
        
        if action == "design_zk_system":
            requirements = step.get("requirements", context.get("requirements", {}))
            framework = step.get("framework", None)
            
            design = await self.design_zk_system(requirements, framework)
            return {"system_design": design}
            
        elif action == "generate_circuit":
            problem_definition = step.get("problem_definition", context.get("problem_definition", {}))
            framework = step.get("framework", context.get("system_design", {}).get("framework", self.zk_frameworks[0]))
            
            circuit = await self.generate_circuit(problem_definition, framework)
            return {"circuit_design": circuit}
            
        elif action == "analyze_security":
            system_design = step.get("system_design", context.get("system_design", {}))
            
            analysis = await self.analyze_security(system_design)
            return {"security_analysis": analysis}
            
        elif action == "optimize_performance":
            circuit_design = step.get("circuit_design", context.get("circuit_design", {}))
            
            optimizations = await self.optimize_performance(circuit_design)
            return {"optimized_design": optimizations}
            
        elif action == "create_implementation_guide":
            system_design = step.get("system_design", context.get("system_design", {}))
            
            guide = await self.create_implementation_guide(system_design)
            return {"implementation_guide": guide}
            
        else:
            return await super().run_playbook_step(step, context)
    
    async def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the ZeroKProof agent with the specified playbook.
        
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
        
        # Add final ZK artifacts
        if "system_design" in context:
            results["system_design"] = context["system_design"]
            
        if "circuit_design" in context:
            results["circuit_design"] = context["circuit_design"]
            
        if "security_analysis" in context:
            results["security_analysis"] = context["security_analysis"]
            
        if "optimized_design" in context:
            results["optimized_design"] = context["optimized_design"]
            
        if "implementation_guide" in context:
            results["implementation_guide"] = context["implementation_guide"]
            
        return results