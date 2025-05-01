# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, AsyncGenerator, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import our streaming module
from core.streaming import (
    StreamingConfig, StreamFormat, StreamEvent, StreamChunk,
    init_streaming_service, stream_response, stream_list, stream_chunks
)
from core.progress_tracker import init_progress_tracker, track_progress, ProgressItemType

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Streaming API Example",
    description="Example API demonstrating streaming responses",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
progress_tracker = None
streaming_service = None

@app.on_event("startup")
async def startup_event():
    """Initialize the system on startup"""
    global progress_tracker, streaming_service
    
    # Initialize progress tracker
    progress_tracker = init_progress_tracker()
    await progress_tracker.start()
    
    # Initialize streaming service with progress tracker
    streaming_service = init_streaming_service(progress_tracker)
    
    logger.info("Services initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global progress_tracker
    
    if progress_tracker:
        await progress_tracker.stop()
    
    logger.info("Services shutdown")

# Example 1: Simple text streaming
@app.get("/stream/text")
async def stream_text_endpoint(
    delay: float = Query(0.1, description="Delay between chunks in seconds"),
    chunk_size: int = Query(5, description="Size of each chunk in characters")
):
    """Stream a text response with specified delay and chunk size."""
    
    # Create a workflow in progress tracker
    workflow_id = progress_tracker.create_workflow(
        name="Text streaming example",
        description="Example of streaming text with progress tracking"
    )
    progress_tracker.start_item(workflow_id)
    
    # Text to stream
    text = "This is an example of streaming text from the server to the client. " \
           "Streaming is useful for long-running operations where you want to show " \
           "progress to the user before the entire response is ready."
    
    # Create source generator
    async def generator() -> AsyncGenerator[str, None]:
        total_chunks = (len(text) + chunk_size - 1) // chunk_size
        chunks_sent = 0
        
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i+chunk_size]
            yield chunk
            
            # Update progress
            chunks_sent += 1
            progress = (chunks_sent / total_chunks) * 100
            progress_tracker.update_progress(workflow_id, progress)
            
            # Add delay
            await asyncio.sleep(delay)
        
        # Mark workflow as complete
        progress_tracker.complete_item(workflow_id)
    
    # Create streaming response
    config = StreamingConfig(
        format=StreamFormat.TEXT,
        content_type="text/plain"
    )
    
    return streaming_service.create_text_response(
        source=generator(),
        config=config,
        progress_parent_id=workflow_id,
        progress_name="Text streaming operation"
    )

# Example 2: JSON streaming
@app.get("/stream/json")
async def stream_json_endpoint(
    count: int = Query(10, description="Number of items to stream"),
    delay: float = Query(0.5, description="Delay between items in seconds")
):
    """Stream a series of JSON objects."""
    
    # Create a workflow in progress tracker
    workflow_id = progress_tracker.create_workflow(
        name="JSON streaming example",
        description="Example of streaming JSON objects with progress tracking"
    )
    progress_tracker.start_item(workflow_id)
    
    # Create source generator
    async def generator() -> AsyncGenerator[Dict[str, Any], None]:
        for i in range(count):
            # Create item
            item = {
                "id": i,
                "value": i * i,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Item {i} of {count}"
            }
            
            yield item
            
            # Update progress
            progress = ((i + 1) / count) * 100
            progress_tracker.update_progress(workflow_id, progress)
            
            # Add delay
            await asyncio.sleep(delay)
        
        # Mark workflow as complete
        progress_tracker.complete_item(workflow_id)
    
    # Create streaming response
    config = StreamingConfig(
        format=StreamFormat.JSON,
        content_type="application/json"
    )
    
    return streaming_service.create_json_response(
        source=generator(),
        config=config,
        progress_parent_id=workflow_id,
        progress_name="JSON streaming operation"
    )

