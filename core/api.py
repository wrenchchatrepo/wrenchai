# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import logging
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks, Depends, status
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import time
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta

from core.agent_system import AgentManager
from core.bayesian_engine import BayesianEngine
from core.tool_system import ToolRegistry
from core.config_loader import load_config, load_configs
from core.agents.super_agent import SuperAgent, TaskRequest
from core.agents.inspector_agent import InspectorAgent
from core.agents.journey_agent import JourneyAgent, JourneyStep
from core.tools.secrets_manager import secrets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="WrenchAI API",
    description="Multi-Agent Framework API",
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

# Initialize systems
CONFIG_DIR = os.getenv("CONFIG_DIR", "core/configs")
system_config = None
agent_manager = None
tool_registry = None
bayesian_engine = None

# Initialize agents
super_agent = SuperAgent()
inspector_agent = InspectorAgent()
journey_agent = JourneyAgent()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, client_id: str):
        self.active_connections[client_id].remove(websocket)
        if not self.active_connections[client_id]:
            del self.active_connections[client_id]

    async def broadcast(self, message: Dict[str, Any], client_id: str):
        if client_id in self.active_connections:
            for connection in self.active_connections[client_id]:
                await connection.send_json(message)

manager = ConnectionManager()

# OAuth2 configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_agent_id(agent):
    """Get a string identifier for an agent"""
    return str(id(agent))

@app.on_event("startup")
async def startup_event():
    """Initialize the system on startup"""
    global system_config, agent_manager, tool_registry, bayesian_engine
    
    try:
        # Load configurations
        system_config = load_configs(CONFIG_DIR)
        logging.info("Loaded system configuration")
        
        # Initialize components
        bayesian_engine = BayesianEngine()
        logging.info("Initialized Bayesian engine")
        
        tool_registry = ToolRegistry(os.path.join(CONFIG_DIR, "tools.yaml"))
        logging.info("Initialized tool registry")
        
        agent_manager = AgentManager(CONFIG_DIR)
        agent_manager.set_tool_registry(tool_registry)
        agent_manager.set_bayesian_engine(bayesian_engine)
        logging.info("Initialized agent manager")
        
        # Register bayesian_tools with the bayesian engine
        from core.tools import bayesian_tools
        bayesian_tools.set_bayesian_engine(bayesian_engine)
        logging.info("Registered Bayesian engine with tools")
        
    except Exception as e:
        logging.error(f"Error initializing system: {e}")
        raise

@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, Any]:
    """Check system health status."""
    try:
        # Implement health checks
        checks = {
            "database": True,  # Replace with actual DB check
            "cache": True,     # Replace with actual cache check
            "agents": {
                "super_agent": isinstance(super_agent, SuperAgent),
                "inspector_agent": isinstance(inspector_agent, InspectorAgent),
                "journey_agent": isinstance(journey_agent, JourneyAgent)
            }
        }
        
        return {
            "status": "healthy" if all(checks.values()) else "unhealthy",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )

@app.post("/api/agents/create")
async def create_agent(data: Dict[str, Any]):
    """Create a new agent with a specific role"""
    try:
        if 'role' not in data:
            raise HTTPException(status_code=400, detail="Missing 'role' field")
            
        agent = agent_manager.initialize_agent(data['role'])
        agent_id = get_agent_id(agent)
        
        # Assign tools if specified
        if 'tools' in data and isinstance(data['tools'], list):
            agent_manager.assign_tools_to_agent(agent_id, data['tools'])
        
        return {"status": "success", "agent_id": agent_id}
    except Exception as e:
        logging.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/{agent_id}/process")
async def process_with_agent(agent_id: str, data: Dict[str, Any]):
    """Process input with a specific agent"""
    try:
        if agent_id not in agent_manager.agents:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
            
        agent = agent_manager.agents[agent_id]
        result = await agent.process(data)
        
        return {"status": "success", "result": result}
    except Exception as e:
        logging.error(f"Error processing with agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/playbooks/run")
async def run_playbook(data: Dict[str, Any], background_tasks: BackgroundTasks):
    """Run a playbook with input data"""
    try:
        if 'playbook' not in data:
            raise HTTPException(status_code=400, detail="Missing 'playbook' field")
        if 'input' not in data:
            raise HTTPException(status_code=400, detail="Missing 'input' field")
            
        # Generate a unique run ID
        run_id = f"run_{int(time.time())}"
        
        # Start workflow in background
        background_tasks.add_task(
            execute_workflow_and_log, 
            run_id=run_id,
            playbook_name=data['playbook'], 
            input_data=data['input']
        )
        
        return {"status": "started", "run_id": run_id}
    except Exception as e:
        logging.error(f"Error running playbook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/playbooks/status/{run_id}")
async def get_playbook_status(run_id: str):
    """Get the status of a playbook run"""
    # In a real implementation, this would check a database or cache
    # For now, we'll return a placeholder
    return {"status": "running", "run_id": run_id}

