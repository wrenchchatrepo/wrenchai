# WrenchAI Playbook Format Documentation

This document provides comprehensive documentation for the WrenchAI playbook format, including examples for all supported step types and configurations.

## Overview

Playbooks in WrenchAI are workflows that orchestrate the execution of AI agents to accomplish complex tasks. They are defined in YAML format and consist of a series of steps, each with a specific type and configuration.

## Playbook Structure

A playbook can be defined in two formats:

### Top-level Fields Format

```yaml
name: example_playbook
description: "An example playbook that demonstrates the standardized format"
tools:
  - web_search
  - code_generation
agents:
  - SuperAgent
  - CodeGeneratorAgent
agent_llms:
  SuperAgent: "claude-3.5-sonnet"
  CodeGeneratorAgent: "claude-3.5-sonnet"

steps:
  - step_id: step1
    type: standard
    description: "Step 1 description"
    # Step-specific fields...
    
  - step_id: step2
    type: standard
    description: "Step 2 description"
    # Step-specific fields...
```

### List-based Format with Metadata Step

```yaml
- step_id: metadata
  type: standard
  description: "Playbook Configuration"
  metadata:
    name: example_playbook
    description: "An example playbook"
    tools:
      - web_search
      - code_generation
    agents:
      - SuperAgent
      - CodeGeneratorAgent
    agent_llms:
      SuperAgent: "claude-3.5-sonnet"
      CodeGeneratorAgent: "claude-3.5-sonnet"

- step_id: step1
  type: standard
  description: "Step 1 description"
  # Step-specific fields...
  
- step_id: step2
  type: standard
  description: "Step 2 description"
  # Step-specific fields...
```

The WrenchAI playbook system supports both formats and automatically handles the conversion between them.

## Step Types

WrenchAI supports the following step types, each with specific configuration options:

### 1. Standard Step

A standard step is executed by a single agent performing a specific operation.

```yaml
- step_id: standard_step
  type: standard
  description: "Execute a single operation with one agent"
  agent: SuperAgent
  operation: "analyze_data"
  tools:
    - web_search
    - memory
  parameters:
    data_source: "sales_data.csv"
    analysis_type: "trend"
  next: next_step_id
```

### 2. Work in Parallel Step

A work in parallel step executes multiple operations concurrently, often with different agents.

```yaml
- step_id: parallel_step
  type: work_in_parallel
  description: "Execute multiple operations concurrently"
  agents:
    - SuperAgent:analyze_user_data
    - CodeGeneratorAgent:generate_frontend
    - CodeGeneratorAgent:generate_backend
  input_distribution:
    type: split
    field: "components"
  output_aggregation:
    type: merge
    strategy: "combine_content"
  next: next_step_id
```

### 3. Partner Feedback Loop Step

A partner feedback loop involves two agents collaborating in a review cycle.

```yaml
- step_id: feedback_loop_step
  type: partner_feedback_loop
  description: "Collaborative improvement process"
  agents:
    creator: CodeGeneratorAgent
    reviewer: InspectorAgent
  operations:
    - role: creator
      name: "create_initial_design"
    - role: reviewer
      name: "review_design"
    - role: creator
      name: "refine_design"
  iterations: 3
  next: next_step_id
```

### 4. Self Feedback Loop Step

A self feedback loop involves a single agent iteratively improving its own work.

```yaml
- step_id: self_improve_step
  type: self_feedback_loop
  description: "Self-improvement process"
  agent: SuperAgent
  operations:
    - name: "draft_content"
    - name: "self_critique"
    - name: "improve_content"
  iterations: 3
  termination_condition: "quality_score > 0.9"
  next: next_step_id
```

### 5. Process Step

A process step involves conditional branching with a sequence of operations.

```yaml
- step_id: process_step
  type: process
  description: "Conditional process with multiple steps"
  agent: TestEngineerAgent
  input:
    source: "test_suite"
  process:
    - operation: "run_unit_tests"
      condition: "unit_tests_passed == true"
      failure_action: "log_and_fix"
    - operation: "run_integration_tests"
      condition: "integration_tests_passed == true"
      failure_action: "log_and_fix"
  output:
    destination: "test_results"
  next: next_step_id
```

### 6. Versus Step

A versus step has two agents competing on the same task, with results compared and the best selected.

```yaml
- step_id: versus_step
  type: versus
  description: "Competitive approach comparison"
  agents:
    competitor1: SuperAgent
    competitor2: CodeGeneratorAgent
  task: "generate_algorithm"
  evaluation_criteria:
    - "efficiency"
    - "readability"
    - "correctness"
  judge: InspectorAgent
  next: next_step_id
```

### 7. Handoff Step

A handoff step delegates to specialized agents based on conditions.

```yaml
- step_id: handoff_step
  type: handoff
  description: "Conditional delegation to specialists"
  primary_agent: GithubJourneyAgent
  operation: "prepare_deployment"
  handoff_conditions:
    - condition: "needs_ci_cd_setup == true"
      target_agent: CodeGeneratorAgent
      operation: "setup_ci_cd"
    - condition: "needs_domain_config == true"
      target_agent: UXDesignerAgent
      operation: "configure_custom_domain"
  completion_action: "deploy_to_github_pages"
  next: next_step_id
```

## Common Fields

The following fields are common to all step types:

- `step_id`: Unique identifier for the step
- `type`: The type of step (standard, work_in_parallel, etc.)
- `description`: A human-readable description of the step
- `next`: Optional ID of the next step to execute

## Advanced Features

### Condition Evaluation

Conditions in process steps and handoff steps are evaluated against the current context. The syntax supports Python expressions:

```yaml
condition: "unit_tests_passed == true and code_coverage > 0.8"
```

### Input Distribution and Output Aggregation

For work_in_parallel steps, you can configure how inputs are distributed and outputs are combined:

#### Distribution Types

- `split`: Divides the input field among operations
- `duplicate`: Sends the same input to all operations
- `round_robin`: Alternates items among operations

#### Aggregation Types

- `merge`: Combines all results into a single structure
- `append`: Appends results in a list
- `filter`: Filters results based on criteria

## Best Practices

1. **Unique Step IDs**: Ensure each step has a unique ID
2. **Valid References**: Make sure `next` fields reference existing step IDs
3. **Required Tools**: List all tools needed by agents in the playbook's `tools` array
4. **Agent Consistency**: Verify all referenced agents are listed in the playbook's `agents` array
5. **Error Handling**: Include failure actions and conditions for critical steps
6. **Documentation**: Add detailed descriptions for steps and operations

## Examples

See the [example_playbook.yaml](../core/configs/playbooks/example_playbook.yaml) for a complete example playbook.

The [docusaurus_portfolio_playbook.yaml](../core/playbooks/docusaurus_portfolio_playbook.yaml) demonstrates a more complex real-world application.