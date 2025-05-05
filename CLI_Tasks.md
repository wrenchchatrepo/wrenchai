# Workflow Engine Implementation Summary

## Objective
Create a Workflow Engine for the WrenchAI CLI that can execute complex multi-agent workflows defined in playbooks like the Docusaurus Portfolio Playbook. The engine must support various workflow patterns including sequential execution, parallel processing, feedback loops, conditional branching, and agent handoff.

## Key Challenges
1. **Diverse Workflow Patterns**: The Docusaurus Portfolio Playbook defines multiple workflow types:
   - `standard`: Sequential step execution
   - `work_in_parallel`: Multiple operations executed concurrently
   - `partner_feedback_loop`: Two agents collaborating in a review cycle
   - `process`: Structured sequence with conditional branching
   - `handoff`: Specialized task delegation based on conditions
2. **State Management**: Each workflow needs to maintain its own state that can be:
   - Persisted between runs for resumability
   - Shared across different agents
   - Modified during execution
3. **Agent Coordination**: Multiple agents must work together on the same task, requiring:
   - Proper initialization of diverse agent types
   - Message passing between agents
   - Results aggregation across agents
4. **MCP Server Dependencies**: Different workflow steps require specific MCP servers (context7, puppeteer, etc.) with proper lifecycle management.
## Proposed Solution
The solution should leverage Pydantic-Graph for workflow definition and execution because:
1. It provides a strong foundation for directed graph execution
2. It supports state persistence and dependency injection
3. It handles asynchronous execution and progress tracking
4. It's already integrated with Pydantic AI, which is our LLM integration layer
**The implementation should:**
1. Create workflow classes corresponding to each pattern (StandardWorkflow, ParallelWorkflow, etc.)
2. Define a common WorkflowState that tracks execution progress
3. Implement agent delegation and result aggregation
4. Provide flexible human interaction points
5. Ensure proper MCP server management throughout execution
## Verification Criteria
The implementation will be successful if:
1. It can correctly parse and execute the Docusaurus Portfolio Playbook
2. Each workflow type (standard, partner_feedback_loop, etc.) executes as expected
3. Multi-agent interactions properly pass context and aggregate results
4. Progress is correctly tracked and reported
5. Execution can be resumed if interrupted
6. MCP servers are properly managed during the entire process
## Remaining Tasks
1. **Workflow Engine Core**:
   - Create base Workflow class with common functionality
   - Implement specialized workflow type classes
   - Define state management structure
2. **Agent Delegation**:
   - Enhance AgentRegistry to properly initialize specialized agents
   - Implement message passing between agents
   - Create result aggregation utilities
3. **SuperAgent Enhancement**:
   - Update SuperAgent to use the Workflow Engine
   - Implement playbook parsing and workflow detection
   - Add execution tracking and reporting
4. **MCP Server Integration**:
   - Enhance MCP server lifecycle management
   - Add support for required server types
   - Implement proper cleanup on completion or failure
5. **Testing & Validation**:
   - Create unit tests for each workflow pattern
   - Test with the Docusaurus Portfolio Playbook
   - Validate all execution paths
## Key Documentation and Code Snippets
### 1. Basic Graph Definition (Foundation for all workflows)
The core pattern for defining workflows uses Pydantic-Graph with `BaseNode` classes:
```
from __future__ import annotations
from dataclasses import dataclass
from pydantic_graph import BaseNode, End, Graph, GraphRunContext
@dataclass
class DivisibleBy5(BaseNode[None, None, int]):  # (1)!
    foo: int
    async def run(
        self,
        ctx: GraphRunContext,
    ) -> Increment | End[int]:
        if self.foo % 5 == 0:
            return End(self.foo)
        else:
            return Increment(self.foo)
@dataclass
class Increment(BaseNode):  # (2)!
    foo: int
    async def run(self, ctx: GraphRunContext) -> DivisibleBy5:
        return DivisibleBy5(self.foo + 1)
fives_graph = Graph(nodes=[DivisibleBy5, Increment])  # (3)!
result = fives_graph.run_sync(DivisibleBy5(4))  # (4)!
print(result.output)
#> 5
```

