# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import asyncio
import json
import logging
from enum import Enum
from typing import (
    Any, AsyncGenerator, Callable, Dict, List, Optional, 
    Union, TypeVar, Generic, AsyncIterable
)

from fastapi import WebSocket
from fastapi.responses import StreamingResponse, Response
from sse_starlette.sse import EventSourceResponse

from core.progress_tracker import ProgressTracker, ProgressStatus, ProgressItemType

logger = logging.getLogger(__name__)

# Type variable for generic streaming content
T = TypeVar('T')


class StreamFormat(str, Enum):
    """Format for streaming responses."""
    TEXT = "text"
    JSON = "json"
    BINARY = "binary"
    SSE = "sse"  # Server-Sent Events


class StreamEncoding(str, Enum):
    """Encoding for streaming responses."""
    UTF8 = "utf-8"
    ASCII = "ascii"
    LATIN1 = "latin-1"
    BASE64 = "base64"


class StreamCompression(str, Enum):
    """Compression for streaming responses."""
    NONE = "none"
    GZIP = "gzip"
    DEFLATE = "deflate"
    BROTLI = "br"


class StreamEvent(str, Enum):
    """Event types for streaming updates."""
    STARTED = "started"
    PROGRESS = "progress"
    CHUNK = "chunk"
    ERROR = "error"
    COMPLETE = "complete"
    CANCELLED = "cancelled"


class StreamingConfig:
    """Configuration for streaming responses."""
    
    def __init__(
        self,
        format: StreamFormat = StreamFormat.TEXT,
        encoding: StreamEncoding = StreamEncoding.UTF8,
        compression: StreamCompression = StreamCompression.NONE,
        content_type: Optional[str] = None,
        buffer_size: int = 4096,
        chunk_size: int = 1024,
        retry_timeout: int = 5000,
        keep_alive_interval: int = 15,
    ):
        """Initialize streaming configuration.
        
        Args:
            format: Format of the streaming data
            encoding: Character encoding for text data
            compression: Compression type for the data
            content_type: HTTP Content-Type header (auto-detected if None)
            buffer_size: Size of the internal buffer in bytes
            chunk_size: Size of chunks sent to the client in bytes
            retry_timeout: Timeout for SSE retry attempts in milliseconds
            keep_alive_interval: Interval to send keepalive messages in seconds
        """
        self.format = format
        self.encoding = encoding
        self.compression = compression
        self.buffer_size = buffer_size
        self.chunk_size = chunk_size
        self.retry_timeout = retry_timeout
        self.keep_alive_interval = keep_alive_interval
        
        # Auto-detect content type if not provided
        if content_type is None:
            if format == StreamFormat.TEXT:
                self.content_type = "text/plain"
            elif format == StreamFormat.JSON:
                self.content_type = "application/json"
            elif format == StreamFormat.SSE:
                self.content_type = "text/event-stream"
            elif format == StreamFormat.BINARY:
                self.content_type = "application/octet-stream"
            else:
                self.content_type = "application/octet-stream"
        else:
            self.content_type = content_type
            
        # Add encoding to content type for text formats
        if self.format in (StreamFormat.TEXT, StreamFormat.JSON, StreamFormat.SSE):
            self.content_type += f"; charset={self.encoding}"
            
        # Add compression to content type if applicable
        if self.compression != StreamCompression.NONE:
            self.content_type += f"; {self.compression}"
    
    def get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for the streaming response.
        
        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "Content-Type": self.content_type,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
        
        if self.format == StreamFormat.SSE:
            headers.update({
                "X-Accel-Buffering": "no",  # Disable Nginx buffering
                "Transfer-Encoding": "chunked"
            })
            
        return headers


