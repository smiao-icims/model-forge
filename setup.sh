#!/bin/bash

# ModelForge Setup Script
# This script sets up the development environment and installs dependencies using uv

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    ModelForge Setup Script                  ║"
    echo "║        A reusable library for managing LLM providers        ║"
    echo "║                      Powered by uv ⚡                       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3.11 or higher."
        exit 1
    fi

    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    required_version="3.11"

    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
        print_error "Python $required_version or higher is required. Found: $python_version"
        exit 1
    fi

    print_success "Python version $python_version is compatible"
}

# Function to install uv
install_uv() {
    if ! command_exists uv; then
        print_info "uv not found. Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh

        # Add uv to PATH for current session
        export PATH="$HOME/.cargo/bin:$PATH"

        if ! command_exists uv; then
            print_error "uv installation failed. Please install uv manually and try again."
            print_info "Visit: https://docs.astral.sh/uv/getting-started/installation/"
            exit 1
        fi

        print_success "uv installed successfully"
    else
        print_success "uv is already installed"
    fi
}

# Function to setup virtual environment and install dependencies
setup_environment() {
    print_info "Setting up virtual environment and installing dependencies..."

    # Create and sync virtual environment with dependencies
    uv sync --extra dev

    print_success "Dependencies installed successfully"

    # Set up pre-commit hooks
    print_info "Setting up pre-commit hooks..."
    if uv run pre-commit install; then
        print_success "Pre-commit hooks installed"
    else
        print_warning "Pre-commit hooks installation failed, but continuing..."
    fi
}

# Function to activate virtual environment
activate_environment() {
    print_info "To activate the virtual environment, run:"
    echo -e "${YELLOW}source .venv/bin/activate${NC}"
    echo
    print_info "Or use uv to run commands directly:"
    echo -e "${YELLOW}uv run <command>${NC}"
}

# Function to display usage instructions
show_usage() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    Setup Complete! 🎉                       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo
    echo "📋 Next steps:"
    echo "   1. Activate the virtual environment:"
    echo -e "      ${YELLOW}source .venv/bin/activate${NC}"
    echo -e "      ${BLUE}Or use: ${YELLOW}uv run <command>${NC}"
    echo
    echo "   2. Try the ModelForge CLI:"
    echo -e "      ${YELLOW}uv run modelforge config show${NC}"
    echo -e "      ${YELLOW}uv run modelforge config add --provider ollama --model qwen3:1.7b${NC}"
    echo
    echo "   3. Use in your Python code:"
    echo -e "      ${YELLOW}from modelforge.registry import ModelForgeRegistry${NC}"
    echo -e "      ${YELLOW}registry = ModelForgeRegistry()${NC}"
    echo
    echo "   4. Run tests:"
    echo -e "      ${YELLOW}uv run pytest${NC}"
    echo
    echo "   5. Run pre-commit checks:"
    echo -e "      ${YELLOW}uv run pre-commit run --all-files${NC}"
    echo
    echo "📚 For more information, check the README.md file"
    echo
}

# Function to run tests
run_tests() {
    print_info "Running tests..."
    if uv run pytest; then
        print_success "All tests passed!"
    else
        print_warning "Some tests failed. Check the output above."
    fi
}

# Main execution
main() {
    print_header

    # Parse command line arguments
    SKIP_TESTS=false
    HELP=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --help|-h)
                HELP=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Usage: $0 [--skip-tests] [--help]"
                exit 1
                ;;
        esac
    done

    if [ "$HELP" = true ]; then
        echo "ModelForge Setup Script (powered by uv)"
        echo
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "Options:"
        echo "  --skip-tests    Skip running tests after setup"
        echo "  --help, -h      Show this help message"
        echo
        echo "This script will:"
        echo "  1. Check Python version compatibility"
        echo "  2. Install uv if not present"
        echo "  3. Set up virtual environment"
        echo "  4. Install all dependencies including dev dependencies"
        echo "  5. Set up pre-commit hooks"
        echo "  6. Run tests (unless --skip-tests is used)"
        echo
        exit 0
    fi

    # Check if we're in the correct directory
    if [ ! -f "pyproject.toml" ]; then
        print_error "pyproject.toml not found. Please run this script from the model-forge directory."
        exit 1
    fi

    # Execute setup steps
    check_python_version
    install_uv
    setup_environment

    # Run tests unless skipped
    if [ "$SKIP_TESTS" = false ]; then
        run_tests
    fi

    show_usage
}

# Run main function
main "$@"
