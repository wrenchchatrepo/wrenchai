# API and WebSocket Services

## Overview

This module provides a comprehensive set of services for communicating with the WrenchAI backend API and WebSocket server, handling authentication, request retry logic, and real-time updates for playbook executions.

## Key Components

### HTTP API Services

- **ApiClient**: Base client for communicating with the API, providing methods for HTTP requests with retry logic and authentication.
- **ResourceClient**: Generic client for interacting with specific API resources, implementing CRUD operations.
- **PlaybookService**: Service for playbook-related operations like listing, creating, updating, and executing playbooks.
- **ExecutionService**: Service for execution-related operations like monitoring, retrieving logs, and canceling executions.

### WebSocket Services

- **WebSocketClient**: Client for real-time communication with the backend via WebSockets, with reconnection and subscription capabilities.
- **WebSocketEvent**: Event object for WebSocket events (connected, disconnected, message, etc.).
- **WebSocketEventType**: Enum for WebSocket event types.

### Factory Functions

- **create_api_client**: Creates an API client with the appropriate configuration.
- **initialize_api_client**: Initializes an API client and checks the connection.
- **create_websocket_client**: Creates a WebSocket client with the appropriate configuration.

### WebSocket Subscriptions

- **subscribe_to_execution**: Subscribes to updates for a specific execution.
- **subscribe_to_playbook**: Subscribes to updates for a specific playbook.
- **subscribe_to_executions**: Subscribes to all execution updates.
- **subscribe_to_playbooks**: Subscribes to all playbook updates.

## Usage Examples

### Creating an API Client

```python
from streamlit_app.services import create_api_client

# Create a new API client
api_client = create_api_client()

# Make a request
async def get_api_info():
    response = await api_client.get("info")
    return response.json()
```

### Creating a WebSocket Client and Subscribing to Updates

```python
import asyncio
from streamlit_app.services import create_websocket_client, subscribe_to_execution

# Define a message handler
async def handle_message(message):
    print(f"Received message: {message}")

# Create a WebSocket client
ws_client = await create_websocket_client(on_message=handle_message)

# Subscribe to execution updates
await subscribe_to_execution(ws_client, "execution_id_123")

# Keep connection alive
await asyncio.sleep(60)  # Run for 60 seconds
await ws_client.disconnect()
```

### Using the Playbook Service

```python
from streamlit_app.services import create_api_client
from streamlit_app.services.playbook_service import PlaybookService

async def list_all_playbooks():
    api_client = create_api_client()
    playbook_service = PlaybookService(api_client)
    playbooks = await playbook_service.list_playbooks()
    return playbooks

async def execute_playbook(playbook_id, parameters):
    api_client = create_api_client()
    playbook_service = PlaybookService(api_client)
    result = await playbook_service.execute_playbook(playbook_id, parameters)
    return result
```

### Monitoring Execution Status

```python
from streamlit_app.services import create_api_client
from streamlit_app.services.execution_service import ExecutionService

async def monitor_execution(execution_id):
    api_client = create_api_client()
    execution_service = ExecutionService(api_client)
    
    def status_callback(execution):
        print(f"Execution status: {execution.state}")
    
    final_result = await execution_service.watch_execution(
        execution_id=execution_id,
        callback=status_callback,
        interval_seconds=1.0
    )
    
    return final_result
```

## Error Handling

All services provide comprehensive error handling:

- `ApiError`: Raised for API-related errors with status code and response details
- Automatic retry logic for transient failures
- Logging and diagnostic information for debugging

## Authentication

Services automatically handle authentication using the configured API token:

- HTTP API requests include the token in the Authorization header
- WebSocket connections include the token in the connection URL
- Authentication status and errors are tracked in the API connection state

## Connection State Management

The services maintain connection state information in the Streamlit session state:

- API connection status, latency, and error information
- WebSocket connection status and event history
- API features and capabilities

## Advanced Features

### Retry Logic

The API client includes advanced retry logic:

- Configurable maximum retries, initial delay, and backoff multiplier
- Exponential backoff for successive retry attempts
- Special handling for rate limiting (429) responses

### Real-time Updates

The WebSocket client provides real-time updates:

- Automatic reconnection on connection loss
- Subscription management for specific topics
- Event tracking for connection, messages, and errors

### Resource-specific Clients

Resource clients provide type-safe interfaces for specific API resources:

- Automatic conversion between API responses and model objects
- CRUD operations (create, read, update, delete)
- Resource-specific validation and error handling