2. State Management in Workflows
States are maintained using dataclasses that store workflow progress:
```
@dataclass
class CountDownState:
    counter: int
@dataclass
class CountDown(BaseNode[CountDownState, None, int]):
    async def run(self, ctx: GraphRunContext[CountDownState]) -> CountDown | End[int]:
        if ctx.state.counter <= 0:
            return End(ctx.state.counter)
        ctx.state.counter -= 1
        return CountDown()
count_down_graph = Graph(nodes=[CountDown])
async def main():
    state = CountDownState(counter=3)
    async with count_down_graph.iter(CountDown(), state=state) as run:
        async for node in run:
            print('Node:', node)
    print('Final output:', run.result.output)
    # > Final output: 0
```

3. Complex Workflow with Feedback Loop
This example shows a feedback loop pattern similar to the `partner_feedback_loop` in our playbook:
```
from __future__ import annotations as _annotations
from dataclasses import dataclass, field
from pydantic import BaseModel, EmailStr
from pydantic_ai import Agent, format_as_xml
from pydantic_ai.messages import ModelMessage
from pydantic_graph import BaseNode, End, Graph, GraphRunContext
@dataclass
class User:
    name: str
    email: EmailStr
    interests: list[str]
@dataclass
class Email:
    subject: str
    body: str
@dataclass
class State:
    user: User
    write_agent_messages: list[ModelMessage] = field(default_factory=list)
email_writer_agent = Agent(
    'google-vertex:gemini-1.5-pro',
    output_type=Email,
    system_prompt='Write a welcome email to our tech blog.',
)
@dataclass
class WriteEmail(BaseNode[State]):
    email_feedback: str | None = None
    async def run(self, ctx: GraphRunContext[State]) -> Feedback:
        if self.email_feedback:
            prompt = (
                f'Rewrite the email for the user:\n'
                f'{format_as_xml(ctx.state.user)}\n'
                f'Feedback: {self.email_feedback}'
            )
        else:
            prompt = (
                f'Write a welcome email for the user:\n'
                f'{format_as_xml(ctx.state.user)}'
            )
        result = await email_writer_agent.run(
            prompt,
            message_history=ctx.state.write_agent_messages,
        )
        ctx.state.write_agent_messages += result.new_messages()
        return Feedback(result.output)
class EmailRequiresWrite(BaseModel):
    feedback: str
class EmailOk(BaseModel):
    pass
feedback_agent = Agent[None, EmailRequiresWrite | EmailOk](
    'openai:gpt-4o',
    output_type=EmailRequiresWrite | EmailOk,  # type: ignore
    system_prompt=(
        'Review the email and provide feedback, email must reference the users specific interests.'
    ),
)
@dataclass
class Feedback(BaseNode[State, None, Email]):
    email: Email
    async def run(
        self,
        ctx: GraphRunContext[State],
    ) -> WriteEmail | End[Email]:
        prompt = format_as_xml({'user': ctx.state.user, 'email': self.email})
        result = await feedback_agent.run(prompt)
        if isinstance(result.output, EmailRequiresWrite):
            return WriteEmail(email_feedback=result.output.feedback)
        else:
            return End(self.email)
```

