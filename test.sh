#!/bin/bash
# Media Intelligence Pipeline - Test Script
# Usage: ./test.sh [--unit] [--integration] [--all]

set -e

# Default values
RUN_UNIT=false
RUN_INTEGRATION=false
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            RUN_UNIT=true
            shift
            ;;
        --integration)
            RUN_INTEGRATION=true
            shift
            ;;
        --all)
            RUN_UNIT=true
            RUN_INTEGRATION=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--unit] [--integration] [--all] [-v|--verbose]"
            echo ""
            echo "Options:"
            echo "  --unit         Run unit tests only"
            echo "  --integration  Run integration tests only (requires GCP credentials)"
            echo "  --all          Run all tests"
            echo "  -v, --verbose  Verbose output"
            echo ""
            echo "Environment variables for integration tests:"
            echo "  PROJECT_ID         GCP Project ID"
            echo "  CLOUD_RUN_URL      Cloud Run service URL (optional)"
            echo "  RUN_INTEGRATION_TESTS=true  Enable integration tests"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# If no test type specified, run unit tests
if [ "$RUN_UNIT" = false ] && [ "$RUN_INTEGRATION" = false ]; then
    RUN_UNIT=true
fi

# Build pytest arguments
PYTEST_ARGS=()
if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS+=("-v")
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Media Intelligence Pipeline Tests${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: Not in a virtual environment${NC}"
    echo "Consider running: python -m venv venv && source venv/bin/activate"
    echo ""
fi

# Install test dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -q -r requirements.txt
pip install -q pytest pytest-mock pytest-asyncio

# Run unit tests
if [ "$RUN_UNIT" = true ]; then
    echo ""
    echo -e "${YELLOW}Running unit tests...${NC}"
    echo ""

    python -m pytest tests/ \
        --ignore=tests/test_integration.py \
        "${PYTEST_ARGS[@]}" \
        --tb=short \
        -q

    echo ""
    echo -e "${GREEN}Unit tests passed!${NC}"
fi

# Run integration tests
if [ "$RUN_INTEGRATION" = true ]; then
    echo ""
    echo -e "${YELLOW}Running integration tests...${NC}"
    echo ""

    # Check for required environment variables
    if [ -z "$PROJECT_ID" ]; then
        echo -e "${RED}Error: PROJECT_ID environment variable is required for integration tests${NC}"
        exit 1
    fi

    # Check for GCP credentials
    if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        echo -e "${YELLOW}Warning: GOOGLE_APPLICATION_CREDENTIALS not set${NC}"
        echo "Using default credentials (gcloud auth application-default login)"
        echo ""
    fi

    export RUN_INTEGRATION_TESTS=true

    python -m pytest tests/test_integration.py \
        "${PYTEST_ARGS[@]}" \
        --tb=short \
        -q

    echo ""
    echo -e "${GREEN}Integration tests passed!${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All tests completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