class StreamProgressAdapter:
    """Adapter for integrating streaming with the progress tracker."""
    
    def __init__(
        self,
        progress_tracker: ProgressTracker,
        parent_id: str,
        name: str,
        description: str = "Streaming operation",
        total_work: float = 100.0,
        weight: float = 1.0,
        type: ProgressItemType = ProgressItemType.OPERATION,
    ):
        """Initialize the stream progress adapter.
        
        Args:
            progress_tracker: Progress tracker to use
            parent_id: ID of the parent progress item
            name: Name of the progress item
            description: Description of the progress item
            total_work: Total work units
            weight: Weight of this item in parent's progress
            type: Type of progress item
        """
        self.progress_tracker = progress_tracker
        self.parent_id = parent_id
        self.name = name
        self.description = description
        self.total_work = total_work
        self.weight = weight
        self.type = type
        self.item_id = None
        self.initialized = False
        
    async def initialize(self) -> str:
        """Initialize the progress item.
        
        Returns:
            ID of the created progress item
        """
        if self.initialized:
            return self.item_id
            
        if self.type == ProgressItemType.OPERATION:
            self.item_id = self.progress_tracker.create_operation(
                parent_id=self.parent_id,
                name=self.name,
                description=self.description,
                total_work=self.total_work,
                weight=self.weight,
            )
        elif self.type == ProgressItemType.SUBTASK:
            self.item_id = self.progress_tracker.create_subtask(
                parent_id=self.parent_id,
                name=self.name,
                description=self.description,
                total_work=self.total_work,
                weight=self.weight,
            )
        else:
            raise ValueError(f"Unsupported progress item type: {self.type}")
            
        self.progress_tracker.start_item(self.item_id)
        self.initialized = True
        
        return self.item_id
        
    async def update(self, progress: float):
        """Update progress.
        
        Args:
            progress: Current progress (0-100)
        """
        if not self.initialized:
            await self.initialize()
            
        self.progress_tracker.update_progress(self.item_id, progress)
        
    async def increment(self, increment: float):
        """Increment progress.
        
        Args:
            increment: Amount to increment (0-100)
        """
        if not self.initialized:
            await self.initialize()
            
        self.progress_tracker.increment_progress(self.item_id, increment)
        
    async def complete(self):
        """Mark the progress item as completed."""
        if not self.initialized:
            await self.initialize()
            
        self.progress_tracker.complete_item(self.item_id)
        
    async def fail(self, error_message: str = None):
        """Mark the progress item as failed.
        
        Args:
            error_message: Error message
        """
        if not self.initialized:
            await self.initialize()
            
        self.progress_tracker.fail_item(self.item_id, error_message)


