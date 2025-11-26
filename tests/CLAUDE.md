---
type: claude-context
directory: tests
purpose: Test suite for media intelligence pipeline
parent: ../CLAUDE.md
sibling_readme: null
children: []
---

# Claude Code Context: tests

Test suite with mocked external dependencies.

## Test Files

### Local Pipeline Tests
- `test_transcription.py` - Whisper transcription tests
- `test_diarization.py` - Speaker diarization tests
- `test_situation.py` - Audio scene classification tests

### GCP Pipeline Tests
- `test_speech_client.py` - Cloud Speech-to-Text tests
- `test_situation_classifier.py` - Vertex AI classifier tests
- `test_storage_manager.py` - GCS operations tests
- `test_audio_processor.py` - GCP orchestrator tests

### Integration Tests
- `test_integration.py` - End-to-end local tests
- `test_gcp_integration.py` - End-to-end GCP tests

## Running Tests

```bash
podman-compose run --rm dev pytest tests/
podman-compose run --rm dev pytest tests/ --cov=src --cov-report=term
podman-compose run --rm dev pytest tests/ -v -k test_transcription
```

## Related

- **Parent**: [media-intelligence](../CLAUDE.md)
