#!/bin/bash

# ModelForge Wrapper Script
# Alternative to poetry shell + modelforge for quick usage

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}" >&2
}

print_error() {
    echo -e "${RED}❌ $1${NC}" >&2
}

# Check if we're in the correct directory
if [ ! -f "pyproject.toml" ]; then
    print_error "pyproject.toml not found. Please run this script from the model-forge directory."
    exit 1
fi

# Check if Poetry is installed
if ! command -v poetry >/dev/null 2>&1; then
    print_error "Poetry is not installed. Please run ./setup.sh first to set up the environment."
    exit 1
fi

# Check if dependencies are installed
if [ ! -d ".venv" ] && ! poetry env info >/dev/null 2>&1; then
    print_info "Setting up environment (this may take a moment)..."
    poetry install >/dev/null 2>&1
fi

# Run the modelforge command with all passed arguments
poetry run modelforge "$@"
