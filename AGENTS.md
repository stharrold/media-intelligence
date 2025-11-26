# AGENTS.md

> Cross-tool AI configuration file. Auto-generated from CLAUDE.md.
> DO NOT EDIT DIRECTLY - edit CLAUDE.md and run sync.

This file provides guidance to AI assistants when working with code in this repository.

## Project Overview

Media Intelligence Pipeline: A containerized audio processing system for extracting structured intelligence from recorded media. Supports two deployment modes:

- **Local**: CPU-only containerized pipeline (air-gapped deployment ready)
- **GCP**: Cloud-native pipeline using Google Cloud managed services

## Essential Commands

```bash
# Build container (once)
podman-compose build

# Run any command (containerized - preferred)
podman-compose run --rm dev <command>

# Common operations
podman-compose run --rm dev pytest tests/              # Run tests
podman-compose run --rm dev pytest tests/ -v -k test_  # Single test
podman-compose run --rm dev ruff check .               # Lint
podman-compose run --rm dev ruff check --fix .         # Auto-fix

# Build and run production container
./build.sh              # Build container image
./run.sh <audio.wav>    # Process audio file
./test.sh               # Run validation tests

# GCP Deployment
./deploy.sh --project PROJECT_ID --region REGION
./test_gcp.sh
```

## Architecture

### Local Pipeline (`src/`)
- `process_audio.py` - Main CLI and orchestration
- `transcription.py` - faster-whisper wrapper (Whisper INT8)
- `diarization.py` - pyannote-audio 3.1 speaker diarization
- `situation.py` - AST AudioSet classifier
- `utils.py` - Shared utilities, data classes

### GCP Pipeline (`src/`)
- `main.py` - Cloud Run/Functions entry points
- `audio_processor.py` - GCP orchestrator
- `speech_client.py` - Cloud Speech-to-Text V2
- `situation_classifier.py` - Vertex AI AutoML
- `storage_manager.py` - GCS operations
- `gcp_utils.py` - GCP-specific utilities

## Key Patterns

- **Dataclasses**: `TranscriptSegment`, `SituationSegment`, `ProcessingResult`
- **Lazy initialization**: GCP clients use `@property` pattern
- **Retry logic**: `tenacity` for transient errors
- **Context managers**: `download_temp_file()` for cleanup

## Testing

```bash
podman-compose run --rm dev pytest tests/
podman-compose run --rm dev pytest tests/ --cov=src --cov-report=term
```

## Prerequisites

```bash
podman --version          # 4.0+ required
podman-compose --version
git --version
python3 --version         # 3.11+
```

## Critical Guidelines

- **One way to run**: Always use `podman-compose run --rm dev <command>`
- **ALWAYS prefer editing existing files** over creating new ones
- **Quality gates must pass** before creating any PR
