#!/bin/bash
# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

# Media Intelligence Pipeline - Test Script
# Validates the installation and runs basic tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Media Intelligence Pipeline - Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

TESTS_PASSED=0
TESTS_FAILED=0

# Test function
run_test() {
    local name="$1"
    local cmd="$2"

    echo -n "Testing: $name... "
    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}PASSED${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test container runtime
echo -e "${BLUE}Checking prerequisites...${NC}"
echo ""

if command -v podman &> /dev/null; then
    CONTAINER_CMD="podman"
    echo -e "Container runtime: ${GREEN}podman${NC}"
elif command -v docker &> /dev/null; then
    CONTAINER_CMD="docker"
    echo -e "Container runtime: ${GREEN}docker${NC}"
else
    echo -e "Container runtime: ${RED}NOT FOUND${NC}"
    echo "Please install podman or docker"
    exit 1
fi

# Check compose
if command -v podman-compose &> /dev/null; then
    echo -e "Compose: ${GREEN}podman-compose${NC}"
elif command -v docker-compose &> /dev/null; then
    echo -e "Compose: ${GREEN}docker-compose${NC}"
else
    echo -e "Compose: ${YELLOW}not found (optional)${NC}"
fi

echo ""

# Test 1: Check required files
echo -e "${BLUE}Checking required files...${NC}"
run_test "Dockerfile exists" "[ -f Dockerfile ]"
run_test "compose.yaml exists" "[ -f compose.yaml ]"
run_test "requirements.txt exists" "[ -f requirements.txt ]"
run_test "Source files exist" "[ -d src ] && [ -f src/process_audio.py ]"
run_test ".env.example exists" "[ -f .env.example ]"
echo ""

# Test 2: Check .env file
echo -e "${BLUE}Checking configuration...${NC}"
if [ -f ".env" ]; then
    run_test ".env file exists" "true"
    if grep -q "HUGGINGFACE_TOKEN=hf_" .env 2>/dev/null; then
        run_test "HuggingFace token configured" "true"
    else
        echo -e "Testing: HuggingFace token configured... ${YELLOW}NOT SET${NC} (diarization disabled)"
    fi
else
    echo -e "Testing: .env file exists... ${YELLOW}NOT FOUND${NC}"
    echo "  Run ./build.sh to create .env from .env.example"
fi
echo ""

# Test 3: Check directories
echo -e "${BLUE}Checking directories...${NC}"
run_test "data/input directory exists" "[ -d data/input ]"
run_test "data/output directory exists" "[ -d data/output ]"
run_test "cache directory exists" "[ -d cache ]"
echo ""

# Test 4: Check container image
echo -e "${BLUE}Checking container image...${NC}"
if $CONTAINER_CMD image exists media-intelligence:latest 2>/dev/null || \
   $CONTAINER_CMD images | grep -q "media-intelligence.*latest" 2>/dev/null; then
    run_test "Container image built" "true"
    IMAGE_EXISTS=true
else
    echo -e "Testing: Container image built... ${YELLOW}NOT FOUND${NC}"
    echo "  Run ./build.sh to build the container"
    IMAGE_EXISTS=false
fi
echo ""

# Test 5: Test container functionality (if image exists)
if [ "$IMAGE_EXISTS" = true ]; then
    echo -e "${BLUE}Testing container functionality...${NC}"

    # Test Python environment
    run_test "Python environment" "$CONTAINER_CMD run --rm media-intelligence:latest python --version"

    # Test module imports
    run_test "Import utils module" "$CONTAINER_CMD run --rm --entrypoint python media-intelligence:latest -c 'from src import utils'"
    run_test "Import transcription module" "$CONTAINER_CMD run --rm --entrypoint python media-intelligence:latest -c 'from src import transcription'"
    run_test "Import diarization module" "$CONTAINER_CMD run --rm --entrypoint python media-intelligence:latest -c 'from src import diarization'"
    run_test "Import situation module" "$CONTAINER_CMD run --rm --entrypoint python media-intelligence:latest -c 'from src import situation'"

    # Test CLI help
    run_test "CLI help" "$CONTAINER_CMD run --rm media-intelligence:latest --help"

    echo ""
fi

# Test 6: Run pytest if available locally
if command -v pytest &> /dev/null && [ -d "tests" ]; then
    echo -e "${BLUE}Running unit tests...${NC}"
    if pytest tests/ -v --tb=short 2>/dev/null; then
        echo -e "Unit tests: ${GREEN}PASSED${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "Unit tests: ${RED}FAILED${NC}"
        ((TESTS_FAILED++))
    fi
    echo ""
fi

# Test 7: Process test file if available
if [ "$IMAGE_EXISTS" = true ]; then
    TEST_FILES=$(find data/input -type f \( -name "*.wav" -o -name "*.mp3" -o -name "*.m4a" \) 2>/dev/null | head -1)
    if [ -n "$TEST_FILES" ]; then
        echo -e "${BLUE}Testing with sample audio file...${NC}"
        echo "File: $(basename $TEST_FILES)"
        if ./run.sh "$(basename $TEST_FILES)" -m tiny.en --no-diarization 2>/dev/null; then
            run_test "Process sample file" "true"
            run_test "JSON output created" "[ -f data/output/*_results.json ]"
            run_test "Transcript output created" "[ -f data/output/*_transcript.txt ]"
        else
            echo -e "Testing: Process sample file... ${RED}FAILED${NC}"
            ((TESTS_FAILED++))
        fi
        echo ""
    else
        echo -e "${YELLOW}No test audio files found in data/input/${NC}"
        echo "Add a sample .wav or .mp3 file to test full processing"
        echo ""
    fi
fi

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please check the output above.${NC}"
    exit 1
fi
