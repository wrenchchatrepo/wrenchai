# Workflow Types in WrenchAI

This document describes the available workflow types for agent collaboration in the WrenchAI framework.

## Overview

Workflows in WrenchAI define how agents interact to accomplish tasks. Each workflow step has a `type` that determines the pattern of agent collaboration for that step.

## Available Workflow Types

### 1. `work_in_parallel`

**Purpose**: Run multiple agents simultaneously on different aspects of a problem.

**Use When**: You need to process multiple parts of a task concurrently to save time.

**Example**:
```yaml
- step_id: analyze_data
  type: work_in_parallel
  description: "Analyze different aspects of the dataset concurrently"
  agents:
    - DataScientistAgent:statistical_analysis
    - DataScientistAgent:visualization
    - DataScientistAgent:outlier_detection
  input: "dataset.csv"
  output_aggregation:
    type: merge
    strategy: "combine_analysis"
  next: generate_report
```

**Key Parameters**:
- `agents`: List of agents and their operations to run in parallel
- `input`: Common input for all agents
- `output_aggregation`: How to combine the results from each agent

---

### 2. `self_feedback_loop`

**Purpose**: Allow an agent to refine its work through iterative self-improvement.

**Use When**: A task requires multiple refinement cycles and the agent can evaluate its own work.

**Example**:
```yaml
- step_id: generate_code
  type: self_feedback_loop
  description: "Generate code with self-testing and refinement"
  agent: CodeGeneratorAgent
  operations:
    - name: "write_initial_code"
    - name: "test_code"
    - name: "refine_code"
  iterations: 3
  exit_condition: "tests_passing >= 95%"
  next: review_code
```

**Key Parameters**:
- `agent`: The agent performing the work
- `operations`: Sequence of operations in the feedback loop
- `iterations`: Maximum number of iterations
- `exit_condition`: Optional condition to exit the loop early

---

### 3. `partner_feedback_loop`

**Purpose**: Establish a collaborative feedback loop between two agents.

**Use When**: You need the specialized expertise of two different agents to refine work iteratively.

**Example**:
```yaml
- step_id: document_api
  type: partner_feedback_loop
  description: "Create API documentation with technical review"
  agents:
    creator: JourneyAgent
    reviewer: InspectorAgent
  operations:
    - role: creator
      name: "draft_documentation"
    - role: reviewer
      name: "review_documentation"
    - role: creator
      name: "revise_documentation"
  iterations: 2
  next: finalize_documentation
```

**Key Parameters**:
- `agents`: The collaborating agents with designated roles
- `operations`: Sequence of operations with assigned roles
- `iterations`: Number of feedback cycles to complete

---

### 4. `process`

**Purpose**: Define a structured process with clear inputs, operations, conditions, and outputs.

**Use When**: You need a step-by-step approach with validation at each stage.

**Example**:
```yaml
- step_id: process_customer_data
  type: process
  description: "Process customer data with validation and transformation"
  agent: DataScientistAgent
  input:
    source: "customer_database"
    format: "csv"
  process:
    - operation: "validate_data"
      condition: "is_valid == true"
      failure_action: "log_and_skip"
    - operation: "transform_data"
    - operation: "normalize_values"
  condition: "processed_records >= 1000"
  output:
    destination: "processed_data"
    format: "parquet"
  next: analyze_processed_data
```

**Key Parameters**:
- `input`: Source and format of input data
- `process`: Sequential operations with optional conditions
- `condition`: Criteria for successful completion
- `output`: Destination and format for results

---

### 5. `versus`

**Purpose**: Set up a competition between agents to find the best solution.

**Use When**: There are multiple valid approaches to a problem and you want to select the most effective one.

**Example**:
```yaml
- step_id: solution_competition
  type: versus
  description: "Generate competing solutions for performance optimization"
  agents:
    - name: DevopsAgent
      operation: "optimize_performance"
      approach: "horizontal_scaling"
    - name: DevopsAgent
      operation: "optimize_performance"
      approach: "vertical_scaling"
  evaluation_criteria:
    - "response_time"
    - "cost_efficiency"
    - "scalability"
  judge: InspectorAgent
  winner_selection: "highest_weighted_score"
  next: implement_winning_solution
```

**Key Parameters**:
- `agents`: Competing agents with their approaches
- `evaluation_criteria`: Metrics for judging solutions
- `judge`: Agent responsible for evaluation
- `winner_selection`: Method for selecting the winning solution

---

### 6. `handoff`

**Purpose**: Transfer control from one agent to specialized agents based on conditions.

**Use When**: Different scenarios require different specialized expertise.

**Example**:
```yaml
- step_id: code_analysis
  type: handoff
  description: "Analyze code and hand off to specialists when needed"
  primary_agent: CodeGeneratorAgent
  operation: "analyze_code"
  handoff_conditions:
    - condition: "contains_security_vulnerability == true"
      target_agent: InfosecAgent
      operation: "address_security_issues"
    - condition: "has_performance_bottleneck == true"
      target_agent: DevopsAgent
      operation: "optimize_performance"
    - condition: "needs_database_optimization == true"
      target_agent: DbaAgent
      operation: "optimize_database_queries"
  completion_action: "merge_results"
  next: generate_report
```

**Key Parameters**:
- `primary_agent`: The agent initiating the work
- `operation`: The initial operation to perform
- `handoff_conditions`: Conditions and target agents for specialized work
- `completion_action`: How to handle results after handoffs

## Using Workflow Types

When creating playbooks in `playbooks.yaml`, use these workflow types to define how agents collaborate. Each workflow type requires different parameters, as shown in the examples above.

Example workflow with multiple types:
```yaml
workflow:
  - step_id: initial_data_processing
    type: process
    # ... process parameters ...
    
  - step_id: parallel_analysis
    type: work_in_parallel
    # ... parallel work parameters ...
    
  - step_id: solution_refinement
    type: partner_feedback_loop
    # ... feedback loop parameters ...
```

## Best Practices

1. Choose the appropriate workflow type based on the collaboration pattern needed
2. Use consistent naming conventions for step_id and next references
3. Define clear exit conditions for iterative processes
4. Ensure all referenced agents and operations are properly configured
5. Use the appropriate level of granularity for each step