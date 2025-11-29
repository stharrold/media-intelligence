# Specification: GCP Processing

**Type:** feature
**Slug:** gcp-processing
**Date:** 2025-11-29
**Author:** stharrold

## Overview

Cloud-native audio processing pipeline using Google Cloud managed services. This feature extends the existing local audio processing pipeline to leverage GCP services for scalable, fault-tolerant processing including Cloud Speech-to-Text V2 for transcription with speaker diarization and Vertex AI for AudioSet classification.

## Implementation Context

<!-- Generated from BMAD planning documents -->

**BMAD Planning:** See `planning/gcp-processing/` for complete requirements and architecture.

**Implementation Preferences:**

- **Task Granularity:** Small tasks (1-2 hours each)
- **Include E2E Tests:** Yes (GCP integration tests)
- **Include Performance Tests:** No
- **Include Security Tests:** No
- **Follow Epic Order:** Yes (E-001 → E-002 → E-003 → E-004)

## Requirements Reference

See: `planning/gcp-processing/requirements.md`

### Functional Requirements Summary

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-001 | Cloud Storage Audio Ingestion | High |
| FR-002 | Cloud Speech-to-Text Transcription | High |
| FR-003 | Vertex AI Audio Classification | Medium |
| FR-004 | Structured Output Generation | High |
| FR-005 | Error Handling and Retry | Medium |

## Detailed Specification

### Component 1: Storage Manager

**File:** `src/storage_manager.py`

**Purpose:** Handle GCS operations for audio file ingestion and result storage

**Implementation:**

```python
from dataclasses import dataclass
from google.cloud import storage
from contextlib import contextmanager
import tempfile
from pathlib import Path

@dataclass
class StorageConfig:
    """GCS bucket configuration."""
    input_bucket: str
    output_bucket: str
    project_id: str

class StorageManager:
    """Manage GCS operations for audio processing pipeline."""

    def __init__(self, config: StorageConfig):
        self._config = config
        self._client: storage.Client | None = None

    @property
    def client(self) -> storage.Client:
        """Lazy initialization of GCS client."""
        if self._client is None:
            self._client = storage.Client(project=self._config.project_id)
        return self._client

    @contextmanager
    def download_temp_file(self, bucket_name: str, blob_name: str):
        """Download blob to temporary file with automatic cleanup."""
        # Implementation with tempfile context manager
        pass

    def upload_result(self, result: dict, blob_name: str) -> str:
        """Upload processing result to output bucket."""
        pass

    def validate_audio_format(self, blob_name: str) -> bool:
        """Validate audio file format (WAV, MP3, FLAC, OGG)."""
        pass
```

**Dependencies:**
- `google-cloud-storage>=2.0.0`

### Component 2: Speech Client

**File:** `src/speech_client.py`

**Purpose:** Cloud Speech-to-Text V2 wrapper with speaker diarization

**Implementation:**

```python
from dataclasses import dataclass
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from src.utils import TranscriptSegment

@dataclass
class SpeechConfig:
    """Speech-to-Text configuration."""
    project_id: str
    language_code: str = "en-US"
    enable_diarization: bool = True
    min_speaker_count: int = 1
    max_speaker_count: int = 10

class CloudSpeechClient:
    """Cloud Speech-to-Text V2 client with diarization."""

    def __init__(self, config: SpeechConfig):
        self._config = config
        self._client: SpeechClient | None = None

    @property
    def client(self) -> SpeechClient:
        """Lazy initialization of Speech client."""
        if self._client is None:
            self._client = SpeechClient()
        return self._client

    def transcribe(self, audio_uri: str) -> list[TranscriptSegment]:
        """Transcribe audio with speaker diarization.

        Args:
            audio_uri: GCS URI (gs://bucket/path)

        Returns:
            List of TranscriptSegment with speaker IDs and timestamps
        """
        pass
```

**Dependencies:**
- `google-cloud-speech>=2.0.0`

### Component 3: Situation Classifier

**File:** `src/situation_classifier.py`

**Purpose:** Vertex AI AudioSet classification

**Implementation:**

```python
from dataclasses import dataclass
from google.cloud import aiplatform
from src.utils import SituationSegment

@dataclass
class ClassifierConfig:
    """Vertex AI classifier configuration."""
    project_id: str
    location: str
    endpoint_id: str
    top_n: int = 5

class SituationClassifier:
    """Vertex AI audio classification client."""

    def __init__(self, config: ClassifierConfig):
        self._config = config
        self._endpoint = None

    @property
    def endpoint(self):
        """Lazy initialization of Vertex AI endpoint."""
        if self._endpoint is None:
            aiplatform.init(
                project=self._config.project_id,
                location=self._config.location
            )
            self._endpoint = aiplatform.Endpoint(self._config.endpoint_id)
        return self._endpoint

    def classify(self, audio_path: str) -> list[SituationSegment]:
        """Classify audio content using AudioSet labels.

        Returns:
            List of SituationSegment with labels and confidence scores
        """
        pass
```

**Dependencies:**
- `google-cloud-aiplatform>=1.0.0`

### Component 4: Audio Processor (GCP Orchestrator)

**File:** `src/audio_processor.py`

**Purpose:** Orchestrate GCP processing pipeline

**Implementation:**

