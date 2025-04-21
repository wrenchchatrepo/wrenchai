# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import sys
import logging
import asyncio
import json
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import argparse
import datetime
import uuid

# Check for web dependencies
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    logging.warning("fastapi and uvicorn are required for the chat app")

# Check for database dependency
try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False
    logging.warning("aiosqlite is required for chat message storage")

# Check for Pydantic AI
try:
    from pydantic_ai import Agent
    HAS_PYDANTIC_AI = True
except ImportError:
    HAS_PYDANTIC_AI = False
    logging.warning("pydantic-ai is required for the chat app")

class ChatManager:
    """Manager for chat messages and sessions"""
    
    def __init__(self, db_path: str = "chat_messages.db"):
        """Initialize the chat manager
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.db = None
        self.connected = False
        self._check_requirements()
    
    def _check_requirements(self):
        """Check if all required dependencies are installed"""
        if not HAS_PYDANTIC_AI:
            logging.error("pydantic-ai is required for the chat app")
            raise ImportError("pydantic-ai is required for the chat app")
            
        if not HAS_AIOSQLITE:
            logging.warning("aiosqlite is required for chat message storage")
            
        if not HAS_FASTAPI:
            logging.warning("fastapi and uvicorn are required for the chat app")
    
    async def connect(self) -> bool:
        """Connect to the SQLite database
        
        Returns:
            True if connection successful, False otherwise
        """
        if not HAS_AIOSQLITE:
            logging.warning("aiosqlite is not installed. Message storage will be in-memory only.")
            self.connected = False
            return False
            
        try:
            self.db = await aiosqlite.connect(self.db_path)
            
            # Create tables if they don't exist
            await self.db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                name TEXT
            )
            """)
            
            await self.db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                role TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
            """)
            
            await self.db.commit()
            
            self.connected = True
            logging.info(f"Connected to SQLite database: {self.db_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to SQLite database: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from the SQLite database"""
        if self.db:
            await self.db.close()
            self.db = None
            self.connected = False
            logging.info("Disconnected from SQLite database")
    
    async def create_session(self, name: Optional[str] = None) -> str:
        """Create a new chat session
        
        Args:
            name: Optional session name
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        
        if self.connected:
            await self.db.execute(
                "INSERT INTO sessions (id, name) VALUES (?, ?)",
                (session_id, name or f"Chat {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
            )
            await self.db.commit()
            
        return session_id
    
    async def add_message(self, session_id: str, role: str, content: str) -> str:
        """Add a message to a session
        
        Args:
            session_id: Session ID
            role: Message role (user or assistant)
            content: Message content
            
        Returns:
            Message ID
        """
        message_id = str(uuid.uuid4())
        
        if self.connected:
            await self.db.execute(
                "INSERT INTO messages (id, session_id, role, content) VALUES (?, ?, ?, ?)",
                (message_id, session_id, role, content)
            )
            await self.db.commit()
            
        return message_id
    
    async def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a session
        
        Args:
            session_id: Session ID
            
        Returns:
            List of messages
        """
        if not self.connected:
            return []
            
        async with self.db.execute(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at
            """,
            (session_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            
        return [
            {
                "id": row[0],
                "role": row[1],
                "content": row[2],
                "created_at": row[3]
            }
            for row in rows
        ]
    
    async def get_sessions(self) -> List[Dict[str, Any]]:
        """Get all chat sessions
        
        Returns:
            List of sessions
        """
        if not self.connected:
            return []
            
        async with self.db.execute(
            """
            SELECT id, name, created_at
            FROM sessions
            ORDER BY created_at DESC
            """
        ) as cursor:
            rows = await cursor.fetchall()
            
        return [
            {
                "id": row[0],
                "name": row[1],
                "created_at": row[2]
            }
            for row in rows
        ]

class ChatApp:
    """Chat application with FastAPI"""
    
    def __init__(self, 
                model: str = "openai:gpt-4-turbo",
                host: str = "127.0.0.1",
                port: int = 8000,
                db_path: str = "chat_messages.db"):
        """Initialize the chat application
        
        Args:
            model: AI model to use
            host: Host to bind the server to
            port: Port to bind the server to
            db_path: Path to the SQLite database file
        """
        if not HAS_FASTAPI:
            logging.error("fastapi and uvicorn are required for the chat app")
            raise ImportError("fastapi and uvicorn are required for the chat app")
            
        self.model = model
        self.host = host
        self.port = port
        
        # Create FastAPI app
        self.app = FastAPI(title="Wrenchai Chat App")
        
        # Create chat manager
        self.chat_manager = ChatManager(db_path)
        
        # Set up routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up FastAPI routes"""
        # Create templates directory
        templates_dir = Path(__file__).parent / "templates"
        templates_dir.mkdir(exist_ok=True)
        
        # Create static directory
        static_dir = Path(__file__).parent / "static"
        static_dir.mkdir(exist_ok=True)
        
        # Create templates
        self.templates = Jinja2Templates(directory=str(templates_dir))
        
        # Create HTML template file if it doesn't exist
        self._create_template_file(templates_dir / "chat.html")
        
        # Create CSS file if it doesn't exist
        self._create_css_file(static_dir / "style.css")
        
        # Create JavaScript file if it doesn't exist
        self._create_js_file(static_dir / "chat.js")
        
        # Serve static files
        self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        
        # Define routes
        @self.app.get("/", response_class=HTMLResponse)
        async def get_chat_page(request: Request):
            return self.templates.TemplateResponse(
                "chat.html", 
                {"request": request, "model": self.model}
            )
        
        @self.app.get("/api/sessions")
        async def get_sessions():
            sessions = await self.chat_manager.get_sessions()
            return {"sessions": sessions}
        
        @self.app.post("/api/sessions")
        async def create_session(data: Dict[str, Any]):
            session_id = await self.chat_manager.create_session(data.get("name"))
            return {"session_id": session_id}
        
        @self.app.get("/api/sessions/{session_id}/messages")
        async def get_session_messages(session_id: str):
            messages = await self.chat_manager.get_session_messages(session_id)
            return {"messages": messages}
        
        @self.app.websocket("/ws/chat/{session_id}")
        async def chat_websocket(websocket: WebSocket, session_id: str):
            await websocket.accept()
            
            try:
                # Create agent
                agent = Agent(
                    self.model,
                    instructions="""
                    You are a helpful assistant in a chat application.
                    Provide concise, accurate, and helpful responses.
                    Format your responses using markdown for better readability.
                    """
                )
                
                # Get existing messages for this session
                messages = await self.chat_manager.get_session_messages(session_id)
                
                # Convert to format expected by agent
                history = [
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in messages
                ]
                
                while True:
                    # Receive message from client
                    data = await websocket.receive_json()
                    user_message = data["message"]
                    
                    # Store user message
                    await self.chat_manager.add_message(session_id, "user", user_message)
                    
                    # Add to history
                    history.append({"role": "user", "content": user_message})
                    
                    # Send initial response to indicate the assistant is thinking
                    await websocket.send_json({
                        "type": "thinking",
                        "message": "Thinking..."
                    })
                    
                    # Generate streaming response
                    response_text = ""
                    async for chunk in agent.run_stream(user_message, message_history=history):
                        response_text += chunk.delta
                        await websocket.send_json({
                            "type": "stream",
                            "message": response_text
                        })
                    
                    # Store assistant response
                    await self.chat_manager.add_message(session_id, "assistant", response_text)
                    
                    # Add to history
                    history.append({"role": "assistant", "content": response_text})
                    
                    # Send final message
                    await websocket.send_json({
                        "type": "complete",
                        "message": response_text
                    })
            except WebSocketDisconnect:
                logging.info(f"WebSocket disconnected for session {session_id}")
            except Exception as e:
                logging.error(f"Error in chat websocket: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                
    def _create_template_file(self, path: Path):
        """Create the HTML template file if it doesn't exist
        
        Args:
            path: Path to the template file
        """
        if not path.exists():
            html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wrenchai Chat</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11.7.0/styles/github.min.css">
    <link rel="stylesheet" href="/static/style.css">
    <script src="https://cdn.jsdelivr.net/npm/marked@4.0.2/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.7.0/lib/highlight.min.js"></script>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <!-- Sidebar with sessions -->
            <div class="col-md-3 sidebar">
                <div class="p-3">
                    <h3>Wrenchai Chat</h3>
                    <p class="text-muted">Using model: {{ model }}</p>
                    <hr/>
                    
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5>Sessions</h5>
                        <button id="new-session-btn" class="btn btn-sm btn-primary">
                            <i class="bi bi-plus-circle"></i> New
                        </button>
                    </div>
                    
                    <div id="sessions-list" class="list-group">
                        <!-- Sessions will be inserted here -->
                    </div>
                </div>
            </div>
            
            <!-- Main chat area -->
            <div class="col-md-9 main-content">
                <div id="chat-container">
                    <div id="chat-messages">
                        <!-- Messages will be inserted here -->
                    </div>
                    
                    <div id="chat-input-container" class="p-3">
                        <form id="chat-form" class="d-flex">
                            <textarea id="message-input" class="form-control" placeholder="Type your message here..." rows="2"></textarea>
                            <button type="submit" class="btn btn-primary ms-2">
                                <i class="bi bi-send"></i>
                            </button>
                        </form>
                    </div>
                </div>
                
                <!-- Empty state -->
                <div id="empty-state" class="d-flex justify-content-center align-items-center">
                    <div class="text-center">
                        <h3>Welcome to Wrenchai Chat</h3>
                        <p class="text-muted">Select an existing session or create a new one to start chatting</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="/static/chat.js"></script>
</body>
</html>
"""
            path.write_text(html_content)
            logging.info(f"Created HTML template file: {path}")
    
    def _create_css_file(self, path: Path):
        """Create the CSS file if it doesn't exist
        
        Args:
            path: Path to the CSS file
        """
        if not path.exists():
            css_content = """body {
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.container-fluid {
    height: 100%;
    padding: 0;
}

.row {
    height: 100%;
    margin: 0;
}

.sidebar {
    background-color: #f8f9fa;
    height: 100%;
    overflow-y: auto;
    border-right: 1px solid #dee2e6;
}

.main-content {
    height: 100%;
    display: flex;
    flex-direction: column;
    padding: 0;
}

#chat-container {
    display: none;
    flex-direction: column;
    height: 100%;
}

#chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
}

#chat-input-container {
    border-top: 1px solid #dee2e6;
    background-color: #fff;
}

