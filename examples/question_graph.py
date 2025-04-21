# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import sys
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
import argparse

# Check for Pydantic AI
try:
    from pydantic_ai import Agent
    from pydantic_ai.graph import Graph, GraphState, GraphRunContext, register_node
    HAS_PYDANTIC_AI = True
except ImportError:
    HAS_PYDANTIC_AI = False
    logging.warning("pydantic-ai is not installed. Question graph will not work.")

# Check for rich (optional - for better output formatting)
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    logging.warning("rich is not installed. Output will use standard formatting.")

@dataclass
class QuestionState(GraphState):
    """State for the question-answer graph"""
    question: Optional[str] = None
    answer: Optional[str] = None
    evaluation: Optional[str] = None
    correct: bool = False
    attempts: int = 0
    history: List[Dict[str, str]] = field(default_factory=list)

@register_node
@dataclass
class AskNode:
    """Node that generates questions on a topic"""
    topic: str
    max_attempts: int = 3
    
    async def run(self, ctx: GraphRunContext[QuestionState]) -> str:
        """Generate a question
        
        Args:
            ctx: Graph run context
            
        Returns:
            Generated question
        """
        # Create agent for generating questions
        ask_agent = Agent(
            "openai:gpt-4-turbo",
            instructions=f"""
            You are a question generator on the topic of {self.topic}.
            Generate a challenging but answerable question.
            Ensure the question is clear and has a definitive answer.
            """
        )
        
        # Generate question based on attempts
        if ctx.state.attempts == 0:
            # First attempt - generate a new question
            response = await ask_agent.run("Generate a new question")
        else:
            # Subsequent attempts - generate a similar but different question
            history_str = "\n".join([
                f"Question: {item.get('question', '')}\nAnswer: {item.get('answer', '')}"
                for item in ctx.state.history
            ])
            
            response = await ask_agent.run(
                f"""
                Previous questions and answers:
                {history_str}
                
                Generate a new question on the same topic but different from the previous ones.
                """
            )
        
        # Update state
        question = response.output.strip()
        ctx.state.question = question
        ctx.state.answer = None
        ctx.state.evaluation = None
        ctx.state.correct = False
        ctx.state.attempts += 1
        
        if HAS_RICH:
            console.print(Panel(
                Markdown(f"# Question\n\n{question}"),
                border_style="blue",
                title=f"Attempt {ctx.state.attempts}/{self.max_attempts}"
            ))
        else:
            print(f"\n--- Attempt {ctx.state.attempts}/{self.max_attempts} ---")
            print(f"Question: {question}")
        
        return question

@register_node
@dataclass
class AnswerNode:
    """Node for answering a question"""
    
    async def run(self, ctx: GraphRunContext[QuestionState]) -> str:
        """Get an answer to the question
        
        Args:
            ctx: Graph run context
            
        Returns:
            The answer
        """
        # Check if we have a question
        if not ctx.state.question:
            return "No question to answer"
            
        # In a real application, this would interact with the user
        # For this example, we'll simulate user input or generate an answer
        
        if sys.stdin.isatty():  # Running in interactive mode
            # Get answer from user
            print("\nYour answer (or press Enter to generate one):")
            user_answer = input("> ")
            
            if user_answer.strip():
                answer = user_answer
            else:
                # Generate answer
                answer = await self._generate_answer(ctx.state.question)
        else:
            # Non-interactive mode - generate answer
            answer = await self._generate_answer(ctx.state.question)
        
        # Update state
        ctx.state.answer = answer
        
        if HAS_RICH:
            console.print(Panel(
                Markdown(f"## Answer\n\n{answer}"),
                border_style="green"
            ))
        else:
            print(f"\nAnswer: {answer}")
        
        return answer
    
    async def _generate_answer(self, question: str) -> str:
        """Generate an answer to the question
        
        Args:
            question: The question to answer
            
        Returns:
            Generated answer
        """
        # Create agent for generating answers
        answer_agent = Agent(
            "openai:gpt-4-turbo",
            instructions="""
            You are an intelligent system that answers questions.
            Provide a concise but detailed answer.
            Ensure your answer is factually correct.
            """
        )
        
        # Generate answer
        response = await answer_agent.run(f"Answer this question: {question}")
        return response.output.strip()

