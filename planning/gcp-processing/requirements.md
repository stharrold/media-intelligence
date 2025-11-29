# Requirements: GCP Processing

**Date:** 2025-11-29
**Author:** stharrold
**Status:** Draft

## Business Context

### Problem Statement

The local audio processing pipeline is limited to single-machine CPU processing. Users need cloud-scale processing with managed services for transcription, speaker diarization, and audio classification to handle large volumes of audio files with automatic scaling, fault tolerance, and integration with enterprise cloud infrastructure.

### Success Criteria

- [ ] Process audio files via Cloud Storage triggers
- [ ] Transcription accuracy matches or exceeds local Whisper model
- [ ] Speaker diarization integrated with transcription output
- [ ] AudioSet classification via Vertex AI
- [ ] Processing latency under 2x audio duration for files under 30 minutes
- [ ] 99.9% availability for the processing pipeline

### Stakeholders

- **Primary:** Operations teams processing large audio archives, analysts requiring near-real-time transcription and classification, enterprise customers with existing GCP infrastructure
- **Secondary:** DevOps teams managing cloud infrastructure, security teams reviewing data handling

## Functional Requirements

### FR-001: Cloud Storage Audio Ingestion

**Priority:** High
**Description:** Automatically trigger processing when audio files are uploaded to designated GCS bucket

**Acceptance Criteria:**
- [ ] GCS bucket configured with event notification
- [ ] Cloud Function or Cloud Run triggered on object creation
- [ ] Support for WAV, MP3, FLAC, OGG audio formats
- [ ] Validate file format and size before processing

### FR-002: Cloud Speech-to-Text Transcription

**Priority:** High
**Description:** Transcribe audio using Google Cloud Speech-to-Text V2 API with speaker diarization

**Acceptance Criteria:**
- [ ] Use Speech-to-Text V2 for improved accuracy
- [ ] Enable speaker diarization in transcription config
- [ ] Support multiple languages (configurable)
- [ ] Return timestamped transcript segments

### FR-003: Vertex AI Audio Classification

**Priority:** Medium
**Description:** Classify audio content using AudioSet labels via Vertex AI

**Acceptance Criteria:**
- [ ] Deploy audio classification model to Vertex AI endpoint
- [ ] Return top-N AudioSet labels with confidence scores
- [ ] Support batch inference for efficiency
- [ ] Handle model versioning and updates

### FR-004: Structured Output Generation

**Priority:** High
**Description:** Generate standardized JSON output combining transcription, diarization, and classification

**Acceptance Criteria:**
- [ ] Output matches local pipeline ProcessingResult schema
- [ ] Include transcript segments with speaker IDs and timestamps
- [ ] Include situation/classification segments with labels
- [ ] Store results in GCS output bucket

### FR-005: Error Handling and Retry

**Priority:** Medium
**Description:** Robust error handling with automatic retry for transient failures

**Acceptance Criteria:**
- [ ] Implement exponential backoff for API calls
- [ ] Dead letter queue for failed messages
- [ ] Structured logging for debugging
- [ ] Alert on repeated failures

## Non-Functional Requirements

### Performance

- Processing latency: < 2x audio duration for files under 30 minutes
- Throughput: 100+ concurrent audio files
- API response time: < 500ms for health checks
- Cold start: < 10 seconds for Cloud Run instances

### Security

- **Authentication:** Workload Identity for GCP service-to-service auth (no service account keys)
- **Authorization:** IAM roles for service account (storage.objectViewer, storage.objectCreator, speech.client, aiplatform.user)
- **Data encryption:** At rest (GCS default encryption) and in transit (TLS 1.3)
- **Input validation:** File extension whitelist, size limits (< 1 GB), path traversal prevention
- **Audit logging:** Cloud Audit Logs enabled for all GCP API calls

### Scalability

- Horizontal scaling: Yes, Cloud Run auto-scales 0-100 instances
- Stateless design: No shared state between requests
- Event-driven: Pub/Sub decouples ingestion from processing

### Reliability

- Uptime target: 99.9% availability
- Error handling: Retry transient failures (3 attempts, exponential backoff)
- Dead letter queue: Failed messages retained for 7 days for investigation
- Data durability: GCS provides 99.999999999% durability

### Maintainability

- Code coverage: ≥40% overall (project minimum), ≥80% for new GCP modules
- Documentation: API docs via OpenAPI, architecture docs in planning/
- Testing: Unit tests (mocked GCP), integration tests, manual GCP validation

## Constraints

### Technology