#message-input {
    resize: none;
}

.message {
    margin-bottom: 15px;
    max-width: 80%;
}

.user-message {
    margin-left: auto;
    background-color: #007bff;
    color: white;
    border-radius: 15px 15px 0 15px;
    padding: 10px 15px;
}

.assistant-message {
    margin-right: auto;
    background-color: #f0f0f0;
    border-radius: 15px 15px 15px 0;
    padding: 10px 15px;
}

.assistant-message-content {
    overflow-x: auto;
}

.assistant-message-content pre {
    background-color: #f8f9fa;
    padding: 10px;
    border-radius: 5px;
    margin: 10px 0;
}

.assistant-message-content code {
    font-family: 'Courier New', Courier, monospace;
}

.thinking {
    margin-right: auto;
    background-color: #f0f0f0;
    border-radius: 15px 15px 15px 0;
    padding: 10px 15px;
    font-style: italic;
    color: #6c757d;
}

#empty-state {
    height: 100%;
}

.session-item {
    cursor: pointer;
}

.session-item.active {
    background-color: #007bff;
    color: white;
}
"""
            path.write_text(css_content)
            logging.info(f"Created CSS file: {path}")
    
    def _create_js_file(self, path: Path):
        """Create the JavaScript file if it doesn't exist
        
        Args:
            path: Path to the JavaScript file
        """
        if not path.exists():
            js_content = """// DOM Elements
