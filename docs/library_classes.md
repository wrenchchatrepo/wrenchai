# Python Library Classes in Wrenchai

## FastAPI
- `FastAPI`: Main application framework
- `WebSocket`: WebSocket connection handling
- `WebSocketDisconnect`: WebSocket disconnection handling
- `HTTPException`: HTTP error handling
- `BackgroundTasks`: Asynchronous background task management
- `CORSMiddleware`: Cross-Origin Resource Sharing middleware
- `Request`: HTTP request handling
- `HTMLResponse`: HTML response type
- `JSONResponse`: JSON response type
- `StaticFiles`: Static file serving
- `Jinja2Templates`: Template rendering

## Pydantic & Pydantic AI
### Core Pydantic
- `BaseModel`: Base class for data validation
- `Field`: Field definitions and validation
- `HttpUrl`: URL validation
- `ValidationError`: Validation error handling
- `model_validator`: Model validation decorator

### Pydantic AI
- `Agent`: Core agent class
- `RunContext`: Execution context
- `Graph`: Workflow graph structure
- `GraphState`: Graph state management
- `GraphRunContext`: Graph execution context
- `register_node`: Node registration decorator
- `MCPServerHTTP`: HTTP-based MCP server
- `MCPServerStdio`: Standard IO-based MCP server
- `PydanticAIDeps`: Dependency management

### Pydantic Evals
- `Case`: Test case definition
- `Dataset`: Dataset management
- `BaseEvaluator`: Base evaluator class

## PyMC & Bayesian Tools
### PyMC
- `Model`: Probabilistic model context manager
- `Normal`: Normal distribution
- `Bernoulli`: Bernoulli distribution
- `Categorical`: Categorical distribution
- `Potential`: Potential function for evidence incorporation
- `sample`: MCMC sampling function

### ArviZ (Bayesian Visualization)
- `summary`: Statistical summary of MCMC samples

## Streamlit
### Core Components
- `set_page_config`: Page configuration
- `sidebar`: Sidebar layout
- `columns`: Column layout
- `container`: Container layout
- `expander`: Expandable section

### Input Widgets
- `text_input`: Text input field
- `text_area`: Text area input
- `button`: Button widget
- `selectbox`: Dropdown selection
- `file_uploader`: File upload widget
- `radio`: Radio button selection

### Output Components
- `markdown`: Markdown text display
- `json`: JSON data display
- `code`: Code block display
- `error`: Error message display
- `success`: Success message display
- `info`: Info message display
- `image`: Image display

## Standard Library
### Typing
- `Dict`: Dictionary type hint
- `List`: List type hint
- `Any`: Any type hint
- `Optional`: Optional type hint
- `Tuple`: Tuple type hint
- `Callable`: Callable type hint

### IO & System
- `tempfile.NamedTemporaryFile`: Temporary file handling
- `os.path`: Path manipulation
- `logging`: Logging functionality

### Data Processing
- `json`: JSON data handling
- `yaml`: YAML data handling
- `numpy`: Numerical computations
- `pandas`: Data manipulation

## Project-Specific Classes
### Core System
- `AgentManager`: Agent management system
- `BayesianEngine`: Probabilistic reasoning engine
- `ConfigLoader`: Configuration management

### Tools
- `MCPServerTools`: MCP server integration
- `WebSearchTools`: Web search functionality
- `ValidationTools`: Playbook validation

### Evaluation
- `EvaluationSystem`: Agent evaluation system
- `MetricsCollector`: Performance metrics collection

## Notes
- The libraries listed above are used throughout the codebase for different purposes:
  - FastAPI: Backend API server
  - Pydantic: Data validation and API modeling
  - PyMC: Probabilistic programming and Bayesian inference
  - Streamlit: Frontend user interface
  - Standard library: Core Python functionality
- Some classes may have additional methods and attributes not listed here
- This documentation reflects the current state of the codebase and may need updates as the project evolves 