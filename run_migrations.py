#!/usr/bin/env python
import os
import subprocess
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Map variables from .env to what alembic expects
os.environ['DB_USER'] = os.environ.get('POSTGRES_USER', 'wrenchai')
os.environ['DB_PASS'] = os.environ.get('POSTGRES_PASSWORD', 'dionedge')
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '5432'
os.environ['DB_NAME'] = os.environ.get('POSTGRES_DB', 'wrenchai')

# Print the database URL for debugging
db_url = f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASS']}@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
print(f"Using database URL: {db_url}")

# Run alembic
subprocess.run(['/Users/dionedge/dev/wrenchai/.venv/bin/alembic', 'upgrade', 'head'])
