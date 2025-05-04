#!/bin/bash
# Install the WrenchAI CLI (wai)

set -e

echo "Installing WrenchAI CLI..."

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Make sure we're in the right directory
cd "$SCRIPT_DIR"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found"
    exit 1
fi

# Create a virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install Pydantic AI and dependencies
echo "Installing dependencies..."
pip install "pydantic-ai>=0.1.0"
pip install -e .

echo ""
echo "WrenchAI CLI (wai) has been installed successfully!"
echo "You can run it with: wai"
echo ""
echo "Available commands:"
echo "  wai list                - List all available playbooks"
echo "  wai select <id>         - Display a playbook configuration"
echo "  wai describe <id>       - Describe parameters for a playbook"
echo "  wai run <id> [options]  - Execute a playbook"
echo ""
echo "For more information, use: wai --help"