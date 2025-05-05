# Roles

## 1. Super (The Orchestrator)

### Responsibilities:
+ Problem Intake & Analysis: Receives the initial user request. Understands the user's goal and decomposes it into subtasks.
+ Role Assignment: Determines which `Journey` agents (and how many) are needed based on the problem's complexity and required expertise.
+ Tool Allocation: Assigns the appropriate tools to each `Journey` agent based on the subtasks. This requires the `Super` to have a registry of available tools and their capabilities.
+ Playbook Selection: Selects the relevant playbook(s) for each `Journey` agent. Playbooks define procedures, workflows, and quality control steps.
+ Clarification & Communication: Interacts with the user to clarify ambiguous requests, gather additional information, and define success criteria (acceptance criteria). This interaction is crucial for alignment.
+ Success Definition: Collaborates with the user to explicitly define what constitutes a successful outcome. This could be a specific output format, a performance metric, or a set of conditions that must be met.
+ Initial Plan Generation: Creates the initial plan, outlining the sequence of actions, agent assignments, tool allocations, and playbooks. This plan may be revised based on feedback from the `Inspector`.
+ Handoff Management: Facilitates handoffs between `Journey` agents, ensuring smooth transitions and data consistency.
+ Final Decision: Based on the `Inspector`'s final approval, delivers the result to the user or initiates further action if necessary.

### Tools (Default Config - Can be Extended):
+ Web Search: To gather initial information about the problem domain.
+ RAG: For accessing relevant documentation or knowledge bases.
+ Memory (STM & LTM): To store user preferences, past interactions, and the evolving plan.
+ Code Generation/Execution (Limited): Potentially for scripting simple tasks related to agent management.

### Bayesian Connection:
+ *Prior Probabilities:* Uses prior knowledge about tool effectiveness, agent capabilities, and playbook success rates to make informed decisions during planning.
+ *Evidence:* User input, clarification responses, and (indirectly) feedback from the `Inspector` serve as evidence to refine the plan and adjust probabilities.
+ *Decision-Making:*  Uses Bayesian reasoning to choose the optimal agent configuration, tool allocation, and playbook selection, aiming to maximize the probability of success.

###  YAML Config: Mostly default, might have parameters for things like "default_uncertainty_threshold" (when to ask for clarification)

## 2. Inspector (The Quality Controller & Monitor)

### Responsibilities:
+ Progress Monitoring: Tracks the progress of all `Journey` agents, potentially using progress bars or other visualization techniques.
+ Bottleneck Detection: Identifies any delays or issues that hinder the progress of `Journey` agents. Reports these bottlenecks to the `Super`.
+ Work Evaluation: Critically, this is the QC agent.  Reviews the intermediate and final outputs of each `Journey` agent *against the defined success criteria and the relevant playbook*.  This is the core of the Bayesian process at runtime.
+ Approval/Rejection: Approves or rejects the work of `Journey` agents. Rejection triggers a re-evaluation by the `Super` (potentially leading to re-planning or re-assignment).
+ Final Approval Signal: Notifies the `Super` when all `Journey` agents have successfully completed their tasks and their outputs have been approved.
+ Resource Monitoring (Optional): Could monitor resource usage (e.g., API calls, computation time) to identify inefficiencies.

### Tools (Default Config - Limited):
+ Memory (STM & LTM): To store the plan, progress updates, agent outputs, and evaluation results. Crucially, needs access to the success criteria defined by the `Super`.
+ Data Analysis (Limited): To analyze progress data and potentially identify trends or anomalies.
+ Specialized LLM Tools (for QC): *Very important*. This is where you'd integrate LLMs specifically trained or prompted for quality assessment in the relevant domains. For example, a "Code Review LLM" or a "Content Quality LLM."

