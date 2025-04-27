# WrenchAI MVP Implementation Plan

## Core Framework Components

### 1. Agent System Implementation

#### Current Status
- Basic agent structure implemented
- Core orchestration logic needs enhancement
- Tool allocation system needs refinement

#### Implementation Steps

1. **SuperAgent Enhancement**
```python
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from core.tools.secrets_manager import secrets

class TaskRequest(BaseModel):
    task_id: str
    description: str
    requirements: List[str]
    constraints: Optional[Dict[str, Any]] = None

class SuperAgent:
    async def orchestrate_task(self, task: TaskRequest) -> Dict[str, Any]:
        """Orchestrate task execution using available agents and tools.
        
        Args:
            task: Task request containing details and requirements
            
        Returns:
            Dict containing execution results and metrics
        """
        try:
            # Analyze task and assign roles
            roles = await self.assign_roles(task)
            
            # Allocate tools to roles
            tool_allocation = await self.allocate_tools(roles)
            
            # Create and execute plan
            plan = await self.create_execution_plan(task, roles)
            results = await self.execute_plan(plan)
            
            return {
                "status": "success",
                "task_id": task.task_id,
                "results": results,
                "metrics": await self.get_execution_metrics(task.task_id)
            }
        except Exception as e:
            logger.error(f"Task orchestration failed: {str(e)}")
            raise AppException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Task orchestration failed: {str(e)}"
            )
```

2. **InspectorAgent Implementation**
```python
from typing import Dict, List, Any, Optional
import pymc as pm
import numpy as np

class InspectorAgent:
    async def monitor_execution(
        self,
        task_id: str,
        execution_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Monitor task execution and evaluate results.
        
        Args:
            task_id: Unique task identifier
            execution_data: Data from task execution
            
        Returns:
            Dict containing evaluation results and recommendations
        """
        try:
            # Perform Bayesian analysis
            quality_score = await self.evaluate_quality(execution_data)
            
            # Monitor resource usage
            resource_metrics = await self.monitor_resources(task_id)
            
            # Generate recommendations
            recommendations = await self.generate_recommendations(
                quality_score,
                resource_metrics
            )
            
            return {
                "task_id": task_id,
                "quality_score": quality_score,
                "resource_metrics": resource_metrics,
                "recommendations": recommendations
            }
        except Exception as e:
            logger.error(f"Execution monitoring failed: {str(e)}")
            raise AppException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Monitoring failed: {str(e)}"
            )
```

3. **JourneyAgent Implementation**
```python
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from core.tools.secrets_manager import secrets

class JourneyStep(BaseModel):
    step_id: str
    action: str
    parameters: Dict[str, Any]
    requirements: List[str]

class JourneyAgent:
    async def execute_journey(
        self,
        steps: List[JourneyStep],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a series of journey steps.
        
        Args:
            steps: List of steps to execute
            context: Execution context and parameters
            
        Returns:
            Dict containing execution results
        """
        results = []
        try:
            for step in steps:
                # Validate step requirements
                await self.validate_step(step)
                
                # Execute step with error handling
                step_result = await self.execute_step(step, context)
                results.append(step_result)
                
                # Update context with step results
                context = await self.update_context(context, step_result)
                
            return {
                "status": "success",
                "results": results,
                "context": context
            }
        except Exception as e:
            logger.error(f"Journey execution failed: {str(e)}")
            raise AppException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Journey failed: {str(e)}"
            )
```

### 2. FastAPI Backend Implementation

#### Current Status
- Basic API structure implemented
- WebSocket support needed
- Authentication system needs enhancement

#### Implementation Steps

1. **API Structure**
```python
from fastapi import FastAPI, WebSocket, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Any, Optional

app = FastAPI(
    title="WrenchAI API",
    description="Multi-Agent Framework API",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, Any]:
    """Check system health status."""
    try:
        checks = {
            "database": await check_database(),
            "cache": await check_cache(),
            "agents": await check_agents()
        }
        return {
            "status": "healthy" if all(checks.values()) else "unhealthy",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )
```

2. **WebSocket Implementation**
```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = set()
        self.active_connections[client_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, client_id: str):
        self.active_connections[client_id].remove(websocket)
        if not self.active_connections[client_id]:
            del self.active_connections[client_id]

    async def broadcast(self, message: Dict[str, Any], client_id: str):
        if client_id in self.active_connections:
            for connection in self.active_connections[client_id]:
                await connection.send_json(message)

manager = ConnectionManager()

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
    except WebSocketDisconnect:
        await manager.disconnect(websocket, client_id)
```

3. **Authentication System**
```python
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def authenticate_user(
    credentials: OAuth2PasswordRequestForm = Depends()
) -> Dict[str, str]:
    """Authenticate user and generate access token."""
    try:
        user = await verify_credentials(credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
            
        access_token = create_access_token(user)
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )
```

