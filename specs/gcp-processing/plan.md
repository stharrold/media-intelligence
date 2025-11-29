# Implementation Plan: GCP Processing

**Type:** feature
**Slug:** gcp-processing
**Date:** 2025-11-29

<!-- Note: Tasks follow BMAD epic order (E-001 → E-002 → E-003 → E-004) -->

## Task Breakdown

### Phase 1: Core Business Logic (E-001)

#### Task impl_001: Implement StorageManager

**Priority:** High

**Files:**
- `src/storage_manager.py`
- `tests/test_storage_manager.py`

**Description:**
Implement GCS storage operations for audio file download and result upload.

**Steps:**
1. Create `StorageConfig` dataclass with bucket configuration
2. Implement `StorageManager` class with lazy client initialization
3. Add `download_temp_file()` context manager for temporary file handling
4. Add `upload_result()` for JSON result storage
5. Add `validate_audio_format()` for format validation (WAV, MP3, FLAC, OGG)
6. Write unit tests with mocked GCS client

**Acceptance Criteria:**
- [ ] StorageManager initializes with config
- [ ] download_temp_file downloads blob to temp file and cleans up
- [ ] upload_result uploads JSON to output bucket
- [ ] validate_audio_format returns True for supported formats
- [ ] Unit tests pass with >85% coverage for this file

**Verification:**
```bash
podman-compose run --rm dev uv run pytest tests/test_storage_manager.py -v
podman-compose run --rm dev uv run pytest tests/test_storage_manager.py --cov=src/storage_manager --cov-report=term
```

**Dependencies:**
- None

---

#### Task impl_002: Implement CloudSpeechClient

**Priority:** High

**Files:**
- `src/speech_client.py`
- `tests/test_speech_client.py`

**Description:**
Implement Cloud Speech-to-Text V2 client with speaker diarization support.

**Steps:**
1. Create `SpeechConfig` dataclass with language and diarization settings
2. Implement `CloudSpeechClient` class with lazy client initialization
3. Add `transcribe()` method that accepts GCS URI and returns `TranscriptSegment` list
4. Configure diarization in recognition config
5. Parse response into `TranscriptSegment` dataclass format
6. Write unit tests with mocked Speech client

**Acceptance Criteria:**
- [ ] CloudSpeechClient initializes with config
- [ ] transcribe() accepts GCS URI and returns list of TranscriptSegment
- [ ] Speaker IDs are included in segments when diarization enabled
- [ ] Timestamps are correctly parsed
- [ ] Unit tests pass with >85% coverage for this file

**Verification:**
```bash
podman-compose run --rm dev uv run pytest tests/test_speech_client.py -v
```

**Dependencies:**
- impl_001 (uses TranscriptSegment from utils)

---

#### Task impl_003: Implement SituationClassifier

**Priority:** Medium

**Files:**
- `src/situation_classifier.py`
- `tests/test_situation_classifier.py`

**Description:**
Implement Vertex AI audio classification client for AudioSet labels.

**Steps:**
1. Create `ClassifierConfig` dataclass with endpoint configuration
2. Implement `SituationClassifier` class with lazy endpoint initialization
3. Add `classify()` method that accepts audio path and returns `SituationSegment` list
4. Configure top-N label filtering
5. Parse prediction response into `SituationSegment` format
6. Write unit tests with mocked Vertex AI endpoint

**Acceptance Criteria:**
- [ ] SituationClassifier initializes with config
- [ ] classify() returns list of SituationSegment with labels and confidence
- [ ] Top-N filtering works correctly
- [ ] Unit tests pass with >85% coverage for this file

**Verification:**
```bash
podman-compose run --rm dev uv run pytest tests/test_situation_classifier.py -v
```

**Dependencies:**
- impl_001 (uses SituationSegment from utils)

---

#### Task impl_004: Implement GCPAudioProcessor

**Priority:** High

**Files:**
- `src/audio_processor.py`
- `tests/test_audio_processor.py`

**Description:**
Implement GCP pipeline orchestrator that combines all components.

**Steps:**
1. Create `ProcessorConfig` dataclass combining all component configs
2. Implement `GCPAudioProcessor` class initializing all components
3. Add `process()` method with retry decorator (tenacity)
4. Orchestrate: download → transcribe → classify → upload result
5. Return `ProcessingResult` matching local pipeline schema
6. Write unit tests with mocked components

