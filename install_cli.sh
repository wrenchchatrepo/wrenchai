#!/bin/bash
# Install the Wrench AI CLI

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect shell
detect_shell() {
    if [ -n "$SHELL" ]; then
        echo "$SHELL"
    elif command_exists bash; then
        echo "/bin/bash"
    elif command_exists zsh; then
        echo "/bin/zsh"
    else
        echo "/bin/sh"
    fi
}

# Add completion to shell profile
add_completion() {
    local shell_path=$1
    local shell_name=$(basename "$shell_path")
    local profile_file=""
    
    case "$shell_name" in
        bash)
            profile_file="$HOME/.bashrc"
            echo "# Wrench AI CLI completion" >> "$profile_file"
            echo 'eval "$(pai --completion)"' >> "$profile_file"
            ;;
        zsh)
            profile_file="$HOME/.zshrc"
            echo "# Wrench AI CLI completion" >> "$profile_file"
            echo 'eval "$(pai --completion)"' >> "$profile_file"
            ;;
        *)
            echo "Completion not supported for $shell_name"
            return 1
            ;;
    esac
    
    echo "Added completion to $profile_file"
    return 0
}

# Install Pydantic AI CLI
install_cli() {
    echo "Installing Pydantic AI CLI..."
    pip install "pydantic-ai[cli]>=0.1.3"
    if [ $? -ne 0 ]; then
        echo "Error installing Pydantic AI CLI"
        exit 1
    fi
    
    # Create a symbolic link for the wrenchai CLI
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
    CLI_SCRIPT="$SCRIPT_DIR/wrenchai_cli.py"
    
    # Make the script executable
    chmod +x "$CLI_SCRIPT"
    
    # Create symbolic link in a directory in the PATH
    if [ -d "$HOME/.local/bin" ]; then
        # User-local bin directory
        ln -sf "$CLI_SCRIPT" "$HOME/.local/bin/wrenchai"
        echo "Created symbolic link in $HOME/.local/bin"
    elif [ -d "/usr/local/bin" ] && [ -w "/usr/local/bin" ]; then
        # System-wide bin directory (if writable)
        ln -sf "$CLI_SCRIPT" "/usr/local/bin/wrenchai"
        echo "Created symbolic link in /usr/local/bin"
    else
        echo "Could not find a suitable directory in PATH to install the wrenchai command"
        echo "You can manually create a symlink or add the script directory to your PATH"
    fi
    
    # Add autocompletion
    shell_path=$(detect_shell)
    echo "Detected shell: $shell_path"
    
    read -p "Do you want to add CLI completion to your shell profile? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        add_completion "$shell_path"
    fi
    
    # Create configuration directory
    python -c "from wrenchai.cli import create_config; create_config('anthropic:claude-3-5-sonnet-20240229')"
    
    echo "Installation complete!"
    echo "You can now use the 'wrenchai' command to access the Pydantic AI CLI"
}

# Main script
install_cli