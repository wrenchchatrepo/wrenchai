# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Import core components
from core.streaming import (
    StreamingConfig, StreamFormat, StreamEvent, StreamChunk,
    init_streaming_service, stream_response
)
from core.progress_tracker import init_progress_tracker, ProgressItemType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create app
app = FastAPI(
    title="LLM Workflow Streaming Demo",
    description="Demonstration of streaming responses in LLM workflows"
)

# Initialize services
progress_tracker = None
streaming_service = None

# Mock LLM client (replace with actual LLM integration)
class MockLLM:
    """Mock LLM client that simulates streaming responses."""
    
    async def generate_stream(
        self, 
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        chunk_size: int = 5,
        delay: float = 0.05
    ) -> AsyncGenerator[str, None]:
        """Generate a response stream similar to an LLM API.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Model temperature
            chunk_size: Size of chunks to return (characters)
            delay: Delay between chunks in seconds
            
        Yields:
            Text chunks from the response
        """
        # Simulate processing time based on prompt length
        await asyncio.sleep(len(prompt) * 0.001)
        
        # Simple prompt-based responses for demonstration
        if "summarize" in prompt.lower():
            response = (
                "This is a summary of the provided content. "
                "The main points include the key information, "
                "important details, and concluding thoughts. "
                "The summary covers all essential elements while "
                "being significantly shorter than the original text. "
                "In conclusion, summarization is an important "
                "technique for condensing information effectively."
            )
        elif "code" in prompt.lower():
            response = """
def streaming_example():
    \"\"\"Example function demonstrating streaming from an LLM.\"\"\"
    # Initialize components
    progress = 0
    results = []
    
    # Process each step
    for i in range(10):
        # Simulate processing
        progress += 10
        yield {
            "progress": progress,
            "message": f"Processed step {i+1}"
        }
        
    # Return final result
    return results
"""
        elif "list" in prompt.lower():
            response = (
                "Here's a list of items as requested:\n\n"
                "1. First item with important details\n"
                "2. Second item with relevant information\n"
                "3. Third item demonstrating the pattern\n"
                "4. Fourth item showing continuity\n"
                "5. Final item with concluding thoughts"
            )
        else:
            response = (
                "I've processed your request about "
                f"\"{prompt[:30]}{'...' if len(prompt) > 30 else ''}\". "
                "The key aspects to consider are the context, "
                "relevant information, and potential applications. "
                "Based on the information provided, I would recommend "
                "approaching this with a structured methodology. "
                "Let me know if you need more specific details."
            )
        
        # Generate tokens one by one with delays
        for i in range(0, len(response), chunk_size):
            chunk = response[i:i+chunk_size]
            yield chunk
            await asyncio.sleep(delay)

# Create a mock LLM instance
mock_llm = MockLLM()