**Acceptance Criteria:**
- [ ] GCPAudioProcessor initializes all components
- [ ] process() orchestrates full pipeline
- [ ] Retry logic handles transient failures
- [ ] Output matches ProcessingResult schema
- [ ] Unit tests pass with >85% coverage for this file

**Verification:**
```bash
podman-compose run --rm dev uv run pytest tests/test_audio_processor.py -v
```

**Dependencies:**
- impl_001, impl_002, impl_003

---

#### Task impl_005: Implement GCP Utils

**Priority:** Medium

**Files:**
- `src/gcp_utils.py`
- `tests/test_gcp_utils.py`

**Description:**
Implement GCP-specific utilities (error handling, logging, config loading).

**Steps:**
1. Add `GCPError` exception classes for structured error handling
2. Add `configure_gcp_logging()` for structured JSON logging
3. Add `load_config_from_env()` for environment-based configuration
4. Add `parse_gcs_uri()` utility for URI parsing
5. Write unit tests

**Acceptance Criteria:**
- [ ] Error classes provide structured error information
- [ ] Logging outputs JSON format
- [ ] Config loading reads from environment variables
- [ ] GCS URI parsing handles edge cases
- [ ] Unit tests pass

**Verification:**
```bash
podman-compose run --rm dev uv run pytest tests/test_gcp_utils.py -v
```

**Dependencies:**
- None

---

### Phase 2: API Layer (E-002)

#### Task impl_006: Implement Cloud Run Entry Point

**Priority:** High

**Files:**
- `src/main.py`
- `tests/test_main.py`

**Description:**
Implement FastAPI application for Cloud Run with HTTP trigger endpoint.

**Steps:**
1. Create FastAPI app with appropriate title/description
2. Define `ProcessRequest` and `ProcessResponse` Pydantic models
3. Implement `POST /process` endpoint for GCS trigger
4. Implement `GET /health` endpoint for health checks
5. Add error handling middleware
6. Write integration tests with TestClient

**Acceptance Criteria:**
- [ ] FastAPI app starts without errors
- [ ] POST /process accepts bucket/name and returns status
- [ ] GET /health returns healthy status
- [ ] Error responses are structured JSON
- [ ] Integration tests pass

**Verification:**
```bash
podman-compose run --rm dev uv run pytest tests/test_main.py -v
```

**Dependencies:**
- impl_004

---

### Phase 3: Testing & Quality (E-003)

#### Task test_001: Unit Test Coverage

**Priority:** High

**Files:**
- `tests/test_*.py`
- `tests/conftest.py`

**Description:**
Ensure comprehensive unit test coverage for all GCP components.

**Coverage Targets:**
- Overall: ≥40% (project minimum)
- GCP modules: ≥80%

**Steps:**
1. Review existing tests for coverage gaps
2. Add fixtures in conftest.py for GCP client mocking
3. Add edge case tests (empty results, errors, timeouts)
4. Add validation tests for all input parameters
5. Run coverage report and fill gaps

**Acceptance Criteria:**
- [ ] All GCP modules have unit tests
- [ ] Edge cases covered (empty, error, timeout)
- [ ] Coverage ≥40% overall
- [ ] All tests passing

**Verification:**
```bash
podman-compose run --rm dev uv run pytest tests/ --cov=src --cov-report=term
podman-compose run --rm dev uv run pytest tests/ --cov=src --cov-fail-under=40
```

**Dependencies:**
- impl_001, impl_002, impl_003, impl_004, impl_005, impl_006

---

#### Task test_002: GCP Integration Tests

**Priority:** High

**Files:**
- `tests/test_gcp_integration.py`

**Description:**
End-to-end integration tests with mocked GCP services.

**Steps:**
1. Create comprehensive mocks for all GCP clients
2. Test full pipeline flow from HTTP request to result
3. Test error scenarios (network failures, invalid input)
4. Test retry logic behavior
5. Test concurrent request handling

**Acceptance Criteria:**
- [ ] Full pipeline integration test passes
- [ ] Error scenarios handled correctly
- [ ] Retry behavior verified
- [ ] Tests are deterministic (no flakiness)

**Verification:**
```bash
podman-compose run --rm dev uv run pytest tests/test_gcp_integration.py -v
```

**Dependencies:**
- test_001

---

