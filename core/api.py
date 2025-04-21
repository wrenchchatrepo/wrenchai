# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import logging
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import time

from core.agent_system import AgentManager
from core.bayesian_engine import BayesianEngine
from core.tool_system import ToolRegistry
from core.config_loader import load_config, load_configs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="Wrenchai Multi-Agent Framework API")

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

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok", 
        "components": {
            "agent_manager": agent_manager is not None,
            "bayesian_engine": bayesian_engine is not None,
            "tool_registry": tool_registry is not None
        }
    }

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

@app.websocket("/ws/agent/{agent_id}")
async def agent_websocket(websocket: WebSocket, agent_id: str):
    """WebSocket endpoint for real-time agent communication"""
    await websocket.accept()
    try:
        if agent_id not in agent_manager.agents:
            await websocket.send_json({"error": f"Agent {agent_id} not found"})
            await websocket.close()
            return
            
        agent = agent_manager.agents[agent_id]
        
        while True:
            data = await websocket.receive_json()
            # Process the message through the agent
            result = await agent.process(data)
            await websocket.send_json(result)
    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected for agent {agent_id}")
    except Exception as e:
        logging.error(f"Error in agent websocket: {e}")
        await websocket.send_json({"error": str(e)})
    finally:
        try:
            await websocket.close()
        except:
            pass

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