### 3. Database Implementation

#### Current Status
- Basic schema defined
- Migration system needed
- Connection pooling implementation required

#### Implementation Steps

1. **Database Models**
```python
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    task_id = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    metadata = Column(JSON)
    
    executions = relationship("TaskExecution", back_populates="task")

class TaskExecution(Base):
    __tablename__ = "task_executions"
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    agent_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    results = Column(JSON)
    
    task = relationship("Task", back_populates="executions")
```

2. **Migration System**
```python
from alembic import context
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        
        with context.begin_transaction():
            context.run_migrations()
```

3. **Connection Management**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.tools.secrets_manager import secrets

async def get_database_url() -> str:
    """Get database URL from secrets manager."""
    try:
        db_password = await secrets.get_secret("db_password")
        return f"postgresql+asyncpg://user:{db_password}@localhost:5432/wrenchai"
    except Exception as e:
        logger.error(f"Failed to get database URL: {str(e)}")
        raise

async def get_db() -> AsyncSession:
    """Get database session."""
    engine = create_async_engine(
        await get_database_url(),
        pool_size=20,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800
    )
    
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
```

### 4. Testing Implementation

#### Current Status
- Basic test structure needed
- Integration tests required
- Performance testing framework needed

#### Implementation Steps

1. **Unit Tests**
```python
import pytest
from httpx import AsyncClient
from core.api import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert "checks" in data
```

2. **Integration Tests**
```python
import pytest
from httpx import AsyncClient
from core.api import app
from core.agents import SuperAgent, InspectorAgent

@pytest.mark.asyncio
async def test_task_execution():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create task
        task_data = {
            "description": "Test task",
            "requirements": ["python", "analysis"]
        }
        response = await client.post("/tasks", json=task_data)
        assert response.status_code == 201
        task_id = response.json()["task_id"]
        
        # Monitor execution
        response = await client.get(f"/tasks/{task_id}/status")
        assert response.status_code == 200
        status = response.json()["status"]
        assert status in ["pending", "running", "completed", "failed"]
```

3. **Performance Tests**
```python
import pytest
from httpx import AsyncClient
from core.api import app
import asyncio

@pytest.mark.asyncio
async def test_concurrent_requests():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create multiple concurrent requests
        tasks = []
        for i in range(10):
            task = client.get("/health")
            tasks.append(task)
        
        # Execute requests concurrently
        responses = await asyncio.gather(*tasks)
        
        # Verify responses
        for response in responses:
            assert response.status_code == 200
            assert response.elapsed.total_seconds() < 1.0
```

### 5. Deployment Implementation

#### Current Status
- Docker configuration needed
- CI/CD pipeline required
- Monitoring setup needed

#### Implementation Steps

1. **Docker Configuration**
```dockerfile
# Base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "core.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. **CI/CD Pipeline**
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest tests/ --cov=core

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and push Docker image
        run: |
          docker build -t wrenchai .
          docker push wrenchai:latest
```

3. **Monitoring Setup**
```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Initialize tracer
provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# Create tracer
tracer = trace.get_tracer(__name__)

@app.middleware("http")
async def add_tracing(request: Request, call_next):
    with tracer.start_as_current_span(
        f"{request.method} {request.url.path}",
        kind=trace.SpanKind.SERVER,
    ) as span:
        response = await call_next(request)
        span.set_attribute("http.status_code", response.status_code)
        return response
```

### 6. Streamlit Implementation

#### Current Status
- Basic Streamlit app structure needed
- Integration with FastAPI backend required
- Docusaurus portfolio playbook execution needed

#### Implementation Steps

1. **Streamlit App Structure**
```python
import streamlit as st
from typing import Dict, Any, Optional
import yaml
import asyncio
from httpx import AsyncClient