### Phase 4: Containerization (E-004)

#### Task container_001: GCP Container

**Priority:** Medium

**Files:**
- `Containerfile.gcp`

**Description:**
Create Cloud Run optimized container for GCP pipeline.

**Steps:**
1. Create multi-stage Containerfile.gcp
2. Install GCP dependencies (google-cloud-* packages)
3. Configure PORT environment variable (8080 for Cloud Run)
4. Add health check
5. Test container build and run locally

**Acceptance Criteria:**
- [ ] Container builds successfully
- [ ] Container starts and responds to health checks
- [ ] Container size is optimized (<1GB)
- [ ] PORT environment variable respected

**Verification:**
```bash
podman build -f Containerfile.gcp -t media-intelligence-gcp:latest .
podman run --rm -p 8080:8080 media-intelligence-gcp:latest
curl http://localhost:8080/health
```

**Dependencies:**
- impl_006

---

#### Task container_002: Update podman-compose.yml

**Priority:** Low

**Files:**
- `podman-compose.yml`

**Description:**
Add GCP service to podman-compose for local development.

**Steps:**
1. Add `gcp` service definition using Containerfile.gcp
2. Configure environment variables for GCP credentials
3. Add volume mount for credentials (local dev only)
4. Update documentation

**Acceptance Criteria:**
- [ ] podman-compose up gcp starts GCP service
- [ ] Service responds to health checks
- [ ] Environment variables configured correctly

**Verification:**
```bash
podman-compose up -d gcp
podman-compose ps
curl http://localhost:8080/health
podman-compose down
```

**Dependencies:**
- container_001

---

## Task Dependencies Graph

```
impl_001 (StorageManager)
    │
    ├─→ impl_002 (SpeechClient)
    │       │
    │       └─→ impl_004 (AudioProcessor) ─→ impl_006 (main.py)
    │               │                              │
    ├─→ impl_003 (SituationClassifier) ────────────┘
    │
    └─→ impl_005 (gcp_utils)

impl_006 ─→ test_001 ─→ test_002 ─→ container_001 ─→ container_002
```

## Critical Path

1. impl_001 (StorageManager)
2. impl_002 (SpeechClient)
3. impl_004 (AudioProcessor)
4. impl_006 (main.py)
5. test_001 (Unit tests)
6. test_002 (Integration tests)
7. container_001 (GCP container)

## Parallel Work Opportunities

- impl_002 and impl_003 can be done in parallel (both depend on impl_001)
- impl_005 (gcp_utils) can be done in parallel with impl_002/impl_003
- container_002 can be done in parallel with test_002

## Quality Checklist

Before considering this feature complete:

- [ ] All tasks marked as complete
- [ ] Test coverage ≥ 40%
- [ ] All tests passing (unit + integration)
- [ ] Linting clean (`podman-compose run --rm dev uv run ruff check .`)
- [ ] AI Config synced (CLAUDE.md → AGENTS.md)
- [ ] Container builds successfully
- [ ] Container health checks passing

## Risk Assessment

### High Risk Tasks

- **impl_002 (SpeechClient)**: Speech-to-Text V2 API has different interface than V1
  - Mitigation: Thoroughly review V2 documentation, test with real API in dev

- **impl_003 (SituationClassifier)**: Vertex AI endpoint configuration can be complex
  - Mitigation: Document endpoint setup, provide fallback to local model

### Medium Risk Tasks

- **impl_004 (AudioProcessor)**: Orchestration complexity with multiple services
  - Mitigation: Clear error handling, comprehensive logging, retry logic

## Notes

### Implementation Tips

- Use `pytest-mock` mocker fixture for all GCP client mocking
- Follow existing patterns in `test_transcription.py` for mock setup
- Use `@property` pattern for lazy client initialization (see existing code)
- Match output schema exactly with local pipeline for compatibility

### Common Pitfalls

- Don't initialize GCP clients at module import time (causes container startup issues)
- Always use context managers for temporary file handling
- Remember to handle empty transcription results gracefully

### Resources

- [Cloud Speech-to-Text V2 Migration Guide](https://cloud.google.com/speech-to-text/v2/docs/migration)
- [Vertex AI Prediction API](https://cloud.google.com/vertex-ai/docs/predictions/get-predictions)
- [Cloud Run Best Practices](https://cloud.google.com/run/docs/tips)