@register_node
@dataclass
class EvaluateNode:
    """Node for evaluating answers"""
    
    async def run(self, ctx: GraphRunContext[QuestionState]) -> bool:
        """Evaluate if the answer is correct
        
        Args:
            ctx: Graph run context
            
        Returns:
            True if the answer is correct, False otherwise
        """
        # Check if we have a question and answer
        if not ctx.state.question or not ctx.state.answer:
            return False
            
        # Create agent for evaluating answers
        evaluate_agent = Agent(
            "openai:gpt-4-turbo",
            instructions="""
            You are an answer evaluator.
            Given a question and answer, evaluate if the answer is correct.
            Provide specific feedback on the answer.
            Be strict but fair in your evaluation.
            """
        )
        
        # Evaluate answer
        prompt = f"""
        Question: {ctx.state.question}
        Answer: {ctx.state.answer}
        
        Evaluate the answer. Is it correct? Provide specific feedback.
        First, state your evaluation result as either "CORRECT" or "INCORRECT".
        Then, on a new line, provide your specific feedback.
        """
        
        response = await evaluate_agent.run(prompt)
        evaluation = response.output.strip()
        
        # Check if the answer is correct
        is_correct = evaluation.startswith("CORRECT")
        
        # Update state
        ctx.state.evaluation = evaluation
        ctx.state.correct = is_correct
        
        # Add to history
        ctx.state.history.append({
            "question": ctx.state.question,
            "answer": ctx.state.answer,
            "evaluation": evaluation,
            "correct": is_correct
        })
        
        if HAS_RICH:
            console.print(Panel(
                Markdown(f"## Evaluation\n\n{evaluation}"),
                border_style="yellow" if is_correct else "red"
            ))
        else:
            print(f"\nEvaluation: {evaluation}")
            print(f"Result: {'Correct' if is_correct else 'Incorrect'}")
        
        return is_correct

@register_node
@dataclass
class ReprimandNode:
    """Node for providing feedback on incorrect answers"""
    
    async def run(self, ctx: GraphRunContext[QuestionState]) -> None:
        """Provide feedback for incorrect answers
        
        Args:
            ctx: Graph run context
            
        Returns:
            None
        """
        if HAS_RICH:
            console.print(Panel(
                "Let's try another question!",
                border_style="blue"
            ))
        else:
            print("\nLet's try another question!")
        
        return None

class QuestionGraph:
    """Graph for question generation and evaluation"""
    
    def __init__(self, topic: str = "Python programming", max_attempts: int = 3):
        """Initialize the question graph
        
        Args:
            topic: Topic for questions
            max_attempts: Maximum number of attempts
        """
        self.topic = topic
        self.max_attempts = max_attempts
        self._check_requirements()
    
    def _check_requirements(self):
        """Check if all required dependencies are installed"""
        if not HAS_PYDANTIC_AI:
            logging.error("pydantic-ai is required for the question graph")
            raise ImportError("pydantic-ai is required for the question graph")
    
    def build_graph(self) -> Graph[QuestionState]:
        """Build the question graph
        
        Returns:
            The constructed graph
        """
        # Create graph
        graph = Graph[QuestionState]()
        
        # Create nodes
        ask_node = AskNode(topic=self.topic, max_attempts=self.max_attempts)
        answer_node = AnswerNode()
        evaluate_node = EvaluateNode()
        reprimand_node = ReprimandNode()
        
        # Set up edges
        graph.add_edge(ask_node, answer_node)
        graph.add_edge(answer_node, evaluate_node)
        graph.add_edge(evaluate_node, reprimand_node, lambda correct: not correct)
        graph.add_edge(evaluate_node, ask_node, lambda correct: not correct and 
                      graph.state.attempts < self.max_attempts)
        
        # Set initial node
        graph.set_initial_node(ask_node)
        
        return graph
    
    async def run(self) -> QuestionState:
        """Run the question graph
        
        Returns:
            Final state
        """
        # Build graph
        graph = self.build_graph()
        
        # Create initial state
        state = QuestionState()
        
        # Run graph
        await graph.run(state)
        
        return state

async def main_async():
    """Async main function"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Question Graph Example")
    parser.add_argument("--topic", default="Python programming", help="Topic for questions")
    parser.add_argument("--max-attempts", type=int, default=3, help="Maximum number of attempts")
    
    args = parser.parse_args()
    
    try:
        # Create and run question graph
        graph = QuestionGraph(topic=args.topic, max_attempts=args.max_attempts)
        final_state = await graph.run()
        
        # Print summary
        if HAS_RICH:
            console.print("\n[bold]Session Summary:[/bold]")
            
            for i, item in enumerate(final_state.history, 1):
                result = "✅ Correct" if item.get("correct") else "❌ Incorrect"
                console.print(f"[bold]Question {i}:[/bold] {item.get('question')} [{result}]")
        else:
            print("\nSession Summary:")
            
            for i, item in enumerate(final_state.history, 1):
                result = "Correct" if item.get("correct") else "Incorrect"
                print(f"Question {i}: {item.get('question')} [{result}]")
        
        # Print final result
        correct_count = sum(1 for item in final_state.history if item.get("correct"))
        total_count = len(final_state.history)
        
        if HAS_RICH:
            console.print(f"\nYou got [bold]{correct_count}/{total_count}[/bold] questions correct!")
        else:
            print(f"\nYou got {correct_count}/{total_count} questions correct!")
    
    except KeyboardInterrupt:
        print("\nQuestion session interrupted by user")
    except Exception as e:
        logging.error(f"Error running question graph: {e}")

def main():
    """Main entry point"""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()