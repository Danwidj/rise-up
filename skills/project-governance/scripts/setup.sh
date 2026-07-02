#!/bin/bash

# ==============================================================================
# Cross-Platform Setup Script (macOS Linux / Windows Git Bash)
# ==============================================================================

echo "Setting up project dependencies..."

# 1. Install uv
if ! command -v uv &> /dev/null; then
    echo "uv not found. Installing uv..."
    
    # Check OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            echo "macOS detected. Installing via Homebrew..."
            brew install uv
        else
            echo "Homebrew not found. Falling back to curl installer..."
            curl -LsSf https://astral.sh/uv/install.sh | sh
        fi
    else
        # Linux or Windows Git Bash
        echo "/Linux/Windows detected. Installing via curl..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
    
    # Try to source the cargo env just in case it was installed there
    if [ -f "$HOME/.cargo/env" ]; then
        source "$HOME/.cargo/env"
    fi
else
    echo "uv is already installed."
fi

# 2. Initialize project (if pyproject.toml is missing)
if [ ! -f "pyproject.toml" ]; then
    echo "pyproject.toml not found. Initializing uv project..."
    uv init
else
    echo "pyproject.toml already exists."
fi

# 3. Add pytest as a dev dependency
echo "Installing Pytest..."
uv add --dev pytest


echo "Configuring environment auto-activation via direnv..."

# 1. Install direnv if missing
if ! command -v direnv &> /dev/null; then
    echo "direnv not found. Installing direnv..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install direnv
        else
            echo "Homebrew not found. Please install direnv manually: https://direnv.net/"
        fi
    else
        echo "Please install direnv for your system: https://direnv.net/"
    fi
else
    echo "direnv is already installed."
fi

# 2. Hook direnv to Zsh
if [ -f "$HOME/.zshrc" ]; then
    if ! grep -q "direnv hook zsh" "$HOME/.zshrc"; then
        echo "" >> "$HOME/.zshrc"
        echo '# Hook direnv' >> "$HOME/.zshrc"
        echo 'eval "$(direnv hook zsh)"' >> "$HOME/.zshrc"
        echo "Added direnv hook to ~/.zshrc"
    else
        echo "direnv hook already exists in ~/.zshrc"
    fi
fi

# 3. Hook direnv to Bash
if [ -f "$HOME/.bashrc" ] || [[ "$OSTYPE" == "msys" ]]; then
    BASH_RC="$HOME/.bashrc"
    if ! grep -q "direnv hook bash" "$BASH_RC" 2>/dev/null; then
        echo "" >> "$BASH_RC"
        echo '# Hook direnv' >> "$BASH_RC"
        echo 'eval "$(direnv hook bash)"' >> "$BASH_RC"
        echo "Added direnv hook to $BASH_RC"
    else
        echo "direnv hook already exists in $BASH_RC"
    fi
fi

# 4. Ensure git-sync runner script is executable
if [ -f "skills/git/scripts/git-sync" ]; then
    chmod +x skills/git/scripts/git-sync
fi

# 5. Create local .envrc file if it doesn't exist
if [ ! -f ".envrc" ]; then
    echo "Creating .envrc..."
    cat << 'EOF' > .envrc
# 1. Auto-activate Python virtual environment
if [ -d .venv ]; then
  source .venv/bin/activate
fi

# 2. Add git scripts to PATH
# This enables running git-sync (or git sync) directly
PATH_add skills/git/scripts

# 3. Load local secrets/config from .env if it exists
dotenv_if_exists .env
EOF
fi

# 5. Allow direnv
if command -v direnv &> /dev/null; then
    direnv allow .envrc
fi

echo "Setup complete! You are ready to code."