class DocusaurusPlaybookExecutor:
    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.client = AsyncClient(base_url=self.api_base_url)
    
    async def load_playbook(self, playbook_path: str) -> Dict[str, Any]:
        """Load and validate the Docusaurus portfolio playbook.
        
        Args:
            playbook_path: Path to the YAML playbook file
            
        Returns:
            Dict containing the playbook configuration
        """
        try:
            with open(playbook_path, 'r') as f:
                playbook = yaml.safe_load(f)
            return playbook
        except Exception as e:
            st.error(f"Failed to load playbook: {str(e)}")
            raise

    async def execute_playbook(self, playbook: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Docusaurus portfolio playbook.
        
        Args:
            playbook: Playbook configuration dictionary
            
        Returns:
            Dict containing execution results
        """
        try:
            response = await self.client.post(
                "/api/v1/playbooks/execute",
                json=playbook
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Failed to execute playbook: {str(e)}")
            raise

class StreamlitApp:
    def __init__(self):
        self.executor = DocusaurusPlaybookExecutor()
        
    def setup_page(self):
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title="WrenchAI Portfolio Generator",
            page_icon="🔧",
            layout="wide"
        )
        st.title("WrenchAI Portfolio Generator")
    
    def render_playbook_form(self) -> Optional[Dict[str, Any]]:
        """Render form for playbook configuration."""
        with st.form("playbook_config"):
            st.subheader("Portfolio Configuration")
            
            # Basic settings
            title = st.text_input("Portfolio Title")
            description = st.text_area("Portfolio Description")
            
            # Project settings
            st.subheader("Projects")
            num_projects = st.number_input("Number of Projects", min_value=1, value=3)
            projects = []
            
            for i in range(int(num_projects)):
                with st.expander(f"Project {i+1}"):
                    project = {
                        "name": st.text_input(f"Project {i+1} Name"),
                        "description": st.text_area(f"Project {i+1} Description"),
                        "github_url": st.text_input(f"Project {i+1} GitHub URL")
                    }
                    projects.append(project)
            
            if st.form_submit_button("Generate Portfolio"):
                return {
                    "title": title,
                    "description": description,
                    "projects": projects
                }
        return None

    async def run(self):
        """Run the Streamlit application."""
        self.setup_page()
        
        # Sidebar navigation
        page = st.sidebar.selectbox(
            "Navigation",
            ["Generate Portfolio", "View Status", "Settings"]
        )
        
        if page == "Generate Portfolio":
            config = self.render_playbook_form()
            if config:
                with st.spinner("Generating portfolio..."):
                    try:
                        playbook = await self.executor.load_playbook(
                            "core/playbooks/docusaurus_portfolio_playbook.yaml"
                        )
                        # Update playbook with form data
                        playbook.update(config)
                        
                        # Execute playbook
                        result = await self.executor.execute_playbook(playbook)
                        
                        # Show success message
                        st.success("Portfolio generated successfully!")
                        st.json(result)
                    except Exception as e:
                        st.error(f"Failed to generate portfolio: {str(e)}")
```

2. **FastAPI Integration**
```python
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, List

router = APIRouter(prefix="/api/v1/playbooks")

class Project(BaseModel):
    name: str
    description: str
    github_url: str

class PlaybookConfig(BaseModel):
    title: str
    description: str
    projects: List[Project]

@router.post("/execute")
async def execute_playbook(config: PlaybookConfig) -> Dict[str, Any]:
    """Execute the Docusaurus portfolio playbook.
    
    Args:
        config: Playbook configuration
        
    Returns:
        Dict containing execution results
    """
    try:
        # Initialize agents
        super_agent = SuperAgent()
        inspector_agent = InspectorAgent()
        
        # Create task request
        task = TaskRequest(
            task_id=f"portfolio_{datetime.utcnow().isoformat()}",
            description="Generate Docusaurus portfolio",
            requirements=["docusaurus", "github"],
            constraints={"config": config.dict()}
        )
        
        # Execute task
        result = await super_agent.orchestrate_task(task)
        
        # Monitor execution
        monitoring = await inspector_agent.monitor_execution(
            task.task_id,
            result
        )
        
        return {
            "status": "success",
            "task_id": task.task_id,
            "result": result,
            "monitoring": monitoring
        }
    except Exception as e:
        logger.error(f"Playbook execution failed: {str(e)}")
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Playbook execution failed: {str(e)}"
        )
```

3. **WebSocket Status Updates**
```python
class PlaybookStatus(BaseModel):
    task_id: str
    status: str
    progress: float
    message: str

@app.websocket("/ws/playbook/{task_id}")
async def playbook_status(websocket: WebSocket, task_id: str):
    await manager.connect(websocket, task_id)
    try:
        while True:
            # Get status updates from task execution
            status = await get_task_status(task_id)
            
            # Broadcast status to connected clients
            await manager.broadcast(
                {
                    "task_id": task_id,
                    "status": status.dict(),
                    "timestamp": datetime.utcnow().isoformat()
                },
                task_id
            )
            
            # Check if task is completed
            if status.status in ["completed", "failed"]:
                break
                
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        await manager.disconnect(websocket, task_id)
```

## Next Steps

1. **Immediate Priority**
   - Complete SuperAgent implementation
   - Enhance WebSocket support
   - Implement authentication system

2. **Short-term Goals**
   - Set up CI/CD pipeline
   - Complete test coverage
   - Deploy monitoring system

3. **Medium-term Goals**
   - Optimize database performance
   - Implement caching system
   - Add advanced analytics

4. **Long-term Vision**
   - Scale system horizontally
   - Add support for more AI models
   - Implement advanced security features 