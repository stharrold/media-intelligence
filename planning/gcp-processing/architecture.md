# Architecture: GCP Processing

**Date:** 2025-11-29
**Author:** stharrold
**Status:** Draft

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Google Cloud Platform                            │
│                                                                          │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────┐ │
│  │  GCS Input   │────>│ Cloud Run    │────>│  GCS Output              │ │
│  │  Bucket      │     │ (FastAPI)    │     │  Bucket                  │ │
│  │              │     │              │     │  (ProcessingResult JSON) │ │
│  └──────────────┘     └──────┬───────┘     └──────────────────────────┘ │
│         │                    │                                           │
│         │            ┌───────┴───────┐                                  │
│         │            │               │                                  │
│         ▼            ▼               ▼                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │ Eventarc/    │  │ Speech-to-   │  │ Vertex AI    │                  │
│  │ Pub/Sub      │  │ Text V2      │  │ Endpoint     │                  │
│  │ (Trigger)    │  │ (Transcribe) │  │ (Classify)   │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

The GCP audio processing pipeline is a **stateless, event-driven** system that:
1. Triggers on audio file uploads to GCS input bucket
2. Processes audio using Cloud Speech-to-Text V2 (transcription + diarization)
3. Classifies audio content using Vertex AI (AudioSet labels)
4. Stores structured JSON results to GCS output bucket

### Components

1. **Cloud Storage (Input Bucket)**
   - Purpose: Receive audio files for processing
   - Technology: GCS with Eventarc/Pub/Sub event notifications
   - Interfaces: Object creation events trigger Cloud Run

2. **Cloud Run Service**
   - Purpose: Orchestrate audio processing pipeline
   - Technology: FastAPI on Python 3.11, containerized
   - Interfaces: HTTP endpoints for GCS triggers and health checks

3. **Cloud Speech-to-Text V2**
   - Purpose: Transcribe audio with speaker diarization
   - Technology: Google Cloud Speech API V2
   - Interfaces: Async batch recognition API

4. **Vertex AI Endpoint**
   - Purpose: Classify audio content with AudioSet labels
   - Technology: Pre-trained or fine-tuned audio classification model
   - Interfaces: Online prediction endpoint

5. **Cloud Storage (Output Bucket)**
   - Purpose: Store processing results
   - Technology: GCS with JSON output files
   - Interfaces: Standard GCS write operations

## Technology Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI (Cloud Run entry point)
- **Package Manager:** uv
- **Database:** None (stateless pipeline)
- **Testing:** pytest with pytest-mock for GCP client mocking
- **Linting:** ruff
- **Containers:** Podman (local), Cloud Run (production)
- **CI/CD:** GitHub Actions

### Technology Justification

**Why Python?**
- Consistent with existing local pipeline codebase
- First-class support in all GCP client libraries
- Team expertise and shared data models (TranscriptSegment, ProcessingResult)

**Why FastAPI?**
- Native async support for I/O-bound GCP API calls
- Automatic OpenAPI documentation
- Pydantic validation for request/response models
- Lightweight for Cloud Run cold starts

**Why Cloud Run (not Cloud Functions)?**
- Longer timeout support (up to 60 minutes for large audio files)
- Container-based deployment matches local development
- Better control over memory and CPU allocation
- Concurrency handling for parallel requests

**Why Speech-to-Text V2?**
- Improved accuracy over V1 (Chirp model)
- Native speaker diarization support
- Batch recognition for files up to 8 hours

## Data Model

### Data Flow

```
1. Audio Upload (GCS)
   ↓ Eventarc trigger
2. Cloud Run receives event
   ↓ Download audio to temp file
3. Speech-to-Text V2 API
   ↓ TranscriptSegment[]
4. Vertex AI Prediction
   ↓ SituationSegment[]
5. Combine into ProcessingResult
   ↓ Upload to output bucket
6. Return success response
```

### Data Entities

Uses shared dataclasses from `src/utils.py`:

```python
@dataclass
class TranscriptSegment:
    """Transcribed text with speaker and timing."""
    text: str
    speaker_id: str
    start_time: float
    end_time: float

@dataclass
class SituationSegment:
    """Audio classification with timing."""
    labels: list[str]
    confidence_scores: list[float]
    start_time: float
    end_time: float

@dataclass
class ProcessingResult:
    """Combined pipeline output."""
    audio_file: str
    duration: float
    transcript_segments: list[TranscriptSegment]
    situation_segments: list[SituationSegment]
    metadata: dict
```

## API Design

### Endpoints

#### POST /process

Triggered by GCS object creation event via Eventarc.

**Request (GCS Event):**
```json
{
  "bucket": "my-input-bucket",
  "name": "audio/recording.wav"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "output_uri": "gs://my-output-bucket/results/recording.json"
}
```

**Response (400 Bad Request):**
```json
{
  "status": "error",
  "error": "Unsupported audio format: .xyz"
}
```

**Response (500 Internal Server Error):**
```json
{
  "status": "error",
  "error": "Speech-to-Text API error: QUOTA_EXCEEDED"
}
```

#### GET /health

Health check for Cloud Run.

**Response (200 OK):**
```json
{
  "status": "healthy"
}
```

## Container Architecture

### Containerfile.gcp

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra gcp

# Copy application code
COPY src/ src/

# Cloud Run expects port 8080
EXPOSE 8080
ENV PORT=8080

HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Cloud Run Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| Memory | 2 GiB | Audio processing requires buffer for large files |
| CPU | 2 | Parallel API calls benefit from multi-core |
| Timeout | 300s | Accommodate large audio files (< 30 min) |
| Concurrency | 80 | Default, tune based on load testing |
| Min instances | 0 | Cost optimization, accept cold starts |
| Max instances | 100 | Budget constraint |

