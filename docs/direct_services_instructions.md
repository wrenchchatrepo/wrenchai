# Addendum: Running WrenchAI Services Directly (No Docker)

This guide explains how to run the WrenchAI services directly on your local machine without using Docker.

## Prerequisites

- Python 3.9+ installed
- PostgreSQL 15+ installed locally
- Redis 7+ installed locally
- Git (to clone the repository if you haven't already)
- Valid API keys for LLM providers

## Step 1: Install Redis

### On macOS

Using Homebrew:
```bash
brew install redis
```

Start Redis service:
```bash
brew services start redis
```

### On Ubuntu/Debian

```bash
sudo apt update
sudo apt install redis-server
```

Edit the Redis configuration to enable protected mode:
```bash
sudo nano /etc/redis/redis.conf
```

Find the line that says `# requirepass foobared` and change it to:
```
requirepass your_secure_redis_password
```

Restart Redis:
```bash
sudo systemctl restart redis
```

### On Windows

1. Download Redis for Windows from GitHub: https://github.com/microsoftarchive/redis/releases
2. Install the MSI package
3. Open a command prompt and run:

```bash
redis-cli
> CONFIG SET requirepass "your_secure_redis_password"
```

## Step 2: Install PostgreSQL

### On macOS

Using Homebrew:
```bash
brew install postgresql@15
brew services start postgresql@15
```

### On Ubuntu/Debian

```bash
sudo apt update
sudo apt install postgresql-15 postgresql-contrib
```

### On Windows

1. Download the installer from https://www.postgresql.org/download/windows/
2. Run the installer and follow the prompts

## Step 3: Create PostgreSQL Database

Execute the following commands:

```bash
sudo -u postgres psql
```

In the PostgreSQL prompt:
```sql
CREATE USER wrenchai WITH PASSWORD 'your_secure_password';
CREATE DATABASE wrenchai OWNER wrenchai;
ALTER USER wrenchai WITH SUPERUSER;
\q
```

## Step 4: Set Up Python Environment

```bash
# Navigate to the project directory
cd wrenchai

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 5: Configure Environment Variables

Create a `.env` file in the root directory:

```env
# Database Configuration (adjust host to 'localhost' since we're running locally)
POSTGRES_USER=wrenchai
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=wrenchai
DATABASE_URL=postgresql://wrenchai:your_secure_password@localhost:5432/wrenchai

# Redis Configuration (adjust host to 'localhost')
REDIS_PASSWORD=your_secure_redis_password
REDIS_URL=redis://:your_secure_redis_password@localhost:6379/0

# Security
SECRET_KEY=your_secret_key

# API Configuration (use localhost instead of Docker service name)
API_BASE_URL=http://localhost:8000

# LLM API Keys
OPENAI_API_KEY=sk-your_openai_key
ANTHROPIC_API_KEY=sk-ant-your_anthropic_key
GEMINI_API_KEY=your_gemini_key
```

## Step 6: Run Database Migrations

```bash
# Ensure you're in the project root directory with virtualenv activated

# Run Alembic migrations to set up the database schema
alembic upgrade head
```

## Step 7: Start the FastAPI Backend

```bash
# Ensure you're in the project root directory with virtualenv activated

# Start the FastAPI application
uvicorn core.api:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

## Step 8: Start the Streamlit Frontend

Open a new terminal window, navigate to the project directory, and activate the virtual environment.

```bash
# Navigate to the project directory
cd wrenchai

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Start the Streamlit application
cd streamlit_app
streamlit run app.py
```

This will start the main Streamlit app. To run the Portfolio Generator specifically:

```bash
streamlit run portfolio_generator.py
```

The Streamlit UI will be available at http://localhost:8501

## Step 9: Execute the Docusaurus Portfolio Playbook

Follow the same execution steps as in the main instructions, starting from Step 4.

## Troubleshooting Local Installation

### Redis Connection Issues

1. Verify Redis is running: `redis-cli ping` (should return PONG)
2. Check if authentication is working: `redis-cli -a your_secure_redis_password ping`
3. Ensure your REDIS_URL in the .env file includes the correct password and points to localhost

### PostgreSQL Connection Issues

1. Verify PostgreSQL is running: `pg_isready`
2. Test connection: `psql -U wrenchai -d wrenchai -h localhost`
3. Check your DATABASE_URL in the .env file

### Alembic Migration Errors

1. Make sure PostgreSQL is running and accessible
2. Verify database credentials are correct
3. Try running with verbose output: `alembic upgrade head --verbose`

### API Startup Issues

1. Check for error messages in the terminal
2. Verify all requirements are installed: `pip install -r requirements.txt`
3. Make sure environment variables are loaded correctly: `python -c "import os; print(os.environ.get('DATABASE_URL'))"`

### Streamlit Connection to API

1. Ensure the FastAPI backend is running
2. Verify the API_BASE_URL is set to http://localhost:8000
3. Check that the Streamlit app can reach the API: `curl http://localhost:8000/health`

---

Note: Running services directly is ideal for development and testing. For production use, the Docker setup is recommended for better isolation, consistency, and ease of deployment.