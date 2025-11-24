# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Media Intelligence Pipeline: A containerized audio processing system for extracting structured intelligence from recorded media. Supports two deployment modes:

- **Local**: CPU-only containerized pipeline (air-gapped deployment ready)
- **GCP**: Cloud-native pipeline using Google Cloud managed services

## Build and Test Commands

### Local Deployment
```bash
./build.sh              # Build container image
./run.sh <audio.wav>    # Process audio file
./test.sh               # Run validation tests
pytest tests/           # Run unit tests
```

### GCP Deployment
```bash
./deploy.sh --project PROJECT_ID --region REGION   # Deploy to GCP
./test_gcp.sh           # Run GCP-specific tests
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

### Infrastructure (`terraform/`)
- `main.tf` - GCP resources (Cloud Run, GCS, Pub/Sub)
- `iam.tf` - Service accounts and permissions
- `variables.tf` / `outputs.tf` - Configuration

## Key Patterns

- **Dataclasses**: `TranscriptSegment`, `SituationSegment`, `ProcessingResult`
- **Lazy initialization**: GCP clients use `@property` pattern
- **Retry logic**: `tenacity` for transient errors
- **Context managers**: `download_temp_file()` for cleanup

## Configuration

- `.env` - Environment variables (HuggingFace token, GCP settings)
- `config.yaml` - Advanced processing options
- Precedence: defaults → config.yaml → .env → CLI args

## Testing

Tests are in `tests/` with mocked external dependencies:
- `test_transcription.py`, `test_diarization.py`, `test_situation.py` - Local
- `test_speech_client.py`, `test_situation_classifier.py`, `test_storage_manager.py`, `test_audio_processor.py` - GCP
- `test_integration.py`, `test_gcp_integration.py` - End-to-end
