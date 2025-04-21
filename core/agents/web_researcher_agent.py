# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Any, Optional, Union
import yaml
import logging
import asyncio
from pathlib import Path
import json

from .journey_agent import JourneyAgent
from ..tools.web_search import web_search, sync_web_search

class WebResearcher(JourneyAgent):
    """
    Advanced research agent specializing in complex problem investigation.
    
    This agent performs thorough web research, synthesizes information from
    multiple sources, identifies patterns, and generates comprehensive reports.
    """
    
    def __init__(self, 
                name: str, 
                llm: Any, 
                tools: List[str], 
                playbook_path: str,
                research_sources: Optional[List[str]] = None,
                knowledge_base_path: Optional[str] = None,
                max_sources_per_query: int = 5):
        """Initialize the WebResearcher agent.
        
        Args:
            name: Agent name
            llm: Language model to use
            tools: List of tool names
            playbook_path: Path to the playbook file
            research_sources: Optional list of preferred research sources
            knowledge_base_path: Optional path to knowledge base file
            max_sources_per_query: Maximum number of sources to use per query
        """
        super().__init__(name, llm, tools, playbook_path)
        
        self.research_sources = research_sources or []
        self.knowledge_base_path = knowledge_base_path or "research_knowledge_base.json"
        self.max_sources_per_query = max_sources_per_query
        self.findings = {}
        
        # Load existing knowledge base if it exists
        self.knowledge_base = self._load_knowledge_base()
        
        # Check tools availability
        if "web_search" not in tools:
            logging.warning("WebResearcher agent should have 'web_search' tool")
    
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """Load the knowledge base from file if it exists.
        
        Returns:
            Knowledge base dictionary
        """
        try:
            kb_path = Path(self.knowledge_base_path)
            if kb_path.exists():
                with open(kb_path, 'r') as f:
                    return json.load(f)
            return {"topics": {}, "sources": {}, "citations": []}
        except Exception as e:
            logging.warning(f"Error loading knowledge base: {e}")
            return {"topics": {}, "sources": {}, "citations": []}
    
    def _save_knowledge_base(self) -> None:
        """Save the knowledge base to file."""
        try:
            with open(self.knowledge_base_path, 'w') as f:
                json.dump(self.knowledge_base, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving knowledge base: {e}")
    
    async def conduct_research(self, query: str, depth: int = 1) -> Dict[str, Any]:
        """Conduct research on a specific query.
        
        Args:
            query: Research query
            depth: Research depth (1-3)
            
        Returns:
            Research findings
        """
        findings = {
            "query": query,
            "sources": [],
            "information": [],
            "patterns": [],
            "recommendations": []
        }
        
        # Check if this query has been researched before
        if query in self.knowledge_base["topics"]:
            logging.info(f"Found existing research for '{query}'")
            findings["from_knowledge_base"] = True
            return self.knowledge_base["topics"][query]
        
        # Perform initial search
        try:
            search_results = await web_search(query, self.max_sources_per_query)
            
            # Process search results
            findings["sources"] = [
                {
                    "title": result.title,
                    "url": result.url,
                    "snippet": result.snippet,
                }
                for result in search_results
            ]
            
            # Extract information from results using the LLM
            sources_text = "\n\n".join([
                f"Source: {src['title']}\nURL: {src['url']}\nContent: {src['snippet']}"
                for src in findings["sources"]
            ])
            
            # Use the LLM to analyze the sources
            analysis_prompt = f"""
            Research Query: {query}
            
            Sources:
            {sources_text}
            
            Based on these sources, please provide:
            
            1. Key Information: Extract the most relevant information related to the query.
            2. Patterns: Identify any patterns or trends across the sources.
            3. Recommendations: Suggest some actionable recommendations based on the findings.
            
            Format your response as JSON with the following structure:
            {{
                "information": [list of extracted information points],
                "patterns": [list of identified patterns],
                "recommendations": [list of actionable recommendations]
            }}
            """
            
            # Use the LLM to analyze sources
            analysis_result = await self.llm.process({"prompt": analysis_prompt})
            
            # Extract structured information from response
            if isinstance(analysis_result, dict) and "output" in analysis_result:
                try:
                    parsed_analysis = json.loads(analysis_result["output"])
                    findings["information"] = parsed_analysis.get("information", [])
                    findings["patterns"] = parsed_analysis.get("patterns", [])
                    findings["recommendations"] = parsed_analysis.get("recommendations", [])
                except json.JSONDecodeError:
                    # If JSON parsing fails, extract information manually
                    response_text = analysis_result["output"]
                    
                    # Simple extraction based on headers
                    if "Key Information:" in response_text:
                        info_section = response_text.split("Key Information:")[1].split("Patterns:")[0]
                        findings["information"] = [i.strip() for i in info_section.split("\n") if i.strip().startswith("-")]
                    
                    if "Patterns:" in response_text:
                        pattern_section = response_text.split("Patterns:")[1].split("Recommendations:")[0]
                        findings["patterns"] = [p.strip() for p in pattern_section.split("\n") if p.strip().startswith("-")]
                    
                    if "Recommendations:" in response_text:
                        rec_section = response_text.split("Recommendations:")[1]
                        findings["recommendations"] = [r.strip() for r in rec_section.split("\n") if r.strip().startswith("-")]
            
            # If we need deeper research and have multiple sources
            if depth > 1 and len(findings["sources"]) > 1:
                # Follow-up research on key points
                for point in findings["information"][:3]:  # Limit to top 3 points for efficiency
                    follow_up_query = f"{query} {point}"
                    follow_up_results = await web_search(follow_up_query, 2)
                    
                    # Add new sources
                    for result in follow_up_results:
                        # Check if this source is already included
                        if not any(src["url"] == result.url for src in findings["sources"]):
                            findings["sources"].append({
                                "title": result.title,
                                "url": result.url,
                                "snippet": result.snippet,
                                "follow_up_query": follow_up_query
                            })
            
            # Update knowledge base
            self.knowledge_base["topics"][query] = findings
            
            # Add sources to knowledge base
            for source in findings["sources"]:
                if source["url"] not in self.knowledge_base["sources"]:
                    self.knowledge_base["sources"][source["url"]] = {
                        "title": source["title"],
                        "used_for": [query]
                    }
                else:
                    if query not in self.knowledge_base["sources"][source["url"]]["used_for"]:
                        self.knowledge_base["sources"][source["url"]]["used_for"].append(query)
            
            # Add citation
            self.knowledge_base["citations"].append({
                "query": query,
                "timestamp": asyncio.get_event_loop().time(),
                "source_count": len(findings["sources"])
            })
            
            # Save updated knowledge base
            self._save_knowledge_base()
            
            return findings
            
        except Exception as e:
            logging.error(f"Error conducting research: {e}")
            findings["error"] = str(e)
            return findings
    
    async def generate_report(self, research_findings: Dict[str, Any], format: str = "markdown") -> str:
        """Generate a comprehensive report from research findings.
        
        Args:
            research_findings: Research findings dictionary
            format: Report format (markdown, html, text)
            
        Returns:
            Formatted research report
        """
        query = research_findings.get("query", "Unknown Query")
        sources = research_findings.get("sources", [])
        information = research_findings.get("information", [])
        patterns = research_findings.get("patterns", [])
        recommendations = research_findings.get("recommendations", [])
        
        # Create a report prompt
        report_prompt = f"""
        Generate a comprehensive research report on the query: "{query}"
        
        Please include the following sections:
        1. Executive Summary
        2. Key Findings
        3. Patterns and Trends
        4. Recommendations
        5. Sources
        
        Information to include:
        - Key information: {information}
        - Patterns identified: {patterns}
        - Recommendations: {recommendations}
        - Sources: {[f"{s['title']} ({s['url']})" for s in sources]}
        
        Format the report in {format} format.
        Make it professional, concise, and well-structured.
        """
        
        # Generate report using LLM
        report_result = await self.llm.process({"prompt": report_prompt})
        
        if isinstance(report_result, dict) and "output" in report_result:
            return report_result["output"]
        return "Error generating report"
    
    async def analyze_multiple_queries(self, queries: List[str]) -> Dict[str, Any]:
        """Analyze multiple related queries and synthesize findings.
        
        Args:
            queries: List of related research queries
            
        Returns:
            Synthesized research findings
        """
        all_findings = []
        
        # Research each query
        for query in queries:
            findings = await self.conduct_research(query)
            all_findings.append(findings)
        
        # Synthesize findings
        synthesis_prompt = f"""
        Synthesize findings from multiple related research queries:
        {queries}
        
        Findings:
        {json.dumps(all_findings, indent=2)}
        
        Please provide:
        1. Common themes across all queries
        2. Key differences between query results
        3. Integrated recommendations based on all findings
        4. Gaps in information that require further research
        
        Format your response as JSON with these four sections.
        """
        
        # Generate synthesis using LLM
        synthesis_result = await self.llm.process({"prompt": synthesis_prompt})
        
        if isinstance(synthesis_result, dict) and "output" in synthesis_result:
            try:
                return json.loads(synthesis_result["output"])
            except json.JSONDecodeError:
                return {"raw_synthesis": synthesis_result["output"]}
        
        return {"error": "Failed to synthesize findings"}
    
    def validate_information(self, information: str, min_sources: int = 2) -> Dict[str, Any]:
        """Validate information by checking source reliability and consistency.
        
        Args:
            information: Information to validate
            min_sources: Minimum number of sources required for validation
            
        Returns:
            Validation results
        """
        # This would be more sophisticated in a real implementation
        sources_count = len(self.findings.get("sources", []))
        
        validation = {
            "validated": sources_count >= min_sources,
            "source_count": sources_count,
            "min_sources_required": min_sources,
            "reliability_score": min(0.9, sources_count / 10)  # Simple reliability heuristic
        }
        
        return validation
    
    async def run_playbook_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific playbook step.
        
        Args:
            step: Playbook step definition
            context: Execution context
            
        Returns:
            Step execution results
        """
        action = step.get("action", "")
        
        if action == "research":
            query = step.get("query", context.get("query", ""))
            depth = step.get("depth", 1)
            findings = await self.conduct_research(query, depth)
            self.findings = findings
            return {"findings": findings}
            
        elif action == "generate_report":
            format = step.get("format", "markdown")
            report = await self.generate_report(self.findings, format)
            return {"report": report}
            
        elif action == "validate":
            information = step.get("information", "")
            min_sources = step.get("min_sources", 2)
            validation = self.validate_information(information, min_sources)
            return {"validation": validation}
            
        elif action == "synthesize":
            queries = step.get("queries", [])
            synthesis = await self.analyze_multiple_queries(queries)
            return {"synthesis": synthesis}
            
        else:
            return await super().run_playbook_step(step, context)
    
    async def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the WebResearcher agent with the specified playbook.
        
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
        
        # Add final research findings and report if available
        if hasattr(self, "findings") and self.findings:
            results["findings"] = self.findings
            
        if "report" in context:
            results["report"] = context["report"]
            
        return results