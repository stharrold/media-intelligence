#!/bin/bash
# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

# Media Intelligence Pipeline - Run Script
# Wrapper for processing audio files in the container

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

# Check for container runtime (prefer Podman)
if command -v podman &> /dev/null; then
    CONTAINER_CMD="podman"
    COMPOSE_CMD="podman-compose"
elif command -v docker &> /dev/null; then
    CONTAINER_CMD="docker"
    COMPOSE_CMD="docker-compose"
else
    echo -e "${RED}Error: Neither podman nor docker found${NC}"
    echo "Please install podman: https://podman.io/docs/installation"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Speaker diarization will be disabled without HuggingFace token."
    echo "Run ./build.sh first or create .env from .env.example"
    echo ""
fi

# Source .env file if it exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs -d '\n' 2>/dev/null || grep -v '^#' .env | xargs)
fi

# Check if data directories exist
if [ ! -d "data/input" ]; then
    echo -e "${YELLOW}Creating data/input directory...${NC}"
    mkdir -p data/input
fi

if [ ! -d "data/output" ]; then
    echo -e "${YELLOW}Creating data/output directory...${NC}"
    mkdir -p data/output
fi

if [ ! -d "cache" ]; then
    echo -e "${YELLOW}Creating cache directory...${NC}"
    mkdir -p cache
fi

# Show help if no arguments
if [ $# -eq 0 ]; then
    echo -e "${BLUE}Media Intelligence Pipeline${NC}"
    echo ""
    echo "Usage: ./run.sh [OPTIONS] <input>"
    echo ""
    echo "Arguments:"
    echo "  <input>         Audio file or directory name in data/input/"
    echo ""
    echo "Options:"
    echo "  -m, --model     Whisper model (tiny, base, small, medium)"
    echo "  -l, --language  Language code (default: en, use 'auto' for detection)"
    echo "  --no-diarization  Disable speaker diarization"
    echo "  --no-situation    Disable situation classification"
    echo "  -v, --verbose   Enable verbose output"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run.sh meeting.wav"
    echo "  ./run.sh meeting.wav -m small"
    echo "  ./run.sh recordings/ -l auto"
    echo ""
    echo "Place audio files in: data/input/"
    echo "Results will be in:   data/output/"
    exit 0
fi

# Parse arguments to find input file
INPUT=""
EXTRA_ARGS=""

for arg in "$@"; do
    case $arg in
        --help)
            # Run container with --help
            $CONTAINER_CMD run --rm \
                -v "$SCRIPT_DIR/data/input:/data/input:ro" \
                -v "$SCRIPT_DIR/data/output:/data/output:rw" \
                -v "$SCRIPT_DIR/cache:/root/.cache:rw" \
                -e "HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN:-}" \
                media-intelligence:latest --help
            exit 0
            ;;
        -*)
            EXTRA_ARGS="$EXTRA_ARGS $arg"
            ;;
        *)
            if [ -z "$INPUT" ]; then
                INPUT="$arg"
            else
                EXTRA_ARGS="$EXTRA_ARGS $arg"
            fi
            ;;
    esac
done

# Validate input
if [ -z "$INPUT" ]; then
    echo -e "${RED}Error: No input file specified${NC}"
    echo "Usage: ./run.sh <input_file>"
    exit 1
fi

# Check if input exists
INPUT_PATH="data/input/$INPUT"
if [ ! -e "$INPUT_PATH" ]; then
    echo -e "${RED}Error: Input not found: $INPUT_PATH${NC}"
    echo ""
    echo "Available files in data/input/:"
    ls -la data/input/ 2>/dev/null || echo "  (directory empty or not accessible)"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Media Intelligence Pipeline${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Input: ${GREEN}$INPUT${NC}"
echo -e "Output: ${GREEN}data/output/${NC}"
echo ""

# Run the container
$CONTAINER_CMD run --rm \
    -v "$SCRIPT_DIR/data/input:/data/input:ro" \
    -v "$SCRIPT_DIR/data/output:/data/output:rw" \
    -v "$SCRIPT_DIR/cache:/root/.cache:rw" \
    -e "HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN:-}" \
    -e "OMP_NUM_THREADS=${OMP_NUM_THREADS:-4}" \
    -e "MKL_NUM_THREADS=${MKL_NUM_THREADS:-4}" \
    --memory="${MEMORY_LIMIT:-8g}" \
    --cpus="${CPU_LIMIT:-4}" \
    media-intelligence:latest \
    "/data/input/$INPUT" \
    -o /data/output \
    $EXTRA_ARGS

# Check result
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Processing complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Results saved to: data/output/"
    echo ""
    echo "Output files:"
    ls -la data/output/ | grep -E "$(basename ${INPUT%.*})" | head -10 || echo "  (check data/output/ for results)"
else
    echo ""
    echo -e "${RED}Processing failed!${NC}"
    exit 1
fi
