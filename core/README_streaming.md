# WrenchAI Streaming System

This module provides a comprehensive streaming response system for WrenchAI, supporting various streaming formats and protocols integrated with the progress tracking system.

## Features

- Multiple streaming formats (Text, JSON, Binary, SSE)
- WebSocket streaming support
- Integration with progress tracking system
- Chunked transfer encoding support
- Event-based streaming
- Structured streaming with metadata
- Configurable buffer sizes and compression
- Automatic content type detection

## Usage Examples

### 1. Basic Text Streaming

```python
from fastapi import FastAPI
from core.streaming import StreamingConfig, StreamFormat, init_streaming_service

app = FastAPI()
streaming_service = init_streaming_service()

@app.get("/stream/text")
async def stream_text():
    async def generator():
        for i in range(10):
            yield f"Chunk {i}\n"
            await asyncio.sleep(0.5)
    
    config = StreamingConfig(format=StreamFormat.TEXT)
    return streaming_service.create_text_response(generator(), config)
```

### 2. JSON Streaming with Progress Tracking

```python
from core.streaming import StreamingConfig, StreamFormat
from core.progress_tracker import init_progress_tracker

# Initialize services
progress_tracker = init_progress_tracker()
streaming_service = init_streaming_service(progress_tracker)

@app.get("/stream/json")
async def stream_json():
    # Create a workflow in progress tracker
    workflow_id = progress_tracker.create_workflow(
        name="JSON Streaming Example",
        description="Example of streaming JSON with progress tracking"
    )
    progress_tracker.start_item(workflow_id)
    
    async def generator():
        for i in range(10):
            item = {
                "id": i,
                "value": i * i,
                "message": f"Item {i}"
            }
            yield item
            
            # Update progress
            progress = ((i + 1) / 10) * 100
            progress_tracker.update_progress(workflow_id, progress)
            await asyncio.sleep(0.5)
        
        # Mark workflow as complete
        progress_tracker.complete_item(workflow_id)
    
    config = StreamingConfig(format=StreamFormat.JSON)
    return streaming_service.create_json_response(
        source=generator(),
        config=config,
        progress_parent_id=workflow_id,
        progress_name="JSON streaming operation"
    )
```

### 3. Using the Context Manager

```python
from core.streaming import stream_response, StreamFormat

@app.get("/stream/context")
async def stream_with_context():
    async def generator():
        for i in range(10):
            yield f"Line {i}\n"
            await asyncio.sleep(0.2)
    
    with stream_response(generator(), format=StreamFormat.TEXT) as response:
        return response
```

### 4. Server-Sent Events (SSE)

```python
@app.get("/stream/sse")
async def stream_sse():
    async def generator():
        for i in range(10):
            yield {
                "id": i,
                "data": f"Event {i}",
                "progress": (i + 1) * 10
            }
            await asyncio.sleep(1)
    
    config = StreamingConfig(format=StreamFormat.SSE)
    return streaming_service.create_sse_response(
        source=generator(),
        config=config,
        event_type="update"
    )
```

### 5. WebSocket Streaming

```python
@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    try:
        await websocket.accept()
        
        async def generator():
            for i in range(20):
                yield {
                    "id": i,
                    "message": f"WebSocket message {i}",
                    "progress": (i + 1) * 5
                }
                await asyncio.sleep(0.5)
        
        await streaming_service.stream_to_websocket(
            websocket=websocket,
            source=generator(),
            format=StreamFormat.JSON
        )
        
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
```

## Integration with LLM Workflows

The streaming system can be used with LLM-based workflows to provide real-time updates as content is generated:

```python
async def llm_streaming_endpoint():
    # Create workflow in progress tracker
    workflow_id = progress_tracker.create_workflow(
        name="LLM Generation", 
        description="Generate text with LLM"
    )
    progress_tracker.start_item(workflow_id)
    
    async def generate():
        # Stream from LLM API
        full_text = ""
        async for chunk in llm_client.generate_stream("Your prompt here"):
            full_text += chunk
            
            # Update progress based on token count or other metrics
            progress = min(len(full_text) / 500 * 100, 100)
            progress_tracker.update_progress(workflow_id, progress)
            
            yield {
                "delta": chunk,
                "text": full_text,
                "progress": progress
            }
        
        # Mark workflow as complete
        progress_tracker.complete_item(workflow_id)
    
    config = StreamingConfig(format=StreamFormat.JSON)
    return streaming_service.create_json_response(
        source=generate(),
        config=config,
        progress_parent_id=workflow_id
    )
```

## Benefits

- **Real-time feedback**: Users see immediate results without waiting for the entire operation to complete
- **Progress tracking**: Integrated with WrenchAI's progress tracking system for accurate status updates
- **Reduced timeouts**: Long-running operations can return data incrementally without timing out
- **Improved UX**: Provides a responsive user experience with continuous feedback
- **Flexible formats**: Support for different streaming formats based on client needs
- **Error handling**: Graceful error handling with proper cleanup

## Implementation Notes

- The streaming system can handle both single-process FastAPI and multi-process deployment configurations.
- Streaming responses automatically handle client disconnections gracefully.
- When a client disconnects, related progress tracking items are properly marked as cancelled or failed.
- The system includes automatic retries for network issues during streaming.
- For very long-running operations, checkpoints are created to enable recovery if needed.