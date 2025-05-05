## AI Agents with Memory
	Definition: A system where AI agents can store and retrieve information across different memory types (short-term and long-term) using a vector database for efficient storage and retrieval.
	Example: A customer service AI that remembers previous interactions with a customer. Short-term memory holds current conversation context, while long-term memory stores historical interactions and preferences in a vector database.

                   [Memory]
               [Short Term│Long Term]
                       ↑
                   [Store]
                 [Vector DB]
               ↑     ↑     ↑
[Input] --> [Agent 1│Agent 2│Agent 3] --> [Output]


### Hierarchical P r o c e s s
	Definition: A structured workflow with a manager agent coordinating multiple worker agents, allowing for task delegation and supervision.
	Example: A project management AI where the manager agent assigns tasks to specialized worker agents (research, writing, and editing), coordinating their efforts to complete a complex document.

               [Input]
                  ↓
            [Manager Agent]
          ↙   ↑    ↑    ↘
[Worker 1] [Worker 2] [Worker 3] → [Output]

## Workflow Process
	Definition: A conditional workflow that routes tasks based on specific criteria, allowing for different processing paths and rejoining of workflows.
	Example: A content moderation system where content is analyzed for complexity: simple content goes directly to automatic approval, while complex content requires human review before joining the publication queue.

[Input] → [Start] → <Condition> --Yes--> [Agent 1] --→ [Join] → [Agent 3] → [Output]
                       ↓                                ↑
                       No                              |
                       ↓ 
                                                    |
                   [Agent 2] ----------------------→

### Agentic Routing Workflow
	Definition: A system that dynamically routes tasks to different LLM instances based on their specializations or capabilities.
	Example: A customer inquiry system that routes technical questions to a technical LLM, billing questions to a financial LLM, and general queries to a customer service LLM.             

[LLM Call 1]
                  ↘
[In] → [LLM Router] → [LLM Call 2] → [Out]
                  ↘
             [LLM Call 3]

### Agentic Orchestrator Worker
	Definition: Similar to routing workflow but includes a synthesizer component that combines or processes the outputs from multiple LLM calls.
	Example: A research assistant that routes different aspects of a query to specialized LLMs (data analysis, literature review, methodology) and synthesizes their outputs into a cohesive research summary.

             [LLM Call 1]
                  ↘
[In] → [LLM Router] → [LLM Call 2] → [Synthesizer] → [Out]
                  ↘
             [LLM Call 3]

### Agentic Autonomous Workflow
	Definition: A self-monitoring system that can interact with its environment, take actions, and adapt based on feedback.
	Example: An AI trading agent that monitors market conditions, makes trading decisions, receives feedback from market responses, and adjusts its strategy accordingly.

[Human] ←→ [LLM Call] --ACTION--> [Environment]
             ↑ ↓                      |
             | |                      |
             | ←-----FEEDBACK---------┘
             ↓
           [Stop]

### Agentic Parallelization
	Definition: A system that processes multiple tasks simultaneously through different LLM instances and aggregates the results.
	Example: A document analysis system that simultaneously processes different sections of a large document through multiple LLMs and combines their insights into a single comprehensive analysis.

        [LLM Call 1]
             ↘
[In] → [LLM Call 2] → [Aggregator] → [Out]
             ↗
        [LLM Call 3]

### Agentic Prompt Chaining
	Definition: A sequential workflow with conditional gates that determine whether to proceed with subsequent steps or exit the process.
	Example: A code review system where code first undergoes syntax checking, and only if it passes does it proceed to security analysis and then performance optimization.

[In] → [LLM Call 1] → <Gate> --Pass--> [LLM Call 2] → [LLM Call 3] → [Out]
                        |
                        └--Fail--> [Exit]

### Agentic Evaluator Optimizer
	Definition: An iterative system that generates solutions and improves them based on evaluation feedback until meeting acceptance criteria.
	Example: An AI writing assistant that generates draft content, evaluates it against quality criteria, and iteratively improves it based on specific feedback until reaching the desired quality level.

[In] → [LLM Call Generator] --SOLUTION--> [LLM Call Evaluator] --ACCEPTED--> [Out]
           ↑                                    |
           └----REJECTED + FEEDBACK-------------┘

### Repetitive Agents
	Definition: A system designed to handle recurring tasks through automated loops, continuing until a specific condition is met.
	Example: A data processing agent that continuously monitors an email inbox, processes new messages according to predefined rules, and loops until no new messages are found.

[Input] → [Looping Agent] --→ [Task] --Done--> [Output]
             ↑     |
             └-----┘
         Next Iteration