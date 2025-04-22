# Playbook Creation Guide

Playbooks are the cornerstone of the WrenchAI framework, defining how agents collaborate to accomplish tasks. This guide will help you create your own custom playbooks without needing to modify agent or tool code.

## What Are Playbooks?

Playbooks are YAML configuration files that define:
- The workflow steps to execute
- Which agents perform each step
- How agents interact with each other
- Which tools agents can use
- The flow of information between steps

## Creating a New Playbook

### 1. Start With the Template

The easiest way to create a new playbook is to copy the template:

```bash
cp core/configs/playbook_template.yaml core/configs/my_custom_playbook.yaml
```

### 2. Define Basic Information

Start by naming and describing your playbook:

```yaml
name: "document_summarization"
description: "Analyze and summarize long documents with key insights extraction"
```

### 3. Plan Your Workflow

Before writing YAML, sketch the workflow:
1. What are the logical steps?
2. Which agents should handle each step?
3. How should information flow between steps?
4. Are there any parallel processes or feedback loops?

### 4. Define Workflow Steps

Define each step in your workflow:

```yaml
workflow:
  - step_id: analyze_document
    type: standard
    description: "Analyze document structure and content"
    agent: DataScientistAgent
    operation: "analyze_content"
    next: extract_insights
    
  - step_id: extract_insights
    # ... step configuration ...
```

For each step, specify:
- `step_id`: Unique identifier
- `type`: Workflow pattern (standard, work_in_parallel, etc.)
- `description`: Human-readable explanation
- `agent` or `agents`: Who performs the work
- `operation`: What function the agent performs
- `next`: The next step to execute (omit for final step)

### 5. Choose Workflow Types

Different workflow types enable different collaboration patterns:

#### Standard Step
```yaml
- step_id: simple_step
  type: standard
  description: "Single agent operation"
  agent: AgentName
  operation: "operation_name"
  next: next_step
```

#### Parallel Processing
```yaml
- step_id: parallel_step
  type: work_in_parallel
  description: "Multiple agents working concurrently"
  agents:
    - FirstAgent:operation_one
    - SecondAgent:operation_two
  input_distribution:
    type: split
    field: "data_items"
  output_aggregation:
    type: merge
    strategy: "combine_results"
  next: next_step
```

#### Partner Feedback Loop
```yaml
- step_id: feedback_step
  type: partner_feedback_loop
  description: "Collaborative refinement"
  agents:
    creator: CreatorAgent
    reviewer: ReviewerAgent
  operations:
    - role: creator
      name: "create_content"
    - role: reviewer
      name: "review_content"
    - role: creator
      name: "revise_content"
  iterations: 2
  next: next_step
```

#### Self-Improvement Loop
```yaml
- step_id: refinement_step
  type: self_feedback_loop
  description: "Self-testing and improvement"
  agent: CodeGeneratorAgent
  operations:
    - name: "write_code"
    - name: "test_code"
    - name: "improve_code"
  iterations: 3
  exit_condition: "tests_passing == true"
  next: next_step
```

#### Process With Conditions
```yaml
- step_id: process_step
  type: process
  description: "Structured multi-stage process"
  agent: ProcessAgent
  input:
    source: "input_data"
  process:
    - operation: "validate"
      condition: "valid == true"
      failure_action: "log_error"
    - operation: "transform"
    - operation: "finalize"
  output:
    destination: "processed_data"
  next: next_step
```

#### Competitive Solutions
```yaml
- step_id: competition_step
  type: versus
  description: "Find best approach through competition"
  agents:
    - name: FirstAgent
      operation: "solve_problem"
      approach: "approach_one"
    - name: SecondAgent
      operation: "solve_problem"
      approach: "approach_two"
  evaluation_criteria:
    - "accuracy"
    - "efficiency"
  judge: InspectorAgent
  winner_selection: "highest_score"
  next: next_step
```

#### Conditional Handoff
```yaml
- step_id: handoff_step
  type: handoff
  description: "Delegate to specialists based on conditions"
  primary_agent: AnalyzerAgent
  operation: "analyze_problem"
  handoff_conditions:
    - condition: "needs_security_review == true"
      target_agent: SecurityAgent
      operation: "security_review"
    - condition: "needs_performance_tuning == true"
      target_agent: PerformanceAgent
      operation: "optimize_performance"
  completion_action: "combine_results"
  next: next_step
```

### 6. Specify Tools and Agents

List all tools and agents used in your playbook:

```yaml
tools_allowed:
  - web_search
  - data_analysis
  - document_processor
  
agents:
  - DataScientistAgent
  - InspectorAgent
  - WriterAgent
```

### 7. Add Your Playbook to the System

Add your playbook to the main playbooks configuration:

```yaml
# In core/configs/playbooks.yaml
playbooks:
  # Existing playbooks...
  
  - name: "document_summarization"
    description: "Analyze and summarize long documents with key insights extraction"
    workflow:
      # Your workflow steps...
    tools_allowed:
      # Your tools...
    agents:
      # Your agents...
```

## Best Practices

1. **Single Responsibility**: Each step should do one thing well
2. **Clear Names**: Use descriptive step_ids and operation names
3. **Error Handling**: Include fallback paths for critical steps
4. **Validation**: Test your playbook with simple inputs first
5. **Documentation**: Add comments explaining complex logic
6. **Flow Control**: Be explicit about the next step for each step
7. **Tool Constraints**: Only include tools the playbook actually needs

## Troubleshooting

### Common Issues

1. **Missing next parameter**: Every step except the final one needs a next parameter
2. **Invalid agent references**: Ensure all agents are properly defined
3. **Tool restrictions**: Agents can only use tools listed in tools_allowed
4. **Step ordering**: Ensure step_ids referenced in next parameters exist
5. **Type mismatch**: Each workflow type requires specific parameters

### Validation

Use the config validation tool to check your playbook:

```bash
python -m core.tools.validate_config my_custom_playbook.yaml
```

## Examples

See the examples in `core/configs/playbooks.yaml` for inspiration, including:
- Document collaboration workflows
- Data analysis pipelines
- GitHub repository setup

## Advanced Topics

### Dynamic Tool Selection

You can specify tools for individual steps:

```yaml
- step_id: specialized_step
  type: standard
  description: "Step with specific tools"
  agent: SpecialistAgent
  operation: "specialized_operation"
  tools:
    - specialized_tool
  next: next_step
```

### Conditional Branching

Create branches in your workflow using conditions:

```yaml
- step_id: decision_point
  type: process
  description: "Decide next path"
  agent: DecisionAgent
  operation: "evaluate_options"
  next_conditions:
    - condition: "complexity > 7"
      next_step: complex_path
    - condition: "complexity <= 7"
      next_step: simple_path
```

### Input and Output Mapping

Define how data flows between steps:

```yaml
- step_id: data_producer
  type: standard
  description: "Produce data for next step"
  agent: DataAgent
  operation: "generate_data"
  output_mapping:
    result: "input_for_next_step"
  next: data_consumer
  
- step_id: data_consumer
  type: standard
  description: "Consume data from previous step"
  agent: ConsumerAgent
  operation: "process_data"
  input_mapping:
    data: "input_for_next_step"
```

## Need Help?

For more details, check the other documentation files:
- [Workflow Types](workflow_types.md)
- [Agent Configuration Guide](agent_configuration.md)
- [Tool Integration Guide](tool_integration.md)