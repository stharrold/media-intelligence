---
type: claude-context
directory: src
purpose: Python source code for the media intelligence pipeline
parent: ../CLAUDE.md
sibling_readme: null
children: []
---

# Claude Code Context: src

Python source code for both local and GCP deployment modes.

## Local Pipeline

- `process_audio.py` - Main CLI and orchestration
- `transcription.py` - faster-whisper wrapper (Whisper INT8)
- `diarization.py` - pyannote-audio 3.1 speaker diarization
- `situation.py` - AST AudioSet classifier
- `utils.py` - Shared utilities, data classes

## GCP Pipeline

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

## Related

- **Parent**: [media-intelligence](../CLAUDE.md)
