# WrenchAI MVP Implementation Plan

## Core Framework Components

### 1. SuperAgent Implementation
#### Current Status
- Basic agent structure exists
- Missing core orchestration logic
- Incomplete tool allocation

#### Implementation Steps
1. **Role Assignment System**
   ```python
   class SuperAgent:
       async def assign_roles(self, task: Dict[str, Any]) -> List[Dict[str, Any]]:
           # Use sequential thinking for role analysis
           roles = await self.sequential_thinking.analyze({
               "task": task,
               "available_roles": self.available_roles,
               "constraints": self.constraints
           })
           return self._validate_and_assign_roles(roles)
   ```
   - Implement role matching algorithm
   - Add role validation logic
   - Create role dependency resolution

2. **Tool Allocation System**
   ```python
   async def allocate_tools(self, roles: List[Dict[str, Any]]) -> Dict[str, List[str]]:
       tool_allocations = {}
       for role in roles:
           tools = await self.memory.query({
               "role": role["name"],
               "required_capabilities": role["capabilities"]
           })
           tool_allocations[role["name"]] = self._optimize_tool_set(tools)
       return tool_allocations
   ```
   - Create tool capability mapping
   - Implement tool conflict resolution
   - Add tool version management

3. **Execution Planning**
   ```python
   async def create_execution_plan(self, task: Dict[str, Any], roles: List[Dict[str, Any]]) -> Dict[str, Any]:
       plan = {
           "stages": [],
           "dependencies": {},
           "estimated_resources": {},
           "fallback_strategies": {}
       }
       # Use sequential thinking for plan generation
       return await self.sequential_thinking.generate_plan(task, roles, plan)
   ```
   - Add stage sequencing logic
   - Implement resource estimation
   - Create fallback handling

### 2. InspectorAgent Enhancement
#### Current Status
- Basic monitoring structure
- Missing Bayesian reasoning
- Incomplete evaluation system

#### Implementation Steps
1. **Bayesian Reasoning Integration**
   ```python
   class InspectorAgent:
       async def evaluate_output(self, output: Dict[str, Any], criteria: Dict[str, Any]) -> float:
           # Initialize PyMC model
           with pm.Model() as model:
               # Define priors
               quality = pm.Normal("quality", mu=0.5, sigma=0.1)
               # Define likelihood
               likelihood = pm.Bernoulli("likelihood", p=quality, observed=self._get_observations(output))
               # Perform inference
               trace = pm.sample(1000, tune=1000)
           return self._calculate_confidence(trace)
   ```
   - Implement prior distribution setup
   - Add observation model
   - Create inference engine

2. **Progress Monitoring System**
   ```python
   async def monitor_progress(self, task_id: str) -> Dict[str, Any]:
       status = await self.memory.retrieve(f"task:{task_id}:status")
       metrics = self._calculate_progress_metrics(status)
       alerts = self._check_thresholds(metrics)
       return {"metrics": metrics, "alerts": alerts}
   ```
   - Add real-time metric collection
   - Implement threshold monitoring
   - Create alert system

3. **Output Evaluation Framework**
   ```python
   async def evaluate_agent_output(self, agent_id: str, output: Dict[str, Any]) -> Dict[str, Any]:
       evaluation = {
           "quality_score": 0.0,
           "confidence": 0.0,
           "improvement_suggestions": []
       }
       # Use sequential thinking for evaluation
       return await self.sequential_thinking.evaluate(output, evaluation)
   ```
   - Implement quality metrics
   - Add confidence scoring
   - Create feedback generation

### 3. JourneyAgent Completion
#### Current Status
- Basic execution framework
- Missing optimization
- Incomplete error handling

#### Implementation Steps
1. **Playbook Execution System**
   ```python
   class JourneyAgent:
       async def execute_playbook(self, playbook: Dict[str, Any]) -> Dict[str, Any]:
           results = []
           for step in playbook["steps"]:
               try:
                   result = await self._execute_step(step)
                   results.append(result)
                   await self.memory.store(f"step:{step['id']}", result)
               except Exception as e:
                   await self._handle_step_error(step, e)
           return self._compile_results(results)
   ```
   - Add step validation
   - Implement progress tracking
   - Create result compilation

2. **Tool Usage Optimization**
   ```python
   async def optimize_tool_usage(self, tools: List[str], task: Dict[str, Any]) -> List[str]:
       usage_patterns = await self.memory.query({
           "tools": tools,
           "task_type": task["type"]
       })
       return self._create_optimal_sequence(usage_patterns)
   ```
   - Implement tool sequencing
   - Add resource optimization
   - Create usage analytics

3. **Error Recovery System**
   ```python
   async def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
       recovery_plan = await self.sequential_thinking.analyze_error({
           "error": str(error),
           "context": context,
           "available_actions": self.recovery_actions
       })
       return await self._execute_recovery(recovery_plan)
   ```
   - Add error classification
   - Implement recovery strategies
   - Create error logging

## Infrastructure Components

### 4. Docker Implementation
#### Current Status
- Missing container setup
- No orchestration
- Incomplete health checks