const sessionsList = document.getElementById('sessions-list');
const newSessionBtn = document.getElementById('new-session-btn');
const chatContainer = document.getElementById('chat-container');
const emptySate = document.getElementById('empty-state');
const chatMessages = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');

// State
let currentSessionId = null;
let socket = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadSessions();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    // New session button
    newSessionBtn.addEventListener('click', createNewSession);
    
    // Chat form submission
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        sendMessage();
    });
    
    // Handle keyboard shortcuts
    messageInput.addEventListener('keydown', (e) => {
        // Submit on Enter (without Shift)
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

// Load sessions from API
async function loadSessions() {
    try {
        const response = await fetch('/api/sessions');
        const data = await response.json();
        
        // Clear sessions list
        sessionsList.innerHTML = '';
        
        // Add sessions to the list
        if (data.sessions.length === 0) {
            sessionsList.innerHTML = '<div class="text-muted p-2">No sessions yet</div>';
        } else {
            data.sessions.forEach(session => {
                const sessionEl = document.createElement('div');
                sessionEl.className = 'list-group-item session-item';
                sessionEl.dataset.id = session.id;
                
                // Add active class if this is the current session
                if (session.id === currentSessionId) {
                    sessionEl.classList.add('active');
                }
                
                sessionEl.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div>${session.name}</div>
                        <small>${formatDate(session.created_at)}</small>
                    </div>
                `;
                
                sessionEl.addEventListener('click', () => selectSession(session.id));
                sessionsList.appendChild(sessionEl);
            });
        }
    } catch (error) {
        console.error('Error loading sessions:', error);
    }
}

// Create a new chat session
async function createNewSession() {
    try {
        const response = await fetch('/api/sessions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: `Chat ${new Date().toLocaleString()}`
            })
        });
        
        const data = await response.json();
        
        // Reload sessions and select the new one
        await loadSessions();
        selectSession(data.session_id);
    } catch (error) {
        console.error('Error creating session:', error);
    }
}

// Select a session
async function selectSession(sessionId) {
    // Close existing socket
    if (socket) {
        socket.close();
    }
    
    // Update UI
    currentSessionId = sessionId;
    
    // Update active session in the list
    const sessionItems = document.querySelectorAll('.session-item');
    sessionItems.forEach(item => {
        if (item.dataset.id === sessionId) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
    
    // Show chat container
    chatContainer.style.display = 'flex';
    emptySate.style.display = 'none';
    
    // Clear chat messages
    chatMessages.innerHTML = '';
    
    // Load session messages
    await loadSessionMessages(sessionId);
    
    // Connect websocket
    connectWebSocket(sessionId);
}

// Load messages for a session
async function loadSessionMessages(sessionId) {
    try {
        const response = await fetch(`/api/sessions/${sessionId}/messages`);
        const data = await response.json();
        
        // Add messages to the chat
        data.messages.forEach(message => {
            addMessage(message.role, message.content);
        });
        
        // Scroll to bottom
        scrollToBottom();
    } catch (error) {
        console.error('Error loading messages:', error);
    }
}

// Connect to the WebSocket
function connectWebSocket(sessionId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat/${sessionId}`;
    
    socket = new WebSocket(wsUrl);
    
    socket.onopen = () => {
        console.log('WebSocket connected');
    };
    
    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'thinking') {
            addThinkingIndicator();
        } else if (data.type === 'stream') {
            updateStreamingMessage(data.message);
        } else if (data.type === 'complete') {
            // Remove any existing thinking indicator and make sure the final message is added
            removeThinkingIndicator();
            updateStreamingMessage(data.message, true);
        } else if (data.type === 'error') {
            removeThinkingIndicator();
            addErrorMessage(data.message);
        }
    };
    
    socket.onclose = () => {
        console.log('WebSocket disconnected');
    };
    
    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

// Send a message
function sendMessage() {
    const message = messageInput.value.trim();
    
    if (message && socket && socket.readyState === WebSocket.OPEN) {
        // Add message to chat
        addMessage('user', message);
        
        // Send message through WebSocket
        socket.send(JSON.stringify({
            message: message
        }));
        
        // Clear input
        messageInput.value = '';
        
        // Scroll to bottom
        scrollToBottom();
    }
}

// Add a message to the chat
function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = role === 'user' ? 'message user-message' : 'message assistant-message';
    
    if (role === 'assistant') {
        // Render markdown for assistant messages
        messageDiv.innerHTML = `
            <div class="assistant-message-content">
                ${marked.parse(content)}
            </div>
        `;
        
        // Apply syntax highlighting
        messageDiv.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
    } else {
        messageDiv.textContent = content;
    }
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

// Add thinking indicator
function addThinkingIndicator() {
    // Remove any existing thinking indicator
    removeThinkingIndicator();
    
    // Add new thinking indicator
    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'message thinking';
    thinkingDiv.id = 'thinking-indicator';
    thinkingDiv.textContent = 'Thinking...';
    chatMessages.appendChild(thinkingDiv);
    scrollToBottom();
}

// Remove thinking indicator
function removeThinkingIndicator() {
    const thinkingIndicator = document.getElementById('thinking-indicator');
    if (thinkingIndicator) {
        thinkingIndicator.remove();
    }
    
    // Also remove any streaming message containers
    const streamingContainer = document.getElementById('streaming-message');
    if (streamingContainer) {
        streamingContainer.removeAttribute('id');
    }
}

// Update streaming message
function updateStreamingMessage(content, isComplete = false) {
    // Remove thinking indicator
    removeThinkingIndicator();
    
    // Check if we have a streaming message container
    let streamingContainer = document.getElementById('streaming-message');
    
    if (!streamingContainer) {
        // Create new message container
        streamingContainer = document.createElement('div');
        streamingContainer.className = 'message assistant-message';
        streamingContainer.id = isComplete ? '' : 'streaming-message';
        
        // Add content div
        streamingContainer.innerHTML = `
            <div class="assistant-message-content">
                ${marked.parse(content)}
            </div>
        `;
        
        chatMessages.appendChild(streamingContainer);
    } else {
        // Update existing container
        streamingContainer.innerHTML = `
            <div class="assistant-message-content">
                ${marked.parse(content)}
            </div>
        `;
        
        // Remove ID if complete
        if (isComplete) {
            streamingContainer.removeAttribute('id');
        }
    }
    
    // Apply syntax highlighting
    streamingContainer.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });
    
    scrollToBottom();
}

// Add error message
function addErrorMessage(content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant-message text-danger';
    messageDiv.textContent = `Error: ${content}`;
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

// Scroll to bottom of chat
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Format date
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString();
}
"""
            path.write_text(js_content)
            logging.info(f"Created JavaScript file: {path}")
    
    async def startup(self):
        """Start the application"""
        # Connect to database
        await self.chat_manager.connect()
    
    async def shutdown(self):
        """Shut down the application"""
        # Disconnect from database
        await self.chat_manager.disconnect()
    
    def run(self):
        """Run the application"""
        if not HAS_FASTAPI:
            logging.error("fastapi and uvicorn are required for the chat app")
            return
            
        # Set up startup and shutdown handlers
        @self.app.on_event("startup")
        async def startup_event():
            await self.startup()
            
        @self.app.on_event("shutdown")
        async def shutdown_event():
            await self.shutdown()
        
        # Run the server
        uvicorn.run(self.app, host=self.host, port=self.port)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Wrenchai Chat Application")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    parser.add_argument("--model", default="openai:gpt-4-turbo", help="Model to use")
    parser.add_argument("--db-path", default="chat_messages.db", help="Path to the SQLite database file")
    
    args = parser.parse_args()
    
    # Create chat app
    app = ChatApp(
        model=args.model,
        host=args.host,
        port=args.port,
        db_path=args.db_path
    )
    
    # Run the app
    app.run()

if __name__ == "__main__":
    main()