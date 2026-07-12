#!/bin/bash

# ==============================================================================
# Cross-Platform Setup Script (macOS / Linux / Windows Git Bash)
# ==============================================================================

echo "Setting up project dependencies..."

# Detect Windows (Git Bash reports OSTYPE=msys)
IS_WINDOWS=false
case "$OSTYPE" in
    msys*|cygwin*) IS_WINDOWS=true ;;
esac

# uv and direnv install into ~/.local/bin on all platforms
export PATH="$HOME/.local/bin:$PATH"

# 1. Install uv
if ! command -v uv &> /dev/null; then
    echo "uv not found. Installing uv..."

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            echo "macOS detected. Installing via Homebrew..."
            brew install uv
        else
            echo "Homebrew not found. Falling back to curl installer..."
            curl -LsSf https://astral.sh/uv/install.sh | sh
        fi
    elif [ "$IS_WINDOWS" = true ]; then
        # Windows Git Bash: the sh installer is not supported, use PowerShell
        echo "Windows detected. Installing via PowerShell installer..."
        powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \
            "irm https://astral.sh/uv/install.ps1 | iex"
    else
        # Linux
        echo "Linux detected. Installing via curl..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi

    # Pick up the freshly installed binaries in this shell
    if [ -f "$HOME/.local/bin/env" ]; then
        source "$HOME/.local/bin/env"
    elif [ -f "$HOME/.cargo/env" ]; then
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
    elif [ "$IS_WINDOWS" = true ]; then
        # No package manager assumption on Windows: fetch the release binary
        mkdir -p "$HOME/.local/bin"
        # Release asset has no .exe suffix; Git Bash needs one to execute it
        curl -fLo "$HOME/.local/bin/direnv.exe" \
            "https://github.com/direnv/direnv/releases/latest/download/direnv.windows-amd64"
    else
        curl -sfL https://direnv.net/install.sh | bash
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

# 3. Hook direnv to Bash (Git Bash may not have a .bashrc yet)
if [ -f "$HOME/.bashrc" ] || [ "$IS_WINDOWS" = true ]; then
    BASH_RC="$HOME/.bashrc"
    if ! grep -q "direnv hook bash" "$BASH_RC" 2>/dev/null; then
        echo "" >> "$BASH_RC"
        echo '# Hook direnv' >> "$BASH_RC"
        echo 'eval "$(direnv hook bash)"' >> "$BASH_RC"
        echo "Added direnv hook to $BASH_RC"
    else
        echo "direnv hook already exists in $BASH_RC"
    fi

    # Git Bash: the native direnv.exe exports a Windows-style (semicolon-
    # separated) PATH that bash cannot read, which breaks every command
    # lookup after the hook fires. Override the hook function to convert
    # PATH back to POSIX form. Must come after `direnv hook bash` above.
    if [ "$IS_WINDOWS" = true ] && ! grep -q "cygpath -p" "$BASH_RC" 2>/dev/null; then
        cat << 'EOF' >> "$BASH_RC"
_direnv_hook() {
  local previous_exit_status=$?
  eval "$(direnv export bash)"
  case "$PATH" in
    *\;*) export PATH="$(/usr/bin/cygpath -p "$PATH")" ;;
  esac
  return $previous_exit_status
}
EOF
        echo "Added Git Bash PATH fix for direnv to $BASH_RC"
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
# (bin/ on macOS/Linux, Scripts/ on Windows)
if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
elif [ -f .venv/Scripts/activate ]; then
  source .venv/Scripts/activate
fi

# 2. Add git scripts to PATH
# This enables running git-sync (or git sync) directly
PATH_add skills/git/scripts

# 3. Load local secrets/config from .env if it exists
dotenv_if_exists .env
EOF
fi

# 6. Allow direnv
if command -v direnv &> /dev/null; then
    direnv allow .envrc
fi

echo "Setup complete! You are ready to code."