#### Implementation Steps
1. **Base Dockerfile**
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY . .
   
   HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
     CMD curl -f http://localhost:8000/health || exit 1
   
   CMD ["uvicorn", "core.api:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **Docker Compose Setup**
   ```yaml
   version: '3.8'
   
   services:
     api:
       build: .
       ports:
         - "8000:8000"
       environment:
         - DB_HOST=db
         - REDIS_HOST=cache
       depends_on:
         - db
         - cache
     
     db:
       image: postgres:13
       volumes:
         - postgres_data:/var/lib/postgresql/data
       environment:
         - POSTGRES_USER=wrenchai
         - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
         - POSTGRES_DB=wrenchai
   
     cache:
       image: redis:6
       volumes:
         - redis_data:/data
   
   volumes:
     postgres_data:
     redis_data:
   
   secrets:
     db_password:
       file: ./secrets/db_password.txt
   ```

3. **Health Check Implementation**
   ```python
   @app.get("/health")
   async def health_check():
       checks = {
           "database": await check_database_connection(),
           "cache": await check_cache_connection(),
           "mcp_server": await check_mcp_server_status()
       }
       return {
           "status": "healthy" if all(checks.values()) else "unhealthy",
           "checks": checks
       }
   ```

### 5. FastAPI Backend
#### Current Status
- Basic API structure
- Missing websockets
- Incomplete error handling

#### Implementation Steps
1. **WebSocket Implementation**
   ```python
   class AgentWebSocket:
       def __init__(self):
           self.active_connections: List[WebSocket] = []
   
       async def connect(self, websocket: WebSocket):
           await websocket.accept()
           self.active_connections.append(websocket)
   
       async def broadcast(self, message: Dict[str, Any]):
           for connection in self.active_connections:
               await connection.send_json(message)
   
   agent_ws = AgentWebSocket()
   
   @app.websocket("/ws/agent/{agent_id}")
   async def agent_websocket(websocket: WebSocket, agent_id: str):
       await agent_ws.connect(websocket)
       try:
           while True:
               data = await websocket.receive_json()
               response = await process_agent_message(agent_id, data)
               await websocket.send_json(response)
       except WebSocketDisconnect:
           agent_ws.active_connections.remove(websocket)
   ```

2. **API Documentation**
   ```python
   app = FastAPI(
       title="WrenchAI API",
       description="API for WrenchAI agent framework",
       version="1.0.0",
       docs_url="/docs",
       redoc_url="/redoc"
   )
   
   class TaskInput(BaseModel):
       description: str
       constraints: Optional[Dict[str, Any]] = None
       timeout: Optional[int] = 3600
   
   @app.post("/tasks/", response_model=TaskResponse)
   async def create_task(task: TaskInput):
       """
       Create a new task for processing by agents.
       
       - **description**: Task description
       - **constraints**: Optional task constraints
       - **timeout**: Optional timeout in seconds
       """
       return await task_manager.create_task(task)
   ```

3. **Error Handling**
   ```python
   class WrenchAIException(Exception):
       def __init__(self, message: str, code: str, details: Optional[Dict[str, Any]] = None):
           self.message = message
           self.code = code
           self.details = details or {}
           super().__init__(self.message)
   
   @app.exception_handler(WrenchAIException)
   async def wrenchai_exception_handler(request: Request, exc: WrenchAIException):
       return JSONResponse(
           status_code=400,
           content={
               "error": {
                   "code": exc.code,
                   "message": exc.message,
                   "details": exc.details
               }
           }
       )
   ```

### 6. Security Implementation
#### Current Status
- Missing authentication
- Incomplete encryption
- No audit logging

#### Implementation Steps
1. **Authentication System**
   ```python
   from fastapi_security import OAuth2PasswordBearer
   from jose import JWTError, jwt
   
   oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
   
   async def authenticate_user(credentials: Dict[str, str]) -> Dict[str, Any]:
       user = await verify_credentials(credentials)
       if not user:
           raise WrenchAIException("Invalid credentials", "AUTH_ERROR")
       access_token = create_access_token(user)
       return {"access_token": access_token, "token_type": "bearer"}
   
   async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
       try:
           payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
           user_id = payload.get("sub")
           if user_id is None:
               raise WrenchAIException("Invalid token", "AUTH_ERROR")
           return await get_user(user_id)
       except JWTError:
           raise WrenchAIException("Invalid token", "AUTH_ERROR")
   ```

2. **Data Encryption**
   ```python
   from cryptography.fernet import Fernet
   
   class EncryptionManager:
       def __init__(self):
           self.key = self._load_or_generate_key()
           self.fernet = Fernet(self.key)
   
       def encrypt_data(self, data: Dict[str, Any]) -> bytes:
           return self.fernet.encrypt(json.dumps(data).encode())
   
       def decrypt_data(self, encrypted_data: bytes) -> Dict[str, Any]:
           return json.loads(self.fernet.decrypt(encrypted_data).decode())
   
       def _load_or_generate_key(self) -> bytes:
           if os.path.exists(KEY_FILE):
               with open(KEY_FILE, 'rb') as f:
                   return f.read()
           key = Fernet.generate_key()
           with open(KEY_FILE, 'wb') as f:
               f.write(key)
           return key
   ```

3. **Audit Logging**
   ```python
   class AuditLogger:
       def __init__(self):
           self.logger = logging.getLogger("audit")
           self._setup_logger()
   
       async def log_event(self, event_type: str, user_id: str, details: Dict[str, Any]):
           event = {
               "timestamp": datetime.utcnow().isoformat(),
               "event_type": event_type,
               "user_id": user_id,
               "details": details
           }
           await self.db.audit_logs.insert_one(event)
           self.logger.info(f"Audit event: {json.dumps(event)}")
   
       def _setup_logger(self):
           handler = logging.FileHandler("audit.log")
           handler.setFormatter(logging.Formatter(
               '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
           ))
           self.logger.addHandler(handler)
   ```

### 7. Cost Management
#### Current Status
- Missing token tracking
- No resource monitoring
- Incomplete alerting

#### Implementation Steps
1. **Token Tracking**
   ```python
   class TokenTracker:
       def __init__(self):
           self.tiktoken_encoder = tiktoken.get_encoding("cl100k_base")
   
       async def track_usage(self, model: str, input_text: str, output_text: str) -> Dict[str, int]:
           input_tokens = len(self.tiktoken_encoder.encode(input_text))
           output_tokens = len(self.tiktoken_encoder.encode(output_text))
           
           usage = {
               "input_tokens": input_tokens,
               "output_tokens": output_tokens,
               "total_tokens": input_tokens + output_tokens
           }
           
           await self.store_usage(model, usage)
           return usage
   
       async def store_usage(self, model: str, usage: Dict[str, int]):
           await self.db.token_usage.insert_one({
               "timestamp": datetime.utcnow(),
               "model": model,
               **usage
           })
   ```

2. **Resource Monitoring**
   ```python
   class ResourceMonitor:
       def __init__(self):
           self.metrics = {}
   
       async def track_resources(self, resource_type: str, usage: Dict[str, Any]):
           metric = {
               "timestamp": datetime.utcnow(),
               "resource_type": resource_type,
               **usage
           }
           await self.db.resource_usage.insert_one(metric)
           await self._check_thresholds(resource_type, usage)
   
       async def _check_thresholds(self, resource_type: str, usage: Dict[str, Any]):
           thresholds = await self.db.thresholds.find_one({"resource_type": resource_type})
           if thresholds and any(usage[k] > v for k, v in thresholds.items()):
               await self.alert_system.create_alert(
                   level="warning",
                   message=f"Resource usage exceeded threshold for {resource_type}",
                   details=usage
               )
   ```

3. **Alert System**
   ```python
   class AlertSystem:
       def __init__(self):
           self.handlers = []
   
       async def create_alert(self, level: str, message: str, details: Dict[str, Any]):
           alert = {
               "timestamp": datetime.utcnow(),
               "level": level,
               "message": message,
               "details": details
           }
           await self.db.alerts.insert_one(alert)
           await self._notify_handlers(alert)
   
       async def _notify_handlers(self, alert: Dict[str, Any]):
           for handler in self.handlers:
               await handler.handle_alert(alert)
   ```

### 8. Documentation
#### Current Status
- Missing API docs
- Incomplete setup guides
- No architecture docs

#### Implementation Steps
1. **API Documentation**
   - Create OpenAPI documentation
   - Add endpoint descriptions
   - Include example requests/responses

2. **Setup Documentation**
   - Create installation guide
   - Add configuration guide
   - Include troubleshooting guide

3. **Architecture Documentation**
   - Create system overview
   - Add component diagrams
   - Include interaction patterns

## Critical MVP Blockers

### 1. Core Framework Completion
1. Complete SuperAgent
   - Implement role assignment
   - Add tool allocation
   - Create execution planning

2. Implement Bayesian Reasoning
   - Add PyMC integration
   - Create evaluation models
   - Implement decision making

3. Finish Tool Integration
   - Complete web search
   - Add code execution
   - Implement tool registry

### 2. Infrastructure Essentials
1. Docker Setup
   - Create base Dockerfile
   - Add compose configuration
   - Implement health checks

2. FastAPI Completion
   - Add websocket support
   - Implement error handling
   - Create API documentation

3. MCP Server
   - Complete server implementation
   - Add protocol handlers
   - Implement fallback system

### 3. Security Fundamentals
1. Authentication
   - Implement user system
   - Add API key management
   - Create role system

2. Data Security
   - Implement encryption
   - Add secret management
   - Create audit logging

### 4. Cost Management
1. Token Tracking
   - Implement counter
   - Add usage storage
   - Create reporting

2. Resource Monitoring
   - Add GCP monitoring
   - Implement alerts
   - Create dashboards

### 5. Documentation
1. Setup Guide
   - Installation steps
   - Configuration guide
   - Examples

2. API Documentation
   - Endpoint documentation
   - Authentication guide
   - Error handling

3. Architecture Overview
   - System diagrams
   - Component descriptions
   - Integration guide 