## Security Considerations

### Authentication & Authorization

- **Workload Identity**: Cloud Run service account authenticates to GCP APIs without service account keys
- **No user authentication**: Pipeline is triggered by GCS events, not user requests
- **Service account roles**:
  - `roles/storage.objectViewer` on input bucket
  - `roles/storage.objectCreator` on output bucket
  - `roles/speech.client` for Speech-to-Text
  - `roles/aiplatform.user` for Vertex AI

### Input Validation

- Validate audio file extension (WAV, MP3, FLAC, OGG only)
- Validate file size (reject files > 1 GB)
- Sanitize blob paths to prevent path traversal (`../` sequences)

### Secrets Management

- No secrets required for GCP API access (Workload Identity)
- If HuggingFace tokens needed: use GCP Secret Manager via `key_manager.py`

### Network Security

- Cloud Run deployed with "internal and Cloud Load Balancing" ingress
- VPC Service Controls optional for additional data isolation

## Error Handling Strategy

### Error Categories

1. **Transient Errors (retry)**
   - Network timeouts
   - API rate limiting (429)
   - Temporary service unavailable (503)

2. **Permanent Errors (no retry)**
   - Invalid audio format (400)
   - File not found (404)
   - Authentication failure (401, 403)

3. **Fatal Errors (alert)**
   - Quota exceeded
   - Model endpoint unavailable
   - Repeated failures for same file

### Retry Logic

Using `tenacity` library:
- Max attempts: 3
- Exponential backoff: 4s, 16s, 60s
- Retry on: connection errors, 429, 503

### Logging

- **Format:** Structured JSON (Cloud Logging compatible)
- **Fields:** timestamp, severity, message, audio_uri, processing_stage, error_type
- **Correlation:** Use Cloud Run request ID for tracing

### Monitoring & Alerting

- **Metrics:** Cloud Run built-in metrics (request count, latency, error rate)
- **Alerts:**
  - Error rate > 5% over 5 minutes
  - Latency p95 > 60 seconds
  - Dead letter queue depth > 10

### Dead Letter Queue

For failed processing:
- Configure Pub/Sub dead letter topic
- Retain failed messages for 7 days
- Manual investigation and replay capability

## Testing Strategy

### Unit Tests

- Mock all GCP clients using `pytest-mock`
- Test each component in isolation
- Target: ≥80% coverage for new GCP modules

### Integration Tests

- Mock GCP services but test full pipeline flow
- Validate error handling and retry logic
- Test with sample audio files

### Manual GCP Validation

Before production:
- Deploy to dev GCP project
- Process real audio files
- Verify Speech-to-Text and Vertex AI outputs

## Deployment Strategy

### Environments

1. **Development:** Local Podman containers with mocked GCP
2. **Staging:** GCP dev project with real APIs
3. **Production:** GCP prod project with monitoring

### Infrastructure as Code

Uses existing `terraform/` directory:
- `main.tf`: Cloud Run, GCS buckets, Pub/Sub
- `iam.tf`: Service accounts and IAM bindings
- `variables.tf`: Environment-specific configuration

## Scalability

### Current Scale Target

- Files per day: 10,000+
- Concurrent processing: 100 files
- Audio duration: Up to 30 minutes per file

### Scaling Strategy

**Horizontal (Cloud Run auto-scaling):**
- Cloud Run scales instances 0-100 based on request queue
- Each instance handles multiple concurrent requests

**Cost Optimization:**
- Min instances = 0 (pay only when processing)
- Batch similar files to reduce cold starts

## Cost Considerations

### Pricing Estimates (per 1000 audio minutes)

| Service | Unit Cost | Estimated |
|---------|-----------|-----------|
| Speech-to-Text V2 | $0.024/min | $24 |
| Vertex AI Prediction | $0.10/1000 predictions | $0.10 |
| Cloud Storage | $0.02/GB/month | ~$0.05 |
| Cloud Run | $0.00002400/vCPU-sec | ~$5 |

### Cost Optimization

- Use standard (not enhanced) Speech model where acceptable
- Batch Vertex AI predictions
- Set Cloud Run max instances to prevent runaway costs

## Open Technical Questions

- [x] Speech-to-Text V1 vs V2? → V2 for better accuracy and diarization
- [x] Cloud Functions vs Cloud Run? → Cloud Run for longer timeouts
- [ ] Vertex AI model: pre-trained or fine-tuned? → Start with pre-trained, evaluate

## Design Trade-offs

### Decision: Synchronous vs Asynchronous Processing

**Chosen:** Synchronous (Cloud Run waits for completion)

**Reasoning:**
- Pro: Simpler architecture, immediate result availability
- Pro: Natural fit with GCS event triggers
- Con: Long-running requests for large files

**Alternative Considered:** Async with Cloud Tasks
- Why not: Added complexity for initial implementation
- Future: Consider for files > 30 minutes

### Decision: Single vs Multi-Container

**Chosen:** Single container (monolithic Cloud Run service)

**Reasoning:**
- Pro: Simpler deployment and debugging
- Pro: All components share same GCP authentication context
- Pro: Matches local development model
- Con: Larger container image

**Alternative Considered:** Microservices (separate transcription/classification services)
- Why not: Premature optimization, added operational complexity

## References

- [Cloud Speech-to-Text V2 Documentation](https://cloud.google.com/speech-to-text/v2/docs)
- [Vertex AI Prediction Documentation](https://cloud.google.com/vertex-ai/docs/predictions/overview)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Eventarc Documentation](https://cloud.google.com/eventarc/docs)
- [Workload Identity Documentation](https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity)
