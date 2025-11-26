#!/bin/bash
# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

# Media Intelligence Pipeline - Build Script
# Builds the container image with all dependencies

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
echo -e "${BLUE}Media Intelligence Pipeline - Build${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check for container runtime (prefer Podman)
if command -v podman &> /dev/null; then
    CONTAINER_CMD="podman"
    COMPOSE_CMD="podman-compose"
    echo -e "${GREEN}Using container runtime: podman${NC}"
elif command -v docker &> /dev/null; then
    CONTAINER_CMD="docker"
    COMPOSE_CMD="docker-compose"
    echo -e "${YELLOW}Using container runtime: docker (podman recommended)${NC}"
else
    echo -e "${RED}Error: Neither podman nor docker found${NC}"
    echo "Please install podman: https://podman.io/docs/installation"
    exit 1
fi

# Check for compose
if ! command -v $COMPOSE_CMD &> /dev/null; then
    echo -e "${YELLOW}Warning: ${COMPOSE_CMD} not found, will use ${CONTAINER_CMD} directly${NC}"
    USE_COMPOSE=false
else
    echo -e "${GREEN}Using compose: ${COMPOSE_CMD}${NC}"
    USE_COMPOSE=true
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}Please edit .env and add your HUGGINGFACE_TOKEN${NC}"
    else
        echo "HUGGINGFACE_TOKEN=" > .env
        echo -e "${YELLOW}Created empty .env file. Add your HUGGINGFACE_TOKEN for diarization.${NC}"
    fi
fi

# Create necessary directories
echo -e "${BLUE}Creating directories...${NC}"
mkdir -p data/input data/output cache models

# Build the container
echo ""
echo -e "${BLUE}Building container image...${NC}"
echo "This may take several minutes on first build."
echo ""

if [ "$USE_COMPOSE" = true ]; then
    $COMPOSE_CMD build
else
    $CONTAINER_CMD build -f Containerfile -t media-intelligence:latest .
fi

# Check build result
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Build successful!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Add your HuggingFace token to .env file (for speaker diarization)"
    echo "  2. Place audio files in data/input/"
    echo "  3. Run: ./run.sh <audio_file>"
    echo ""
    echo "Example:"
    echo "  ./run.sh recording.wav"
    echo ""
    echo "For help:"
    echo "  ./run.sh --help"
else
    echo ""
    echo -e "${RED}Build failed!${NC}"
    echo "Please check the error messages above."
    exit 1
fi
