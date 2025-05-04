# WrenchAI Portfolio Generator: Setup and Execution Guide

This guide walks you through the process of setting up and running the WrenchAI Portfolio Generator, which uses a Docusaurus Playbook to generate a professional portfolio website.

## Prerequisites

Before starting, ensure you have the following installed:

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- Git (to clone the repository if you haven't already)
- A valid API key for the LLM provider (OpenAI, Anthropic, etc.) that will be used by the agents

## Step 1: Environment Setup

1. Create or modify the `.env` file in the root directory with the following variables:

```env
# Database Configuration
POSTGRES_USER=wrenchai
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=wrenchai
DATABASE_URL=postgresql://wrenchai:your_secure_password@db:5432/wrenchai

# Redis Configuration
REDIS_PASSWORD=your_secure_redis_password
REDIS_URL=redis://:your_secure_redis_password@redis:6379/0

# Security
SECRET_KEY=your_secret_key

# API Configuration
API_BASE_URL=http://api:8000

# LLM API Keys - Add the appropriate keys for your LLMs
OPENAI_API_KEY=sk-your_openai_key
ANTHROPIC_API_KEY=sk-ant-your_anthropic_key
GEMINI_API_KEY=your_gemini_key
```

## Step 2: Start the Services

1. From the root directory of the project, start all services using Docker Compose:

```bash
docker-compose up -d
```

This command starts several services:
- API (FastAPI backend)
- Streamlit (UI)
- PostgreSQL database
- Redis cache
- Nginx web server

2. Wait for all services to initialize. You can check the status with:

```bash
docker-compose ps
```

3. Check the logs to ensure everything is running properly:

```bash
docker-compose logs -f
```

Press Ctrl+C to exit the logs view when ready.

## Step 3: Access the Portfolio Generator

1. Open your web browser and navigate to:

```
http://localhost:8501/
```

If you're using the Nginx configuration, you can also use:

```
http://localhost/
```

2. You should see the main WrenchAI interface. To access the Portfolio Generator specifically, select the appropriate page from the sidebar or navigate directly to:

```
http://localhost:8501/portfolio_generator
```

## Step 4: Execute the Docusaurus Portfolio Playbook

1. Once in the Portfolio Generator interface, you'll see a form with several configuration options:

   - **Basic Settings**:
     - Enter a title for your portfolio
     - Select a theme (classic, modern, or minimal)
     - Provide a description of your portfolio

   - **Projects**:
     - Specify the number of projects to include
     - For each project, enter:
       - Name
       - Description
       - GitHub URL (if applicable)
       - Technologies used

2. After filling out the form, click the **Generate Portfolio** button.

3. The system will:
   - Load the Docusaurus portfolio playbook
   - Update it with your configuration
   - Submit it to the API for execution
   - Display a success message with the task ID

## Step 5: Monitor Execution Progress

1. After submitting the playbook, switch to the **View Status** page from the sidebar.

2. You should see your task ID and current execution status.

3. The playbook execution involves multiple steps with various agents working together:
   - SuperAgent analyzes and plans
   - GithubJourneyAgent sets up the repository
   - UXDesignerAgent and InspectorAgent design the UI
   - CodeGeneratorAgent sets up Docusaurus and generates content
   - And more...

4. This process may take some time as the agents work through all the steps in the playbook.

## Step 6: View and Access Your Generated Portfolio

Once the playbook execution is complete:

1. The status page will show the execution as completed
2. You'll receive a link to your GitHub repository containing your portfolio
3. If configured, you'll also get a link to the deployed GitHub Pages site

## Troubleshooting

If you encounter issues:

### API Connection Problems

1. Check the **Settings** page and verify the API Base URL is correctly set.
2. Ensure all Docker services are running: `docker-compose ps`
3. Check the API logs: `docker-compose logs api`

### Playbook Execution Failures

1. Check if there are any specific error messages in the UI
2. Look at the API logs for detailed error information: `docker-compose logs api`
3. Ensure your LLM API keys are valid and have sufficient credits

### Playbook Path Issues

If you get a "Failed to load playbook" error:

1. The default path is `core/playbooks/docusaurus_portfolio_playbook.yaml`
2. Make sure this file exists in the expected location relative to the API service
3. You may need to modify the path in `streamlit_app/portfolio_generator.py` if your deployment structure differs

## Advanced: Running Locally (Without Docker)

If you prefer to run the services locally without Docker:

1. Create a Python virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r streamlit_app/requirements.txt
```

2. Start the FastAPI backend:

```bash
uvicorn core.api:app --reload --host 0.0.0.0 --port 8000
```

3. In a separate terminal, start the Streamlit app:

```bash
cd streamlit_app
streamlit run portfolio_generator.py
```

4. Access the UI at `http://localhost:8501`

## Notes

- The playbook execution may take several minutes depending on the complexity of your portfolio
- If GitHub integration is enabled, ensure your GitHub credentials or token are properly configured
- Some tools and specialized agents might be in development, so certain advanced features might not be fully implemented yet

---

Happy portfolio generating with WrenchAI! 🔧