- Programming language: Python 3.11+
- Package manager: uv
- Framework: FastAPI for Cloud Run entry point
- Database: None (stateless pipeline)
- Container: Podman (local), Cloud Run (production)

### Budget

- Speech-to-Text V2: ~$0.024/minute (standard model)
- Vertex AI Prediction: ~$0.10/1000 predictions
- Cloud Run: ~$0.00002400/vCPU-second
- Cloud Storage: ~$0.02/GB/month
- **Monthly estimate:** $500-2000 for 10,000 audio files/day (avg 5 min each)

### Timeline

- Target completion: Implementation ready for review
- Milestones: Core pipeline → Testing → Container → Deployment

### Dependencies

- External systems: GCP Speech-to-Text V2, Vertex AI, Cloud Storage, Cloud Run
- Internal systems: Shared data models from src/utils.py (TranscriptSegment, ProcessingResult)
- Third-party libraries: google-cloud-storage, google-cloud-speech, google-cloud-aiplatform, tenacity, fastapi

## Out of Scope

Explicitly excluded from this feature:

- **Real-time streaming:** Only batch processing of complete audio files
- **Video processing:** Audio extraction from video is not supported
- **Custom model training:** Uses pre-trained or pre-deployed models only
- **Multi-region deployment:** Single region deployment initially
- **User-facing UI:** API-only, no web interface
- **Terraform infrastructure:** Uses existing terraform/ modules, no new IaC

## Risks and Mitigation

| Risk | Probability | Impact | Mitigation Strategy |
|------|------------|--------|---------------------|
| GCP API quota limits exceeded | Medium | High | Request quota increase, implement rate limiting |
| Speech-to-Text accuracy lower than Whisper | Low | Medium | Benchmark before deployment, fallback to local pipeline |
| Vertex AI cold start latency | Medium | Low | Keep minimum instances, batch predictions |
| Cost overruns from unexpected usage | Medium | High | Set budget alerts, max instance limits, monitoring |
| Audio format compatibility issues | Low | Low | Validate formats upfront, clear error messages |

## Data Requirements

### Data Entities

- **Input:** Audio files (WAV, MP3, FLAC, OGG) up to 1 GB
- **Output:** ProcessingResult JSON with transcript and classification
- **Intermediate:** Temporary files during processing (auto-cleaned)

### Data Volume

- Expected: 10,000+ audio files per day
- Average file size: 10-50 MB
- Average duration: 5-30 minutes

### Data Retention

- Input files: Retained in input bucket (user-managed)
- Output files: Retained in output bucket indefinitely
- Logs: 30 days in Cloud Logging
- Failed messages: 7 days in dead letter queue

## User Stories

### As an operations analyst, I want to process audio files by uploading them to GCS so that I can get transcriptions without managing infrastructure

**Scenario 1:** Successful processing
- Given an audio file is uploaded to the input bucket
- When the processing pipeline completes
- Then a JSON result file appears in the output bucket with transcription and classification

**Scenario 2:** Unsupported format
- Given a file with unsupported extension (e.g., .xyz) is uploaded
- When the pipeline receives the event
- Then the request is rejected with a clear error message and no processing occurs

**Scenario 3:** Transient API failure
- Given a Speech-to-Text API call fails with a 503 error
- When the retry logic is triggered
- Then the request is retried up to 3 times with exponential backoff before failing to DLQ

### As a DevOps engineer, I want to monitor pipeline health so that I can respond to issues quickly

**Scenario 1:** Health check
- Given the Cloud Run service is deployed
- When I call GET /health
- Then I receive a 200 response with status "healthy"

**Scenario 2:** Error alerting
- Given the error rate exceeds 5% over 5 minutes
- When Cloud Monitoring evaluates the alert policy
- Then a notification is sent to the on-call channel

## Assumptions

- GCP project exists with billing enabled
- Service account with appropriate IAM roles is configured
- Network connectivity to GCP APIs is available
- Audio files uploaded to input bucket are valid and not corrupted
- Vertex AI endpoint for AudioSet classification is pre-deployed

## Questions and Open Issues

- [x] Speech-to-Text V1 vs V2? → V2 for better accuracy and native diarization
- [x] Cloud Functions vs Cloud Run? → Cloud Run for longer timeouts and container flexibility
- [ ] Vertex AI model: use pre-trained or fine-tune on domain data?
- [ ] Multi-language support: which languages to enable by default?

## Approval

- [ ] Product Owner review
- [ ] Technical Lead review
- [ ] Security review (if applicable)
- [ ] Ready for implementation
