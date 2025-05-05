## 2. System Architecture

### 2.1 High-Level Architecture

```
┌────────────────────┐     ┌───────────────────┐     ┌─────────────────┐
│  Streamlit App     │     │                   │     │                 │
│  (Wrench AI        │◄───►│  FastAPI Backend  │◄───►│  Agent System   │
│  Toolbox)          │     │                   │     │                 │
└────────────────────┘     └───────────────────┘     └─────────────────┘
         │                          │                        │
         ▼                          ▼                        ▼
┌────────────────────┐     ┌───────────────────┐     ┌─────────────────┐
│  User Interface    │     │  API Endpoints    │     │  AI Agents      │
│  - Chat            │     │  - Playbooks      │     │  - SuperAgent   │
│  - Playbooks       │     │  - Agents         │     │  - GithubAgent  │
│  - Monitoring      │     │  - Tasks          │     │  - UXDesigner   │
│  - Results         │     │  - Tools          │     │  - CodeGen      │
└────────────────────┘     └───────────────────┘     └─────────────────┘
                                     │
                                     ▼
                           ┌───────────────────┐
                           │  External Tools   │
                           │  - GitHub API     │
                           │  - Web Search     │
                           │  - Code Execution │
                           └───────────────────┘
```

### 2.2 Streamlit App Structure

```
wrenchai/streamlit_app/
├── app.py                 # Main app entry point with onboarding
├── components/            # Reusable UI components
│   ├── agent_card.py      # Agent visualization component
│   ├── error_handler.py   # Error handling
│   ├── playbook_card.py   # Playbook visualization component
│   ├── playbook_results.py# Results visualization
│   ├── task_monitor.py    # Real-time task monitoring
│   ├── tooltips.py        # Contextual help tooltips
│   └── ai_assistant.py    # Synthia AI assistant integration
├── pages/                 # Multi-page app structure
│   ├── 01_chat.py         # Conversational interface
│   ├── 02_playbooks.py    # Playbook browser and executor
│   ├── 03_agents.py       # Agent management
│   ├── 04_tools.py        # Tool browser and testing
│   └── 05_metrics.py      # Monitoring and analytics
├── models/                # Pydantic models for UI generation
│   ├── playbook_config.py # Playbook configuration models
│   ├── agent_config.py    # Agent configuration models
│   └── task_config.py     # Task configuration models
├── services/              # Backend service connections
│   ├── api_client.py      # FastAPI client
│   ├── websocket_client.py# WebSocket client
│   └── playbook_service.py# Playbook operations
└── utils/                 # Utility functions
    ├── config.py          # Configuration management
    ├── session.py         # Session state management
    ├── formatting.py      # Text and data formatting
    └── theme.py           # Custom theme configuration
```