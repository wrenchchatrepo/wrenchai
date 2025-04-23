please review this playbook outline and edit as needed. update all related documents as needed (agents, tools). this will be our first test of the framework so we're on the home strech!

name: docusaurus_portfolio_playbook
description: Build a public-facing Docusaurus portfolio with **six** sections: 1) select GitHub projects (AI/ML in Python), 2) useful scripts (Python, gcloud, SQL, LookML, JS/TS, Git), 3) technical articles, 4) frontend examples (NextJS, React), 5) GCP Analytics Pipeline, 6) Data Science (Plotly + Dash, PyMC, PyTorch, SciPy).
- step_1: analyse source materials and assign to codegenerators
- step_2: design, develop docuaurus environment
- step_3: generate scripts, articles, etc. 
- step_4: design, execute tests for docusaurus environment.
- step_5: design test scripts, proofread articlts, etc.
- step_6: user acceptanc testing 

SuperAgent
- web_search
- secrets_manager
- memory
- code_generation
- LLM: Claude-3.7-Sonnet (best for orchestration and complex reasoning)
- type: standard

GithubJourneyAgent
- github_tool
- github_mcp
- code_execution
- LLM: GPT-4.1 (Complex Tasks)
- type: handoff

CodeGeneratorAgent
- code_execution
- code_generation
- github_tool
- LLM: Claude-3.7-Sonnet (balanced reasoning and code generation)
- type: partner_feedback_loop
- type: work_in_parallel

CodeGeneratorAgent
- code_execution
- code_generation
- github_tool
- LLM: Claude-3.7-Sonnet (balanced reasoning and code generation)
- type: partner_feedback_loop
- type: work_in_parallel

CodifierAgent
- code_execution
- memory
- web_search
- LLM: Claude-3.7-Sonnet (efficient for code standardization)
- type: partner_feedback_loop

CodifierAgent
- code_execution
- memory
- web_search
- LLM: Claude-3.7-Sonnet (efficient for code standardization)
- type: partner_feedback_loop

UXDesignerAgent
- puppeteer
- code_execution
- web_search
- LLM: GPT-4.1 (Complex Tasks)
- type: partner_feedback_loop

InspectorAgent
- memory
- data_analysis
- bayesian_update
- LLM: Claude-3.7-Sonnet (excellent evaluation capabilities)
- type: partner_feedback_loop

TestEngineerAgent
- code_execution
- github_tool
- document_analyzer
- LLM: Claude-3.7-Sonnet (methodical test development)
- type: partner_feedback_loop

UATAgent
- browser_tools
- memory
- web_search
- LLM: Gemini-2.5-Flash (good for testing user journeys with faster reasoning)
- type: partner_feedback_loop

CodifierAgent
- code_execution
- memory
- web_search
- LLM: Claude-3.7-Sonnet (efficient for code standardization)
- type: partner_feedback_loop

InspectorAgent
- memory
- data_analysis
- bayesian_update
- LLM: Claude-3.7-Sonnet (excellent evaluation capabilities)
- type: process


```
the available values for the type: parameter in workflow steps are:
1. standard - Sequential, single-agent operation
2. work_in_parallel - Concurrent execution across multiple agents
3. self_feedback_loop - Iterative self-improvement by a single agent
4. partner_feedback_loop - Collaborative feedback loop between two agents
5. process - Structured process with validation steps and conditions
6. versus - Competition between agents to find the best solution
7. handoff - Transfer to specialized agents based on conditions
```

```
core/
	agents/
		code_generator_agent.py
		codifier_agent.py
		comptroller_agent.py
		data_scientist_agent.py
		dba_agent.py
		devops_agent.py
		gcp_architect_agent.py
		github_journey_agent.py
		infosec_agent.py
		inspector_agent.py
		journey_agent.py
		paralegal_agent.py
		super_agent.py
		test_engineer_agent.py
		uat_agent.py
		ux_designer_agent.py
		web_researcher_agent.py
		zerokproof_agent.py
	configs/
		agents.yaml
		github_agent_config.yaml
		inspector_agent_config.yaml
		journey_agent_template.yaml
		playbook_template.yaml
		playbooks.yaml
		pricing_data.yaml
		super_agent_config.yaml
		tools.yaml
		web_researcher_config.yaml
	playbooks/
		web_research_playbook.yaml
	tools/
		bayesian_tools.py
		code_execution.py
		github_tool.py
		mcp_client.py
		mcp_server.py
		mcp_servers.py
		mcp.py
		run_python.py
		web_search.py
	agent_system.py
	api.py
	bayesian_engine.py
	config_loader.py
	evaluation.py
	graph_workflow.py
	inputs.py
	tool_system.py
	utils.py
```
