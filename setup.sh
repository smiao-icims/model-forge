#!/bin/bash

# ModelForge Setup Script
# This script sets up the development environment and installs dependencies

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

# Function to install Poetry
install_poetry() {
    if ! command_exists poetry; then
        print_info "Poetry not found. Installing Poetry..."
        curl -sSL https://install.python-poetry.org | python3 -
        
        # Add Poetry to PATH for current session
        export PATH="$HOME/.local/bin:$PATH"
        
        if ! command_exists poetry; then
            print_error "Poetry installation failed. Please install Poetry manually and try again."
            print_info "Visit: https://python-poetry.org/docs/#installation"
            exit 1
        fi
        
        print_success "Poetry installed successfully"
    else
        print_success "Poetry is already installed"
    fi
}

# Function to setup virtual environment and install dependencies
setup_environment() {
    print_info "Setting up virtual environment and installing dependencies..."
    
    # Configure Poetry to create virtual environment in project directory
    poetry config virtualenvs.in-project true
    
    # Install dependencies
    poetry install
    
    print_success "Dependencies installed successfully"
    
    # Set up pre-commit hooks
    print_info "Setting up pre-commit hooks..."
    poetry run pre-commit install
    print_success "Pre-commit hooks installed"
}

# Function to activate virtual environment
activate_environment() {
    print_info "Activating virtual environment..."
    
    # Check if we're already in a virtual environment
    if [ -n "$VIRTUAL_ENV" ]; then
        print_warning "Already in a virtual environment: $VIRTUAL_ENV"
        return
    fi
    
    # Try to activate the Poetry virtual environment
    if [ -d ".venv" ]; then
        source .venv/bin/activate
        print_success "Virtual environment activated"
    else
        print_warning "Virtual environment not found. Running poetry shell..."
        poetry shell
    fi
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
    echo -e "      ${YELLOW}poetry shell${NC}"
    echo
    echo "   2. Try the ModelForge CLI:"
    echo -e "      ${YELLOW}modelforge config show${NC}"
    echo -e "      ${YELLOW}modelforge config add --provider ollama --model qwen3:1.7b${NC}"
    echo
    echo "   3. Use in your Python code:"
    echo -e "      ${YELLOW}from modelforge.registry import ModelForgeRegistry${NC}"
    echo -e "      ${YELLOW}registry = ModelForgeRegistry()${NC}"
    echo
    echo "   4. Run tests:"
    echo -e "      ${YELLOW}pytest${NC}"
    echo
    echo "📚 For more information, check the README.md file"
    echo
}

# Function to run tests
run_tests() {
    print_info "Running tests..."
    if poetry run pytest; then
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
        echo "ModelForge Setup Script"
        echo
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "Options:"
        echo "  --skip-tests    Skip running tests after setup"
        echo "  --help, -h      Show this help message"
        echo
        echo "This script will:"
        echo "  1. Check Python version compatibility"
        echo "  2. Install Poetry if not present"
        echo "  3. Set up virtual environment"
        echo "  4. Install all dependencies"
        echo "  5. Run tests (unless --skip-tests is used)"
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
    install_poetry
    setup_environment
    
    # Run tests unless skipped
    if [ "$SKIP_TESTS" = false ]; then
        run_tests
    fi
    
    show_usage
}

# Run main function
main "$@" 