# Example 3: SSE (Server-Sent Events)
@app.get("/stream/sse")
async def stream_sse_endpoint(
    count: int = Query(10, description="Number of events to send"),
    delay: float = Query(1.0, description="Delay between events in seconds")
):
    """Stream a series of events using Server-Sent Events (SSE)."""
    
    # Create a workflow in progress tracker
    workflow_id = progress_tracker.create_workflow(
        name="SSE streaming example",
        description="Example of streaming SSE events with progress tracking"
    )
    progress_tracker.start_item(workflow_id)
    
    # Create source generator
    async def generator() -> AsyncGenerator[StreamChunk, None]:
        for i in range(count):
            # Calculate progress
            progress = ((i + 1) / count) * 100
            
            # Determine event type
            if i == 0:
                event = StreamEvent.STARTED
            elif i == count - 1:
                event = StreamEvent.COMPLETE
            else:
                event = StreamEvent.CHUNK
            
            # Create chunk with data and progress
            chunk = StreamChunk(
                delta=f"Event {i + 1}",
                data={
                    "id": i,
                    "value": i * i,
                    "timestamp": datetime.utcnow().isoformat()
                },
                event=event,
                progress=progress,
                metadata={"remaining": count - i - 1}
            )
            
            yield chunk
            
            # Update progress
            progress_tracker.update_progress(workflow_id, progress)
            
            # Add delay
            await asyncio.sleep(delay)
        
        # Mark workflow as complete
        progress_tracker.complete_item(workflow_id)
    
    # Create streaming response
    config = StreamingConfig(
        format=StreamFormat.SSE,
        content_type="text/event-stream"
    )
    
    return streaming_service.create_sse_response(
        source=generator(),
        config=config,
        event_type="update",
        progress_parent_id=workflow_id,
        progress_name="SSE streaming operation"
    )

# Example 4: WebSocket streaming
@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """Stream data over a WebSocket connection."""
    
    try:
        # Accept the connection
        await websocket.accept()
        
        # Receive parameters from client
        params = await websocket.receive_json()
        count = params.get("count", 20)
        delay = params.get("delay", 0.5)
        
        # Create a workflow in progress tracker
        workflow_id = progress_tracker.create_workflow(
            name="WebSocket streaming example",
            description="Example of streaming data over WebSocket"
        )
        progress_tracker.start_item(workflow_id)
        
        # Create source generator
        async def generator():
            for i in range(count):
                # Create item
                item = {
                    "id": i,
                    "value": i * i,
                    "timestamp": datetime.utcnow().isoformat(),
                    "progress": ((i + 1) / count) * 100,
                    "event": "update"
                }
                
                yield item
                
                # Add delay
                await asyncio.sleep(delay)
        
        # Stream to WebSocket
        await streaming_service.stream_to_websocket(
            websocket=websocket,
            source=generator(),
            format=StreamFormat.JSON,
            progress_parent_id=workflow_id,
            progress_name="WebSocket streaming"
        )
        
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")

# Example 5: Using context manager
@app.get("/stream/context")
async def stream_with_context():
    """Stream using the context manager pattern."""
    
    # Create a workflow in progress tracker
    workflow_id = progress_tracker.create_workflow(
        name="Context manager example",
        description="Example of streaming using context manager"
    )
    progress_tracker.start_item(workflow_id)
    
    # List of items to stream
    items = [
        {"message": "Starting stream..."},
        {"message": "Processing item 1"},
        {"message": "Processing item 2"},
        {"message": "Processing item 3"},
        {"message": "Stream complete"}
    ]
    
    # Use context manager to create response
    with stream_response(
        source=stream_list(items, delay=0.5),
        format=StreamFormat.JSON,
        progress_parent_id=workflow_id,
        progress_name="Context manager streaming"
    ) as response:
        return response