```python
from dataclasses import dataclass
from src.storage_manager import StorageManager
from src.speech_client import CloudSpeechClient
from src.situation_classifier import SituationClassifier
from src.utils import ProcessingResult
from tenacity import retry, stop_after_attempt, wait_exponential

@dataclass
class ProcessorConfig:
    """GCP audio processor configuration."""
    storage: StorageConfig
    speech: SpeechConfig
    classifier: ClassifierConfig

class GCPAudioProcessor:
    """GCP audio processing pipeline orchestrator."""

    def __init__(self, config: ProcessorConfig):
        self._config = config
        self._storage = StorageManager(config.storage)
        self._speech = CloudSpeechClient(config.speech)
        self._classifier = SituationClassifier(config.classifier)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    def process(self, input_uri: str) -> ProcessingResult:
        """Process audio file from GCS.

        Args:
            input_uri: GCS URI of input audio file

        Returns:
            ProcessingResult with transcription and classification
        """
        pass
```

**Dependencies:**
- `tenacity>=8.0.0`

### Component 5: Cloud Run Entry Point

**File:** `src/main.py`

**Purpose:** Cloud Run/Functions HTTP entry point

**Implementation:**

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.audio_processor import GCPAudioProcessor

app = FastAPI(title="Media Intelligence GCP Pipeline")

class ProcessRequest(BaseModel):
    """Processing request from GCS trigger."""
    bucket: str
    name: str

class ProcessResponse(BaseModel):
    """Processing response."""
    status: str
    output_uri: str | None = None
    error: str | None = None

@app.post("/process", response_model=ProcessResponse)
async def process_audio(request: ProcessRequest):
    """Process audio file triggered by GCS upload."""
    pass

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
```

## Data Models

### Shared with Local Pipeline

Uses existing dataclasses from `src/utils.py`:
- `TranscriptSegment` - Transcribed text with speaker and timestamps
- `SituationSegment` - Classification labels with timestamps
- `ProcessingResult` - Combined output structure

## Testing Requirements

### Unit Tests

**Files:**
- `tests/test_storage_manager.py`
- `tests/test_speech_client.py`
- `tests/test_situation_classifier.py`
- `tests/test_audio_processor.py`

All GCP clients must be mocked using `pytest-mock`.

### Integration Tests

**File:** `tests/test_gcp_integration.py`

End-to-end test with mocked GCP services to validate:
- Full pipeline flow
- Error handling
- Retry logic

## Quality Gates

- [ ] Test coverage ≥ 40% overall (project minimum), ≥80% for new GCP modules
- [ ] All tests passing
- [ ] Linting clean (ruff check)
- [ ] AI Config synced (CLAUDE.md → AGENTS.md)
- [ ] Build succeeds (Containerfile.gcp)

## Container Specifications

### Containerfile.gcp

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra gcp

COPY src/ src/

EXPOSE 8080

ENV PORT=8080

HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Cloud Run Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| Memory | 2 GiB | Audio processing buffer for large files |
| CPU | 2 | Multi-core for parallel API calls |
| Timeout | 300s | Accommodate audio files up to 30 min |
| Concurrency | 80 | Default, tune based on load testing |
| Min instances | 0 | Cost optimization |
| Max instances | 100 | Budget constraint |

## Dependencies

**pyproject.toml additions:**

```toml
[project.optional-dependencies]
gcp = [
    "google-cloud-storage>=2.0.0",
    "google-cloud-speech>=2.0.0",
    "google-cloud-aiplatform>=1.0.0",
    "google-cloud-secret-manager>=2.0.0",
    "tenacity>=8.0.0",
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
]
```

## Implementation Notes

### Key Considerations

- Use lazy initialization (`@property`) for all GCP clients to avoid connection issues at import time
- All processing should be idempotent for retry safety
- Output schema must match local pipeline `ProcessingResult` for compatibility

### Error Handling

- Wrap all GCP API calls with `tenacity` retry decorator
- Log detailed errors with request context
- Return structured error responses from Cloud Run

### Dead Letter Queue

For failed processing, configure Pub/Sub dead letter topic:
- Create dead letter topic: `{project}-audio-dlq`
- Set max delivery attempts: 3
- Retain failed messages for 7 days
- Monitor DLQ depth with Cloud Monitoring alert

### Logging

Use structured JSON logging compatible with Cloud Logging:

```python
import logging
import json

class StructuredLogFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "severity": record.levelname,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record),
            "audio_uri": getattr(record, "audio_uri", None),
            "processing_stage": getattr(record, "processing_stage", None),
        })
```

### Alerting

Configure Cloud Monitoring alert policies:
- Error rate > 5% over 5 minutes → PagerDuty/Slack
- Latency p95 > 60 seconds → Warning notification
- DLQ depth > 10 messages → Critical alert

### Security

- Use Workload Identity for GCP authentication (no service account keys)
- Input validation on all API endpoints
- Sanitize file paths to prevent path traversal
- IAM roles: storage.objectViewer, storage.objectCreator, speech.client, aiplatform.user

## Current State

The repository already contains GCP-related files in `src/`:
- `src/main.py` - Cloud Run/Functions entry points
- `src/audio_processor.py` - GCP orchestrator
- `src/speech_client.py` - Cloud Speech-to-Text V2
- `src/situation_classifier.py` - Vertex AI AutoML
- `src/storage_manager.py` - GCS operations
- `src/gcp_utils.py` - GCP-specific utilities

This specification focuses on:
1. Completing implementation of existing stubs
2. Adding comprehensive tests
3. Ensuring quality gate compliance
4. Container optimization for Cloud Run

## References

- [Cloud Speech-to-Text V2 Documentation](https://cloud.google.com/speech-to-text/v2/docs)
- [Vertex AI Prediction Documentation](https://cloud.google.com/vertex-ai/docs/predictions/overview)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