# LLM Workflow Pattern
class LLMWorkflow:
    """Base class for LLM-based workflows with streaming support."""
    
    def __init__(self, workflow_name: str, workflow_description: str):
        """Initialize LLM workflow.
        
        Args:
            workflow_name: Name of the workflow
            workflow_description: Description of the workflow
        """
        self.workflow_name = workflow_name
        self.workflow_description = workflow_description
        self.workflow_id = None
        
    async def start_workflow(self, input_data: Dict[str, Any]) -> str:
        """Start the workflow and return the workflow ID.
        
        Args:
            input_data: Input data for the workflow
            
        Returns:
            Workflow ID
        """
        global progress_tracker
        
        # Create workflow in progress tracker
        self.workflow_id = progress_tracker.create_workflow(
            name=self.workflow_name,
            description=self.workflow_description
        )
        
        # Start the workflow
        progress_tracker.start_item(self.workflow_id)
        
        return self.workflow_id
    
    async def process_step(
        self,
        step_name: str,
        step_description: str,
        weight: float = 1.0,
        parent_id: Optional[str] = None
    ) -> str:
        """Process a workflow step and track progress.
        
        Args:
            step_name: Name of the step
            step_description: Description of the step
            weight: Weight of this step in the workflow
            parent_id: Parent item ID (defaults to workflow ID)
            
        Returns:
            Step ID
        """
        global progress_tracker
        
        # Use workflow ID as parent if not specified
        if parent_id is None:
            parent_id = self.workflow_id
        
        # Create step in progress tracker
        step_id = progress_tracker.create_step(
            workflow_id=parent_id,
            name=step_name,
            description=step_description,
            weight=weight
        )
        
        # Start the step
        progress_tracker.start_item(step_id)
        
        return step_id
    
    async def execute(self, input_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the workflow and yield results.
        
        Args:
            input_data: Input data for the workflow
            
        Yields:
            Incremental results and progress updates
        """
        # Start the workflow
        await self.start_workflow(input_data)
        
        try:
            # Workflow implementation should be provided by subclasses
            async for result in self._run_workflow(input_data):
                yield result
                
            # Mark workflow as completed when done
            progress_tracker.complete_item(self.workflow_id)
            
        except Exception as e:
            # Mark workflow as failed on error
            logger.error(f"Workflow error: {str(e)}")
            progress_tracker.fail_item(self.workflow_id, str(e))
            yield {
                "event": "error",
                "error": str(e),
                "workflow_id": self.workflow_id
            }
    
    async def _run_workflow(self, input_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Run the workflow implementation.
        
        Args:
            input_data: Input data for the workflow
            
        Yields:
            Incremental results and progress updates
        """
        # Base implementation - should be overridden by subclasses
        yield {
            "event": "progress",
            "message": "Workflow is not implemented",
            "progress": 0
        }

# Example Workflow Implementations
class TextGenerationWorkflow(LLMWorkflow):
    """Simple text generation workflow with streaming support."""
    
    def __init__(self):
        """Initialize text generation workflow."""
        super().__init__(
            workflow_name="Text Generation",
            workflow_description="Generate text based on a prompt"
        )
    
    async def _run_workflow(self, input_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Run the text generation workflow.
        
        Args:
            input_data: Input data including 'prompt'
            
        Yields:
            Generated text chunks with progress updates
        """
        prompt = input_data.get("prompt", "")
        temperature = input_data.get("temperature", 0.7)
        
        # Step 1: Prompt processing
        step1_id = await self.process_step(
            step_name="Prompt Processing",
            step_description="Process and prepare the input prompt",
            weight=0.2
        )
        
        # Simulate processing
        await asyncio.sleep(0.5)
        
        # Enhanced prompt with instructions
        enhanced_prompt = f"Please respond to the following: {prompt}"
        
        # Update progress
        progress_tracker.update_progress(step1_id, 100)
        progress_tracker.complete_item(step1_id)
        
        yield {
            "event": "progress",
            "step": "prompt_processing",
            "message": "Prompt processed",
            "progress": 20
        }
        
        # Step 2: Text generation
        step2_id = await self.process_step(
            step_name="Text Generation",
            step_description="Generate text using LLM",
            weight=0.8
        )
        
        # Stream from LLM with progress tracking
        result_text = ""
        chunk_count = 0
        expected_chunks = 20  # Estimated
        
        async for chunk in mock_llm.generate_stream(
            prompt=enhanced_prompt,
            temperature=temperature
        ):
            result_text += chunk
            chunk_count += 1
            
            # Update progress
            progress = min(((chunk_count / expected_chunks) * 100), 95)
            progress_tracker.update_progress(step2_id, progress)
            
            # Yield chunk with progress
            yield {
                "event": "chunk",
                "delta": chunk,
                "text": result_text,
                "progress": 20 + (progress * 0.8),  # Scale to overall workflow progress
                "step": "text_generation"
            }
        
        # Complete the step
        progress_tracker.complete_item(step2_id)
        
        # Final result
        yield {
            "event": "complete",
            "text": result_text,
            "progress": 100,
            "message": "Text generation complete"
        }

class MultiStepWorkflow(LLMWorkflow):
    """Multi-step workflow with multiple LLM calls and processing."""
    
    def __init__(self):
        """Initialize multi-step workflow."""
        super().__init__(
            workflow_name="Multi-Step Processing",
            workflow_description="Process input through multiple LLM and analysis steps"
        )
    
    async def _run_workflow(self, input_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Run the multi-step workflow.
        
        Args:
            input_data: Input data including 'input_text' and 'analysis_type'
            
        Yields:
            Results from various processing steps with progress updates
        """
        input_text = input_data.get("input_text", "")
        analysis_type = input_data.get("analysis_type", "general")
        
        # Overall results object to build incrementally
        results = {
            "summary": "",
            "analysis": {},
            "recommendations": []
        }
        
        # Step 1: Summarization
        step1_id = await self.process_step(
            step_name="Summarization",
            step_description="Summarize the input text",
            weight=0.3
        )
        
        # Construct prompt for summarization
        summary_prompt = f"Summarize the following text concisely: {input_text}"
        
        # Stream summary generation
        summary = ""
        async for chunk in mock_llm.generate_stream(
            prompt=summary_prompt,
            delay=0.1
        ):
            summary += chunk
            
            # Update progress
            progress = min(len(summary) / 200 * 100, 100)  # Estimate based on length
            progress_tracker.update_progress(step1_id, progress)
            
            # Update results
            results["summary"] = summary
            
            # Yield incremental result
            yield {
                "event": "chunk",
                "step": "summarization",
                "results": results.copy(),
                "progress": progress * 0.3  # Scale to overall workflow progress
            }
        
        # Complete step
        progress_tracker.complete_item(step1_id)
        
        # Step 2: Analysis
        step2_id = await self.process_step(
            step_name="Analysis",
            step_description=f"Perform {analysis_type} analysis",
            weight=0.4
        )
        
        # Construct prompt for analysis
        analysis_prompt = (
            f"Perform {analysis_type} analysis on this text: {input_text}\n"
            f"Based on the summary: {summary}"
        )
        
        # Stream analysis generation
        analysis_text = ""
        async for chunk in mock_llm.generate_stream(
            prompt=analysis_prompt,
            delay=0.15
        ):
            analysis_text += chunk
            
            # Simulate parsing results into structured data
            if len(analysis_text) > 20:
                results["analysis"] = {
                    "type": analysis_type,
                    "content": analysis_text,
                    "key_points": [
                        p.strip() for p in analysis_text.split(".")
                        if len(p.strip()) > 15
                    ][:3]
                }
            
            # Update progress
            progress = min(len(analysis_text) / 300 * 100, 100)
            progress_tracker.update_progress(step2_id, progress)
            
            # Yield incremental results
            yield {
                "event": "chunk",
                "step": "analysis",
                "results": results.copy(),
                "progress": 30 + (progress * 0.4)  # Scale to overall progress
            }
        
        # Complete step
        progress_tracker.complete_item(step2_id)
        
        # Step 3: Recommendations
        step3_id = await self.process_step(
            step_name="Recommendations",
            step_description="Generate recommendations based on analysis",
            weight=0.3
        )
        
        # Construct prompt for recommendations
        rec_prompt = (
            f"Based on the {analysis_type} analysis: {analysis_text}\n"
            f"Generate a list of 3-5 actionable recommendations."
        )
        
        # Stream recommendations generation
        rec_text = ""
        async for chunk in mock_llm.generate_stream(
            prompt=rec_prompt,
            delay=0.12
        ):
            rec_text += chunk
            
            # Simulate parsing into list items
            if len(rec_text) > 30:
                # Extract recommendations by line
                lines = rec_text.split("\n")
                clean_lines = [
                    line.strip().lstrip("0123456789. -") 
                    for line in lines if len(line.strip()) > 5
                ]
                results["recommendations"] = clean_lines
            
            # Update progress
            progress = min(len(rec_text) / 250 * 100, 100)
            progress_tracker.update_progress(step3_id, progress)
            
            # Yield incremental results
            yield {
                "event": "chunk",
                "step": "recommendations",
                "results": results.copy(),
                "progress": 70 + (progress * 0.3)  # Scale to overall progress
            }
        
        # Complete step
        progress_tracker.complete_item(step3_id)
        
        # Final yield with complete results
        yield {
            "event": "complete",
            "results": results,
            "progress": 100,
            "message": "Workflow completed successfully"
        }

# Available workflows
WORKFLOWS = {
    "text_generation": TextGenerationWorkflow,
    "multi_step": MultiStepWorkflow
}

# Startup and Shutdown
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global progress_tracker, streaming_service
    
    # Initialize progress tracker
    progress_tracker = init_progress_tracker()
    await progress_tracker.start()
    
    # Initialize streaming service
    streaming_service = init_streaming_service(progress_tracker)
    
    logger.info("Services initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    global progress_tracker
    
    if progress_tracker:
        await progress_tracker.stop()
    
    logger.info("Services shutdown")

# API Routes
@app.post("/workflows/{workflow_type}/stream")
async def stream_workflow(
    workflow_type: str,
    input_data: Dict[str, Any]
):
    """Execute a workflow with streaming response.
    
    Args:
        workflow_type: Type of workflow to execute
        input_data: Input data for the workflow
        
    Returns:
        Streaming response with workflow results
    """
    if workflow_type not in WORKFLOWS:
        return {"error": f"Unknown workflow type: {workflow_type}"}
    
    # Create workflow instance
    workflow_class = WORKFLOWS[workflow_type]
    workflow = workflow_class()
    
    # Create streaming config
    config = StreamingConfig(
        format=StreamFormat.JSON,
        content_type="application/json"
    )
    
    # Return streaming response
    return streaming_service.create_json_response(
        source=workflow.execute(input_data),
        config=config,
        progress_parent_id=None,  # Workflow creates its own tracking
        progress_name=f"{workflow_type} workflow"
    )

@app.websocket("/workflows/{workflow_type}/ws")
async def workflow_websocket(websocket: WebSocket, workflow_type: str):
    """Execute a workflow with results streamed over WebSocket.
    
    Args:
        websocket: WebSocket connection
        workflow_type: Type of workflow to execute
    """
    if workflow_type not in WORKFLOWS:
        await websocket.accept()
        await websocket.send_json({"error": f"Unknown workflow type: {workflow_type}"})
        await websocket.close()
        return
    
    try:
        # Accept connection
        await websocket.accept()
        
        # Receive input data
        input_data = await websocket.receive_json()
        
        # Create workflow instance
        workflow_class = WORKFLOWS[workflow_type]
        workflow = workflow_class()
        
        # Execute workflow and stream results
        await streaming_service.stream_to_websocket(
            websocket=websocket,
            source=workflow.execute(input_data),
            format=StreamFormat.JSON,
            progress_parent_id=None,  # Workflow creates its own tracking
            progress_name=f"{workflow_type} workflow"
        )
        
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass

@app.get("/sse/{workflow_type}")
async def workflow_sse(
    request: Request,
    workflow_type: str,
    input_text: str = Query("Please provide a comprehensive analysis of this text."),
    analysis_type: str = Query("detailed")
):
    """Execute a workflow with results streamed as Server-Sent Events.
    
    Args:
        request: HTTP request
        workflow_type: Type of workflow to execute
        input_text: Input text for the workflow
        analysis_type: Type of analysis to perform
        
    Returns:
        SSE streaming response
    """
    if workflow_type not in WORKFLOWS:
        return {"error": f"Unknown workflow type: {workflow_type}"}
    
    # Create input data
    input_data = {
        "input_text": input_text,
        "analysis_type": analysis_type,
        "prompt": input_text  # For compatibility with text generation workflow
    }
    
    # Create workflow instance
    workflow_class = WORKFLOWS[workflow_type]
    workflow = workflow_class()
    
    # Create streaming config
    config = StreamingConfig(
        format=StreamFormat.SSE,
        content_type="text/event-stream"
    )
    
    # Return SSE response
    return streaming_service.create_sse_response(
        source=workflow.execute(input_data),
        config=config,
        event_type="update",
        progress_parent_id=None,  # Workflow creates its own tracking
        progress_name=f"{workflow_type} SSE workflow"
    )

# Run standalone
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)