# Example 6: Long-running operation with progress
@app.get("/stream/long-operation")
async def long_operation_endpoint(
    duration: int = Query(10, description="Duration of operation in seconds")
):
    """Simulate a long-running operation with progress updates."""
    
    # Create a workflow in progress tracker
    workflow_id = progress_tracker.create_workflow(
        name="Long-running operation",
        description=f"Simulated operation taking {duration} seconds"
    )
    progress_tracker.start_item(workflow_id)
    
    # Create generator for the operation
    async def generator() -> AsyncGenerator[Dict[str, Any], None]:
        # Yield initial status
        yield {
            "status": "started",
            "message": "Operation started",
            "progress": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Simulate work with progress
        steps = 20  # Number of progress updates
        step_duration = duration / steps
        
        for i in range(1, steps + 1):
            # Simulate work
            await asyncio.sleep(step_duration)
            
            # Calculate progress
            progress = (i / steps) * 100
            
            # Update progress tracker
            progress_tracker.update_progress(workflow_id, progress)
            
            # Yield progress update
            yield {
                "status": "in_progress",
                "message": f"Operation in progress - step {i} of {steps}",
                "progress": progress,
                "timestamp": datetime.utcnow().isoformat(),
                "details": {
                    "step": i,
                    "total_steps": steps,
                    "elapsed": i * step_duration,
                    "remaining": (steps - i) * step_duration
                }
            }
        
        # Complete the workflow
        progress_tracker.complete_item(workflow_id)
        
        # Yield completion status
        yield {
            "status": "completed",
            "message": "Operation completed successfully",
            "progress": 100,
            "timestamp": datetime.utcnow().isoformat(),
            "result": {
                "duration": duration,
                "steps_completed": steps
            }
        }
    
    # Create streaming response
    config = StreamingConfig(
        format=StreamFormat.JSON,
        content_type="application/json"
    )
    
    return streaming_service.create_json_response(
        source=generator(),
        config=config,
        progress_parent_id=workflow_id,
        progress_name="Long operation streaming"
    )

# Example 7: Hierarchical progress tracking with streaming
@app.get("/stream/hierarchical")
async def hierarchical_stream_endpoint():
    """Demonstrate hierarchical progress tracking with streaming."""
    
    # Create a workflow
    workflow_id = progress_tracker.create_workflow(
        name="Hierarchical example",
        description="Example of hierarchical progress tracking with streaming"
    )
    progress_tracker.start_item(workflow_id)
    
    # Create a generator that demonstrates hierarchical progress
    async def generator() -> AsyncGenerator[Dict[str, Any], None]:
        # Create steps within the workflow
        steps = []
        for i in range(3):
            step_id = progress_tracker.create_step(
                workflow_id=workflow_id,
                name=f"Step {i + 1}",
                description=f"Step {i + 1} of the hierarchical workflow",
                weight=1.0
            )
            steps.append(step_id)
        
        # Process each step
        for i, step_id in enumerate(steps):
            # Start the step
            progress_tracker.start_item(step_id)
            
            yield {
                "event": "step_started",
                "step": i + 1,
                "message": f"Starting step {i + 1}"
            }
            
            # Create some subtasks for this step
            subtasks = []
            for j in range(4):
                subtask_id = progress_tracker.create_subtask(
                    parent_id=step_id,
                    name=f"Subtask {j + 1}",
                    description=f"Subtask {j + 1} of step {i + 1}",
                    weight=1.0
                )
                subtasks.append(subtask_id)
            
            # Process each subtask
            for j, subtask_id in enumerate(subtasks):
                # Start the subtask
                progress_tracker.start_item(subtask_id)
                
                yield {
                    "event": "subtask_started",
                    "step": i + 1,
                    "subtask": j + 1,
                    "message": f"Starting subtask {j + 1} of step {i + 1}"
                }
                
                # Simulate work on this subtask
                subtask_steps = 5
                for k in range(subtask_steps):
                    # Simulate work
                    await asyncio.sleep(0.2)
                    
                    # Update progress
                    progress = ((k + 1) / subtask_steps) * 100
                    progress_tracker.update_progress(subtask_id, progress)
                    
                    yield {
                        "event": "progress",
                        "step": i + 1,
                        "subtask": j + 1,
                        "progress": progress,
                        "message": f"Step {i+1}, subtask {j+1}: {progress:.1f}% complete"
                    }
                
                # Complete the subtask
                progress_tracker.complete_item(subtask_id)
                
                yield {
                    "event": "subtask_completed",
                    "step": i + 1,
                    "subtask": j + 1,
                    "message": f"Completed subtask {j + 1} of step {i + 1}"
                }
            
            # Complete the step
            progress_tracker.complete_item(step_id)
            
            yield {
                "event": "step_completed",
                "step": i + 1,
                "message": f"Completed step {i + 1}"
            }
        
        # Complete the workflow
        progress_tracker.complete_item(workflow_id)
        
        yield {
            "event": "workflow_completed",
            "message": "Hierarchical workflow completed"
        }
    
    # Create streaming response
    config = StreamingConfig(
        format=StreamFormat.JSON,
        content_type="application/json"
    )
    
    return streaming_service.create_json_response(
        source=generator(),
        config=config,
        progress_parent_id=workflow_id,
        progress_name="Hierarchical streaming operation"
    )

# Example 8: Binary streaming
@app.get("/stream/binary")
async def binary_stream_endpoint():
    """Stream binary data with progress tracking."""
    
    # Create a workflow
    workflow_id = progress_tracker.create_workflow(
        name="Binary streaming example",
        description="Example of streaming binary data with progress tracking"
    )
    progress_tracker.start_item(workflow_id)
    
    # Create a generator for binary data
    async def generator() -> AsyncGenerator[bytes, None]:
        # Simulate a file or binary stream
        chunk_size = 1024  # 1 KB chunks
        total_size = chunk_size * 20  # 20 KB total
        chunks_sent = 0
        total_chunks = total_size // chunk_size
        
        for i in range(0, total_size, chunk_size):
            # Create a chunk of binary data
            chunk = bytes([i % 256 for _ in range(chunk_size)])
            
            yield chunk
            
            # Update progress
            chunks_sent += 1
            progress = (chunks_sent / total_chunks) * 100
            progress_tracker.update_progress(workflow_id, progress)
            
            # Add delay
            await asyncio.sleep(0.2)
        
        # Complete the workflow
        progress_tracker.complete_item(workflow_id)
    
    # Create streaming response
    config = StreamingConfig(
        format=StreamFormat.BINARY,
        content_type="application/octet-stream"
    )
    
    return streaming_service.create_binary_response(
        source=generator(),
        config=config,
        progress_parent_id=workflow_id,
        progress_name="Binary streaming operation"
    )

# Status endpoint to get info about active streams
@app.get("/status/streams")
async def get_streams_status():
    """Get status of all active streams."""
    
    streams_info = await streaming_service.get_active_streams_info()
    
    return JSONResponse(content={
        "active_streams": len(streams_info),
        "streams": streams_info
    })

# Status endpoint to get progress information
@app.get("/status/progress/{workflow_id}")
async def get_progress_status(workflow_id: str):
    """Get detailed progress information for a workflow."""
    
    # Get workflow progress tree
    progress_data = progress_tracker.get_workflow_progress(workflow_id)
    
    if not progress_data:
        return JSONResponse(
            status_code=404,
            content={"error": "Workflow not found"}
        )
    
    return JSONResponse(content=progress_data)

# Overall status dashboard data
@app.get("/status/dashboard")
async def get_dashboard_data():
    """Get data for status dashboard."""
    
    # Get overall progress summary
    progress_summary = progress_tracker.get_overall_progress()
    
    # Get active streams
    streams_info = await streaming_service.get_active_streams_info()
    
    # Combine data
    dashboard_data = {
        "progress": progress_summary,
        "streams": {
            "active_count": len(streams_info),
            "details": streams_info
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return JSONResponse(content=dashboard_data)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)