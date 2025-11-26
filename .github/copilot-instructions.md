# GitHub Copilot Instructions

> Auto-generated from CLAUDE.md. DO NOT EDIT DIRECTLY.

## Project Overview

Media Intelligence Pipeline: A containerized audio processing system for extracting structured intelligence from recorded media.

## Essential Commands

```bash
podman-compose run --rm dev pytest tests/              # Run tests
podman-compose run --rm dev ruff check .               # Lint
./build.sh              # Build container image
./run.sh <audio.wav>    # Process audio file
```

## Architecture

### Local Pipeline (`src/`)
- `process_audio.py` - Main CLI and orchestration
- `transcription.py` - faster-whisper wrapper
- `diarization.py` - pyannote-audio speaker diarization
- `situation.py` - AST AudioSet classifier

### GCP Pipeline (`src/`)
- `main.py` - Cloud Run entry points
- `audio_processor.py` - GCP orchestrator
- `speech_client.py` - Cloud Speech-to-Text V2

## Key Patterns

- **Dataclasses**: `TranscriptSegment`, `SituationSegment`, `ProcessingResult`
- **Lazy initialization**: GCP clients use `@property` pattern
- **Retry logic**: `tenacity` for transient errors

## Guidelines

- Always use `podman-compose run --rm dev <command>`
- Prefer editing existing files over creating new ones