### Bayesian Connection:
+ *Prior Probabilities:*  Has priors about the expected quality of work from different agents and tools, based on past performance.
+ *Evidence:* The outputs of `Journey` agents are the primary evidence.  The `Inspector` compares these outputs to the success criteria and the playbook, calculating a likelihood of the work being acceptable.
+ *Decision-Making:* Uses Bayes' Theorem to determine the posterior probability of the work being satisfactory.  If this probability falls below a threshold, the work is rejected.  This threshold is a key parameter.

```
The core Bayesian logic: `P(Acceptable | Output, Success Criteria, Playbook) = [P(Output | Acceptable, Success Criteria, Playbook) * P(Acceptable)] / P(Output)`
```

* YAML Config: Mostly default, might define acceptance thresholds, specify QC-specific LLMs.

## 3. Journey (The Workers)

### Responsibilities:
+ Task Execution: Performs the specific tasks assigned by the `Super`, following the designated playbook.
+ Tool Utilization: Uses the allocated tools to complete their tasks.
+ Output Generation: Produces the required outputs, adhering to the format and quality standards specified in the playbook.
+ Progress Reporting (Optional): May provide regular progress updates to the `Inspector`.
+ Error Handling: Attempts to handle errors encountered during task execution, potentially by retrying or using alternative tools (if allowed by the playbook).
+ Handoff Preparation: Prepares outputs for handoff to other agents, if required by the plan.

### Tools (Configurable via YAML):
+ Can have any combination of 1 to 5 tools, as determined by the `Super` and specified in the YAML configuration. This is the most flexible part of the system.
+ Examples: Web Search, RAG, Code Generation, Data Analysis, API Interaction, Specialized LLMs.

### Bayesian Connection:
+ *Internal Reasoning (Optional):*  More sophisticated `Journey` agents *could* use internal Bayesian reasoning to optimize their tool usage or choose between alternative actions within the constraints of their playbook. This adds a layer of autonomy.
+ *Evidence for Inspector:* Their outputs are the evidence used by the `Inspector`.

###  YAML Config:  *Highly* configurable. Defines the agent's role, tools, and playbook. This is where you'd specify the details of a particular type of `Journey` agent (e.g., a "Web Researcher" agent, a "Code Generator" agent, a "Data Analyst" agent).

## Key Interactions and Workflow:

+ 1.  User -> Super: User provides the initial request.
+ 2.  Super -> User:  `Super` clarifies the request and defines success criteria with the user.
+ 3.  Super -> Journey (Multiple): `Super` assigns tasks, tools, and playbooks to `Journey` agents based on a generated plan.
+ 4.  Journey -> Inspector: `Journey` agents execute their tasks and provide outputs to the `Inspector`.
+ 5.  Inspector -> Journey: `Inspector` evaluates the outputs and provides approval/rejection.
+ 6.  Inspector -> Super: `Inspector` reports progress, bottlenecks, and final approval status to the `Super`.
+ 7.  Super -> Journey (Feedback Loop): If the `Inspector` rejects work, the `Super` re-evaluates and may re-plan, re-assign, or request further clarification from the user.
+ 8.  Super -> User: Once the `Inspector` signals overall success, the `Super` delivers the final result to the user.

## YAML Configuration Example (Conceptual):

```yaml
# journey_agent_web_researcher.yaml
role: Journey
name: WebResearcher
description: An agent specialized in web research.
tools:
  - web_search
  - rag
playbook: web_research_playbook.yaml
```

```yaml
# journey_agent_code_generator.yaml
role: Journey
name: CodeGenerator
description: An agent specialized in generating Python code.
tools:
  - code_generation
  - code_execution
playbook: code_generation_playbook.yaml
```

```yaml
# super_agent_config.yaml
role: Super
name: DefaultSuper
description: Default configuration for the Super agent.
default_uncertainty_threshold: 0.8  # Ask for clarification if uncertainty is above 80%
```

```yaml
# inspector_agent_config.yaml
role: Inspector
name: DefaultInspector
description: Default configuration for the Inspector agent.
acceptance_threshold: 0.9 # Reject work if probability of being acceptable is below 90%
qc_llm: "code_review_llm_v2"
```