4. Human-in-the-Loop Workflow (For interactive CLI usage)
**Example for workflows that need human intervention:**
```
@dataclass
class QuestionState:
    question: str | None = None
    ask_agent_messages: list[ModelMessage] = field(default_factory=list)
    evaluate_agent_messages: list[ModelMessage] = field(default_factory=list)
@dataclass
class Ask(BaseNode[QuestionState]):
    async def run(self, ctx: GraphRunContext[QuestionState]) -> Answer:
        result = await ask_agent.run(
            'Ask a simple question with a single correct answer.',
            message_history=ctx.state.ask_agent_messages,
        )
        ctx.state.ask_agent_messages += result.new_messages()
        ctx.state.question = result.output
        return Answer(result.output)
@dataclass
class Answer(BaseNode[QuestionState]):
    question: str
    async def run(self, ctx: GraphRunContext[QuestionState]) -> Evaluate:
        answer = input(f'{self.question}: ')
        return Evaluate(answer)
```
5. State Persistence for Resumable Workflows
```
async def main():
    run_id = 'run_abc123'
    persistence = FileStatePersistence(Path(f'count_down_{run_id}.json'))
    state = CountDownState(counter=5)
    await count_down_graph.initialize(
        CountDown(), state=state, persistence=persistence
    )
    done = False
    while not done:
        done = await run_node(run_id)
async def run_node(run_id: str) -> bool:
    persistence = FileStatePersistence(Path(f'count_down_{run_id}.json'))
    async with count_down_graph.iter_from_persistence(persistence) as run:
        node_or_end = await run.next()
    return isinstance(node_or_end, End)
```

6. Dependency Injection for External Services
**This pattern is useful for MCP server integration:**
```
@dataclass
class GraphDeps:
    executor: ProcessPoolExecutor
@dataclass
class Increment(BaseNode[None, GraphDeps]):
    foo: int
    async def run(self, ctx: GraphRunContext[None, GraphDeps]) -> DivisibleBy5:
        loop = asyncio.get_running_loop()
        compute_result = await loop.run_in_executor(
            ctx.deps.executor,
            self.compute,
        )
        return DivisibleBy5(compute_result)
    def compute(self) -> int:
        return self.foo + 1
```

## Key Challenges
1. **Diverse Workflow Patterns**: The Docusaurus Portfolio Playbook defines multiple workflow types that must be mapped to these patterns
2. **State Management**: Each workflow needs persistent state
3. **Agent Coordination**: Multiple agents work together on the same task
4. **MCP Server Dependencies**: Different workflow steps require specific MCP servers

## Proposed Solution
** Develop a WorkflowEngine class that:**
1. Maps playbook workflow types to Pydantic-Graph patterns
2. Creates appropriate workflow state classes for each type
3. Handles agent initialization and coordination
4. Manages MCP server lifecycle

## Verification Criteria
**The implementation should:**
1. Correctly execute the Docusaurus Portfolio Playbook
2. Support all workflow types
3. Properly coordinate multiple agents
4. Track and report progress
5. Manage MCP servers correctly

## Remaining Tasks

1. **Workflow Engine Core**: Create base and specialized workflow classes
2. **Agent Delegation**: Enhance agent registration and coordination
3. **SuperAgent Enhancement**: Update to use the Workflow Engine
4. **MCP Server Integration**: Improve lifecycle management
5. **Testing & Validation**: Test with actual playbooks
These code snippets and patterns from the Pydantic-Graph documentation provide a solid foundation for implementing all the required workflow types.

## mcp-server-context7
**I discovered this documentation through a systematic approach:**
1. **Initial Resource Identification**:
   - I used the `resolve-library-id` tool to search for "pydantic-ai" which returned the Context7-compatible library ID "/pydantic/pydantic-ai"
   - This confirmed that Pydantic AI was the primary framework being used
2. **Topic-Specific Documentation Retrieval**:
   - I used the `get-library-docs` tool with parameters:
     - context7CompatibleLibraryID: "/pydantic/pydantic-ai"
     - topic: "workflows"
   - This returned initial documentation about workflow concepts
3. **Refined Search for Implementation Details**:
   - I performed a more targeted search with:
     - context7CompatibleLibraryID: "/pydantic/pydantic-ai"
     - topic: "graph workflow"
   - This returned detailed code examples of different workflow patterns
4. **Source Identification**:
   The documentation came primarily from these files in the Pydantic AI repository:
   - `docs/graph.md` - Core documentation for Pydantic-Graph
   - `docs/examples/question-graph.md` - Example of human-in-the-loop workflow
   - `docs/examples/flight-booking.md` - Multi-agent workflow examples
   - `pydantic_graph/README.md` - Basic usage patterns