@app.post("/api/reasoning/models/create")
async def create_belief_model(data: Dict[str, Any]):
    """Create a new belief model in the Bayesian engine"""
    try:
        if 'model_name' not in data:
            raise HTTPException(status_code=400, detail="Missing 'model_name' field")
        if 'variables' not in data or not isinstance(data['variables'], dict):
            raise HTTPException(status_code=400, detail="Missing or invalid 'variables' field")
            
        bayesian_engine.create_model(data['model_name'], data['variables'])
        
        return {"status": "success", "model": data['model_name']}
    except Exception as e:
        logging.error(f"Error creating belief model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reasoning/update")
async def update_beliefs(data: Dict[str, Any]):
    """Update beliefs in the Bayesian model"""
    try:
        if 'model' not in data:
            raise HTTPException(status_code=400, detail="Missing 'model' field")
        if 'evidence' not in data or not isinstance(data['evidence'], dict):
            raise HTTPException(status_code=400, detail="Missing or invalid 'evidence' field")
            
        # Optional sampling parameters
        sample_kwargs = data.get('sample_kwargs', {})
        
        updated_beliefs = bayesian_engine.update_beliefs(
            data['model'], data['evidence'], sample_kwargs
        )
        
        return {"status": "success", "beliefs": updated_beliefs}
    except Exception as e:
        logging.error(f"Error updating beliefs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reasoning/decide")
async def make_decision(data: Dict[str, Any]):
    """Make a decision based on current beliefs"""
    try:
        if 'model' not in data:
            raise HTTPException(status_code=400, detail="Missing 'model' field")
        if 'options' not in data or not isinstance(data['options'], list):
            raise HTTPException(status_code=400, detail="Missing or invalid 'options' field")
        if 'utility_function' not in data:
            raise HTTPException(status_code=400, detail="Missing 'utility_function' field")
            
        # Convert utility function from string to callable
        # WARNING: This is unsafe in production - use a safer approach
        utility_function = eval(data['utility_function'])
        
        best_option, utility = bayesian_engine.make_decision(
            data['model'], data['options'], utility_function
        )
        
        return {
            "status": "success", 
            "decision": best_option,
            "expected_utility": utility
        }
    except Exception as e:
        logging.error(f"Error making decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tools/list")
async def list_tools():
    """List all available tools"""
    try:
        tools = tool_registry.list_tools()
        return {"status": "success", "tools": tools}
    except Exception as e:
        logging.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast({
                "client_id": client_id,
                "message": data,
                "timestamp": datetime.utcnow().isoformat()
            }, client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        await manager.disconnect(websocket, client_id)

async def execute_workflow_and_log(run_id: str, playbook_name: str, input_data: Dict[str, Any]):
    """Execute a workflow and log the results"""
    try:
        # Execute the workflow
        result = await agent_manager.run_workflow(playbook_name, input_data)
        
        # In a real implementation, store the result in a database
        logging.info(f"Workflow {run_id} ({playbook_name}) completed successfully")
        
        # For now, just log the result
        logging.info(f"Workflow result: {json.dumps(result)[:1000]}...")
        
        return result
    except Exception as e:
        logging.error(f"Error executing workflow {run_id}: {e}")
        # In a real implementation, update status in database
        raise

# Task endpoints
@app.post("/tasks", tags=["Tasks"])
async def create_task(task: TaskRequest) -> Dict[str, Any]:
    """Create and start a new task."""
    try:
        result = await super_agent.orchestrate_task(task)
        return result
    except Exception as e:
        logger.error(f"Task creation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task creation failed: {str(e)}"
        )

@app.get("/tasks/{task_id}", tags=["Tasks"])
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get status of a specific task."""
    try:
        # Implement task status retrieval
        return {
            "task_id": task_id,
            "status": "running",  # Replace with actual status
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get task status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )

# Journey endpoints
@app.post("/journeys", tags=["Journeys"])
async def create_journey(
    steps: List[JourneyStep],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Create and execute a new journey."""
    try:
        result = await journey_agent.execute_journey(steps, context)
        return result
    except Exception as e:
        logger.error(f"Journey creation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Journey creation failed: {str(e)}"
        )

@app.get("/journeys/{journey_id}", tags=["Journeys"])
async def get_journey_status(journey_id: str) -> Dict[str, Any]:
    """Get status of a specific journey."""
    try:
        if journey_id not in journey_agent.active_journeys:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journey not found"
            )
        return journey_agent.active_journeys[journey_id]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get journey status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get journey status: {str(e)}"
        )

# Monitoring endpoints
@app.get("/monitor/{task_id}", tags=["Monitoring"])
async def monitor_task(task_id: str) -> Dict[str, Any]:
    """Monitor a specific task."""
    try:
        execution_data = {
            "task_id": task_id,
            "metrics": {
                "success_rate": "95%",
                "duration": "00:05:23"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        result = await inspector_agent.monitor_execution(task_id, execution_data)
        return result
    except Exception as e:
        logger.error(f"Task monitoring failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task monitoring failed: {str(e)}"
        )

# Authentication endpoint
@app.post("/token", tags=["Auth"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Dict[str, str]:
    """Authenticate user and generate access token."""
    try:
        # Implement actual authentication logic
        if form_data.username == "test" and form_data.password == "test":
            return {
                "access_token": "dummy_token",
                "token_type": "bearer"
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    try:
        logger.info("Cleaning up API resources...")
        # Cleanup any resources here
    except Exception as e:
        logger.error(f"Shutdown cleanup failed: {str(e)}")
        raise