class StreamChunk(Generic[T]):
    """A chunk of data in a stream, with metadata."""
    
    def __init__(
        self,
        delta: Optional[T] = None,
        data: Optional[T] = None,
        event: StreamEvent = StreamEvent.CHUNK,
        progress: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        """Initialize a stream chunk.
        
        Args:
            delta: Incremental data for this chunk
            data: Complete data up to this point (for stateful formats)
            event: Type of streaming event
            progress: Progress indicator (0-100)
            metadata: Additional metadata for this chunk
            error: Error message if an error occurred
        """
        self.delta = delta
        self.data = data
        self.event = event
        self.progress = progress
        self.metadata = metadata or {}
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Returns:
            Dictionary representation of the chunk
        """
        result = {
            "event": self.event,
        }
        
        if self.delta is not None:
            result["delta"] = self.delta
            
        if self.data is not None:
            result["data"] = self.data
            
        if self.progress is not None:
            result["progress"] = self.progress
            
        if self.metadata:
            result["metadata"] = self.metadata
            
        if self.error:
            result["error"] = self.error
            
        return result
    
    def to_sse_event(self) -> str:
        """Convert to SSE event string.
        
        Returns:
            SSE-formatted event string
        """
        event_name = self.event.value
        data = json.dumps(self.to_dict())
        
        return f"event: {event_name}\ndata: {data}\n\n"
    
    def to_json(self) -> str:
        """Convert to JSON string.
        
        Returns:
            JSON-formatted string
        """
        return json.dumps(self.to_dict())
    
    def __str__(self) -> str:
        """String representation of the chunk.
        
        Returns:
            String representation
        """
        if isinstance(self.delta, str):
            return self.delta
            
        if isinstance(self.data, str):
            return self.data
            
        return self.to_json()


class StreamProcessor(Generic[T]):
    """Processes a stream of data and produces formatted output."""
    
    def __init__(
        self,
        config: StreamingConfig,
        progress_adapter: Optional[StreamProgressAdapter] = None,
    ):
        """Initialize the stream processor.
        
        Args:
            config: Streaming configuration
            progress_adapter: Optional progress tracker adapter
        """
        self.config = config
        self.progress_adapter = progress_adapter
        self.buffer = ""
        self.total_processed = 0
        self.is_completed = False
        self.is_started = False
        self.is_cancelled = False
        self.error = None
    
    async def process_stream(
        self,
        source: AsyncIterable[T],
        transform: Optional[Callable[[T], Union[T, StreamChunk[T]]]] = None,
    ) -> AsyncGenerator[Union[str, bytes], None]:
        """Process a stream of data and yield formatted chunks.
        
        Args:
            source: Async iterable source of data
            transform: Optional function to transform each item
            
        Yields:
            Formatted chunks of data
        """
        try:
            # Start progress tracking if enabled
            if self.progress_adapter and not self.is_started:
                await self.progress_adapter.initialize()
                
            # Mark as started
            self.is_started = True
            yield await self._format_event(StreamEvent.STARTED)
            
            # Process stream items
            async for item in source:
                if self.is_cancelled:
                    break
                    
                # Apply transformation if provided
                if transform:
                    result = transform(item)
                    if isinstance(result, StreamChunk):
                        chunk = result
                    else:
                        chunk = StreamChunk(delta=result)
                else:
                    # Create chunk directly from item
                    chunk = StreamChunk(delta=item)
                
                # Update progress if available
                if chunk.progress is not None and self.progress_adapter:
                    await self.progress_adapter.update(chunk.progress)
                    
                # Yield formatted output
                yield await self._format_chunk(chunk)
                
                # Update total processed
                self.total_processed += 1
                
            # Mark as completed
            self.is_completed = True
            if self.progress_adapter:
                await self.progress_adapter.complete()
                
            yield await self._format_event(StreamEvent.COMPLETE)
            
        except Exception as e:
            logger.error(f"Error processing stream: {e}")
            self.error = str(e)
            
            if self.progress_adapter:
                await self.progress_adapter.fail(self.error)
                
            yield await self._format_event(StreamEvent.ERROR, error=self.error)
    
    async def _format_event(
        self,
        event: StreamEvent,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Union[str, bytes]:
        """Format an event for output.
        
        Args:
            event: Event type
            metadata: Additional metadata
            error: Error message if applicable
            
        Returns:
            Formatted event data
        """
        chunk = StreamChunk(
            event=event,
            metadata=metadata,
            error=error,
        )
        
        return await self._format_chunk(chunk)
    
    async def _format_chunk(self, chunk: StreamChunk[T]) -> Union[str, bytes]:
        """Format a chunk for output.
        
        Args:
            chunk: The chunk to format
            
        Returns:
            Formatted chunk data
        """
        if self.config.format == StreamFormat.TEXT:
            # For text format, just return the string representation
            if isinstance(chunk.delta, str):
                return chunk.delta
            elif chunk.delta is not None:
                return str(chunk.delta)
            else:
                return str(chunk)
                
        elif self.config.format == StreamFormat.JSON:
            # For JSON format, return a JSON-encoded chunk
            return chunk.to_json() + "\n"
            
        elif self.config.format == StreamFormat.SSE:
            # For SSE format, return an SSE-formatted event
            return chunk.to_sse_event()
            
        elif self.config.format == StreamFormat.BINARY:
            # For binary format, we need binary data
            if isinstance(chunk.delta, bytes):
                return chunk.delta
            elif isinstance(chunk.delta, str):
                return chunk.delta.encode(self.config.encoding)
            else:
                # Fall back to JSON for non-binary data
                return chunk.to_json().encode(self.config.encoding)
                
        # Fallback to string representation
        return str(chunk)
    
    def cancel(self):
        """Cancel streaming."""
        self.is_cancelled = True


class StreamConverter:
    """Converts between different streaming formats."""
    
    @staticmethod
    async def text_to_sse(text_stream: AsyncIterable[str]) -> AsyncGenerator[str, None]:
        """Convert a text stream to SSE format.
        
        Args:
            text_stream: Async iterable of text chunks
            
        Yields:
            SSE-formatted events
        """
        event_id = 0
        
        # Send initial event
        yield f"id: {event_id}\nevent: started\ndata: Stream started\n\n"
        event_id += 1
        
        try:
            async for chunk in text_stream:
                # Skip empty chunks
                if not chunk:
                    continue
                    
                # Format as SSE event
                yield f"id: {event_id}\nevent: chunk\ndata: {chunk}\n\n"
                event_id += 1
                
            # Send completion event
            yield f"id: {event_id}\nevent: complete\ndata: Stream complete\n\n"
            
        except Exception as e:
            # Send error event
            yield f"id: {event_id}\nevent: error\ndata: {str(e)}\n\n"
    
    @staticmethod
    async def stream_to_websocket(
        stream: AsyncIterable[Union[str, bytes, Dict]],
        websocket: WebSocket,
    ):
        """Send a stream to a WebSocket.
        
        Args:
            stream: Stream of data to send
            websocket: WebSocket connection
        """
        try:
            async for chunk in stream:
                if isinstance(chunk, dict):
                    await websocket.send_json(chunk)
                elif isinstance(chunk, bytes):
                    await websocket.send_bytes(chunk)
                else:
                    await websocket.send_text(str(chunk))
        except Exception as e:
            logger.error(f"Error streaming to WebSocket: {e}")
            try:
                await websocket.send_json({
                    "event": "error",
                    "error": str(e)
                })
            except:
                pass


class StreamingService:
    """Service for creating and managing streaming responses."""
    
    def __init__(self, progress_tracker: Optional[ProgressTracker] = None):
        """Initialize the streaming service.
        
        Args:
            progress_tracker: Optional progress tracker for integration
        """
        self.progress_tracker = progress_tracker
        self.active_streams: Dict[str, StreamProcessor] = {}
    
    def create_text_response(
        self,
        source: AsyncIterable[str],
        config: Optional[StreamingConfig] = None,
        progress_parent_id: Optional[str] = None,
        progress_name: str = "Streaming text",
    ) -> StreamingResponse:
        """Create a text streaming response.
        
        Args:
            source: Async iterable source of text chunks
            config: Streaming configuration (defaults to text format)
            progress_parent_id: Parent ID for progress tracking
            progress_name: Name for progress tracking
            
        Returns:
            FastAPI StreamingResponse
        """
        # Create default config if not provided
        if config is None:
            config = StreamingConfig(format=StreamFormat.TEXT)
        
        # Create progress adapter if tracking enabled
        progress_adapter = None
        if self.progress_tracker and progress_parent_id:
            progress_adapter = StreamProgressAdapter(
                progress_tracker=self.progress_tracker,
                parent_id=progress_parent_id,
                name=progress_name,
                description="Streaming text response",
                type=ProgressItemType.OPERATION,
            )
        
        # Create processor and start streaming
        processor = StreamProcessor[str](config, progress_adapter)
        self.active_streams[id(processor)] = processor
        
        async def stream_generator():
            try:
                async for chunk in processor.process_stream(source):
                    yield chunk
            finally:
                # Clean up when streaming is done
                if id(processor) in self.active_streams:
                    del self.active_streams[id(processor)]
        
        # Create and return streaming response
        return StreamingResponse(
            stream_generator(),
            media_type=config.content_type,
            headers=config.get_headers(),
        )
    
    def create_json_response(
        self,
        source: AsyncIterable[Any],
        config: Optional[StreamingConfig] = None,
        progress_parent_id: Optional[str] = None,
        progress_name: str = "Streaming JSON",
    ) -> StreamingResponse:
        """Create a JSON streaming response.
        
        Args:
            source: Async iterable source of data (serialized to JSON)
            config: Streaming configuration (defaults to JSON format)
            progress_parent_id: Parent ID for progress tracking
            progress_name: Name for progress tracking
            
        Returns:
            FastAPI StreamingResponse
        """
        # Create default config if not provided
        if config is None:
            config = StreamingConfig(format=StreamFormat.JSON)
        
        # Create progress adapter if tracking enabled
        progress_adapter = None
        if self.progress_tracker and progress_parent_id:
            progress_adapter = StreamProgressAdapter(
                progress_tracker=self.progress_tracker,
                parent_id=progress_parent_id,
                name=progress_name,
                description="Streaming JSON response",
                type=ProgressItemType.OPERATION,
            )
        
        # Create processor and start streaming
        processor = StreamProcessor[Any](config, progress_adapter)
        self.active_streams[id(processor)] = processor
        
        async def stream_generator():
            try:
                async for chunk in processor.process_stream(source):
                    yield chunk
            finally:
                # Clean up when streaming is done
                if id(processor) in self.active_streams:
                    del self.active_streams[id(processor)]
        
        # Create and return streaming response
        return StreamingResponse(
            stream_generator(),
            media_type=config.content_type,
            headers=config.get_headers(),
        )
    
    def create_binary_response(
        self,
        source: AsyncIterable[bytes],
        config: Optional[StreamingConfig] = None,
        progress_parent_id: Optional[str] = None,
        progress_name: str = "Streaming binary",
    ) -> StreamingResponse:
        """Create a binary streaming response.
        
        Args:
            source: Async iterable source of binary data
            config: Streaming configuration (defaults to binary format)
            progress_parent_id: Parent ID for progress tracking
            progress_name: Name for progress tracking
            
        Returns:
            FastAPI StreamingResponse
        """
        # Create default config if not provided
        if config is None:
            config = StreamingConfig(format=StreamFormat.BINARY)
        
        # Create progress adapter if tracking enabled
        progress_adapter = None
        if self.progress_tracker and progress_parent_id:
            progress_adapter = StreamProgressAdapter(
                progress_tracker=self.progress_tracker,
                parent_id=progress_parent_id,
                name=progress_name,
                description="Streaming binary response",
                type=ProgressItemType.OPERATION,
            )
        
        # Create processor and start streaming
        processor = StreamProcessor[bytes](config, progress_adapter)
        self.active_streams[id(processor)] = processor
        
        async def stream_generator():
            try:
                async for chunk in processor.process_stream(source):
                    yield chunk
            finally:
                # Clean up when streaming is done
                if id(processor) in self.active_streams:
                    del self.active_streams[id(processor)]
        
        # Create and return streaming response
        return StreamingResponse(
            stream_generator(),
            media_type=config.content_type,
            headers=config.get_headers(),
        )
    
    def create_sse_response(
        self,
        source: AsyncIterable[Any],
        config: Optional[StreamingConfig] = None,
        event_type: str = "message",
        progress_parent_id: Optional[str] = None,
        progress_name: str = "Streaming SSE",
    ) -> EventSourceResponse:
        """Create a Server-Sent Events (SSE) streaming response.
        
        Args:
            source: Async iterable source of data
            config: Streaming configuration (defaults to SSE format)
            event_type: Event type for SSE events
            progress_parent_id: Parent ID for progress tracking
            progress_name: Name for progress tracking
            
        Returns:
            SSE streaming response
        """
        # Create default config if not provided
        if config is None:
            config = StreamingConfig(format=StreamFormat.SSE)
        
        # Create progress adapter if tracking enabled
        progress_adapter = None
        if self.progress_tracker and progress_parent_id:
            progress_adapter = StreamProgressAdapter(
                progress_tracker=self.progress_tracker,
                parent_id=progress_parent_id,
                name=progress_name,
                description="Streaming SSE response",
                type=ProgressItemType.OPERATION,
            )
        
        # Create processor
        processor = StreamProcessor[Any](config, progress_adapter)
        self.active_streams[id(processor)] = processor
        
        async def stream_generator():
            try:
                # Send initial event
                yield {
                    "event": "started",
                    "data": "Stream started",
                    "id": 0
                }
                
                event_id = 1
                async for item in source:
                    if isinstance(item, dict):
                        data = item
                    elif hasattr(item, 'to_dict') and callable(item.to_dict):
                        data = item.to_dict()
                    else:
                        # Convert item to string if it's not a dict
                        data = {"data": str(item)}
                    
                    # Add event type and ID
                    yield {
                        "event": event_type,
                        "data": data,
                        "id": event_id
                    }
                    
                    event_id += 1
                    
                    # Update progress if adapter exists
                    if progress_adapter:
                        progress = (event_id / 100) * 100  # Simple progress calculation
                        await progress_adapter.update(min(progress, 99))
                
                # Mark progress as complete
                if progress_adapter:
                    await progress_adapter.complete()
                
                # Send completion event
                yield {
                    "event": "complete",
                    "data": "Stream complete",
                    "id": event_id
                }
                
            except Exception as e:
                logger.error(f"Error in SSE stream: {str(e)}")
                
                # Mark progress as failed
                if progress_adapter:
                    await progress_adapter.fail(str(e))
                
                # Send error event
                yield {
                    "event": "error",
                    "data": {"error": str(e)},
                    "id": -1
                }
                
            finally:
                # Clean up when streaming is done
                if id(processor) in self.active_streams:
                    del self.active_streams[id(processor)]
        
        # Create and return SSE response
        return EventSourceResponse(
            stream_generator(),
            media_type=config.content_type,
            headers=config.get_headers(),
        )
    
    async def stream_to_websocket(
        self,
        websocket: WebSocket,
        source: AsyncIterable[Any],
        format: StreamFormat = StreamFormat.JSON,
        progress_parent_id: Optional[str] = None,
        progress_name: str = "WebSocket stream",
    ):
        """Stream data to a WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            source: Async iterable source of data
            format: Format to use for the stream
            progress_parent_id: Parent ID for progress tracking
            progress_name: Name for progress tracking
        """
        # Create progress adapter if tracking enabled
        progress_adapter = None
        if self.progress_tracker and progress_parent_id:
            progress_adapter = StreamProgressAdapter(
                progress_tracker=self.progress_tracker,
                parent_id=progress_parent_id,
                name=progress_name,
                description="Streaming to WebSocket",
                type=ProgressItemType.OPERATION,
            )
        
        config = StreamingConfig(format=format)
        processor = StreamProcessor[Any](config, progress_adapter)
        self.active_streams[id(processor)] = processor
        
        try:
            # Accept the WebSocket connection
            await websocket.accept()
            
            # Send initial message
            await websocket.send_json({
                "event": "started",
                "message": "Stream started"
            })
            
            # Initialize progress tracking
            if progress_adapter:
                await progress_adapter.initialize()
            
            # Process each item in the source
            item_count = 0
            async for item in source:
                item_count += 1
                
                # Format based on type and specified format
                if format == StreamFormat.JSON:
                    if isinstance(item, dict):
                        await websocket.send_json(item)
                    else:
                        try:
                            # Try to convert to dict if possible
                            if hasattr(item, 'to_dict') and callable(item.to_dict):
                                await websocket.send_json(item.to_dict())
                            else:
                                await websocket.send_json({"data": str(item)})
                        except Exception as e:
                            await websocket.send_json({
                                "event": "error",
                                "error": f"Failed to serialize item: {str(e)}"
                            })
                elif format == StreamFormat.TEXT:
                    await websocket.send_text(str(item))
                elif format == StreamFormat.BINARY:
                    if isinstance(item, bytes):
                        await websocket.send_bytes(item)
                    else:
                        # Convert to bytes
                        await websocket.send_bytes(str(item).encode('utf-8'))
                
                # Update progress if adapter exists
                if progress_adapter:
                    # Simple progress calculation - will be refined in real implementation
                    progress = min(item_count, 99)
                    await progress_adapter.update(progress)
            
            # Mark progress as complete
            if progress_adapter:
                await progress_adapter.complete()
            
            # Send completion message
            await websocket.send_json({
                "event": "complete",
                "message": "Stream complete"
            })
            
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
            if progress_adapter:
                await progress_adapter.fail("WebSocket disconnected")
                
        except Exception as e:
            logger.error(f"Error in WebSocket stream: {str(e)}")
            
            # Try to send error message if connection is still open
            try:
                await websocket.send_json({
                    "event": "error",
                    "error": str(e)
                })
            except:
                pass
                
            # Mark progress as failed
            if progress_adapter:
                await progress_adapter.fail(str(e))
                
        finally:
            # Clean up
            if id(processor) in self.active_streams:
                del self.active_streams[id(processor)]
    
    def cancel_stream(self, stream_id: Any) -> bool:
        """Cancel an active stream.
        
        Args:
            stream_id: ID of the stream to cancel
            
        Returns:
            True if stream was found and cancelled, False otherwise
        """
        if stream_id in self.active_streams:
            processor = self.active_streams[stream_id]
            processor.cancel()
            return True
        return False
    
    async def get_active_streams_info(self) -> List[Dict[str, Any]]:
        """Get information about all active streams.
        
        Returns:
            List of dictionaries with stream information
        """
        return [
            {
                "id": stream_id,
                "format": processor.config.format,
                "started": processor.is_started,
                "completed": processor.is_completed,
                "cancelled": processor.is_cancelled,
                "items_processed": processor.total_processed,
                "error": processor.error,
            }
            for stream_id, processor in self.active_streams.items()
        ]


# Create a global instance for convenience
streaming_service = None


def init_streaming_service(progress_tracker_instance=None):
    """Initialize the global streaming service.
    
    Args:
        progress_tracker_instance: Optional progress tracker instance
        
    Returns:
        The initialized streaming service
    """
    global streaming_service
    
    if streaming_service is None:
        streaming_service = StreamingService(progress_tracker_instance)
        
    return streaming_service


# Context manager for streaming
class stream_response:
    """Context manager for creating streaming responses.
    
    Usage:
    ```python
    @app.get("/stream")
    async def stream_endpoint():
        async def generator():
            for i in range(10):
                yield f"Chunk {i}\n"
                await asyncio.sleep(0.5)
        
        with stream_response(generator(), "text/plain") as response:
            return response
    ```
    """
    
    def __init__(
        self,
        source: AsyncIterable[Any],
        content_type: Optional[str] = None,
        format: StreamFormat = StreamFormat.TEXT,
        progress_parent_id: Optional[str] = None,
        progress_name: str = "Streaming response",
    ):
        """Initialize streaming response context.
        
        Args:
            source: Async iterable source of data
            content_type: Content type (auto-detected if None)
            format: Format of the stream
            progress_parent_id: Parent ID for progress tracking
            progress_name: Name for progress tracking
        """
        self.source = source
        self.content_type = content_type
        self.format = format
        self.progress_parent_id = progress_parent_id
        self.progress_name = progress_name
        self.response = None
        
        # Ensure streaming service is initialized
        global streaming_service
        if streaming_service is None:
            from core.progress_tracker import progress_tracker
            streaming_service = init_streaming_service(progress_tracker)
        
        self.service = streaming_service
    
    def __enter__(self) -> Response:
        """Enter the context manager and create response.
        
        Returns:
            Streaming response
        """
        config = StreamingConfig(
            format=self.format,
            content_type=self.content_type,
        )
        
        # Create appropriate response type
        if self.format == StreamFormat.TEXT:
            self.response = self.service.create_text_response(
                self.source,
                config,
                self.progress_parent_id,
                self.progress_name,
            )
        elif self.format == StreamFormat.JSON:
            self.response = self.service.create_json_response(
                self.source,
                config,
                self.progress_parent_id,
                self.progress_name,
            )
        elif self.format == StreamFormat.BINARY:
            self.response = self.service.create_binary_response(
                self.source,
                config,
                self.progress_parent_id,
                self.progress_name,
            )
        elif self.format == StreamFormat.SSE:
            self.response = self.service.create_sse_response(
                self.source,
                config,
                "message",
                self.progress_parent_id,
                self.progress_name,
            )
        else:
            raise ValueError(f"Unsupported stream format: {self.format}")
            
        return self.response
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        # No cleanup needed for StreamingResponse
        pass


# Async generators for common streaming patterns
async def stream_list(items: List[Any], delay: float = 0.1) -> AsyncGenerator[Any, None]:
    """Stream items from a list with optional delay.
    
    Args:
        items: List of items to stream
        delay: Delay between items in seconds
        
    Yields:
        Items from the list
    """
    for item in items:
        yield item
        if delay > 0:
            await asyncio.sleep(delay)


async def stream_chunks(
    text: str,
    chunk_size: int = 10,
    delay: float = 0.05
) -> AsyncGenerator[str, None]:
    """Stream a text as chunks with optional delay.
    
    Args:
        text: Text to stream
        chunk_size: Size of each chunk in characters
        delay: Delay between chunks in seconds
        
    Yields:
        Text chunks
    """
    for i in range(0, len(text), chunk_size):
        yield text[i:i+chunk_size]
        if delay > 0:
            await asyncio.sleep(delay)