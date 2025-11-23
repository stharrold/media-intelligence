# API Documentation

The Media Intelligence Pipeline exposes a REST API via Cloud Run.

## Base URL

```
https://media-processor-{hash}-{region}.a.run.app
```

Get your service URL:
```bash
gcloud run services describe media-processor \
    --region us-central1 \
    --format 'value(status.url)'
```

## Authentication

By default, Cloud Run requires authentication. Options:

### 1. Identity Token (Recommended)

```bash
TOKEN=$(gcloud auth print-identity-token)
curl -H "Authorization: Bearer $TOKEN" $SERVICE_URL/health
```

### 2. Service Account

```bash
TOKEN=$(gcloud auth print-identity-token \
    --impersonate-service-account=client@project.iam.gserviceaccount.com)
curl -H "Authorization: Bearer $TOKEN" $SERVICE_URL/process
```

### 3. Allow Unauthenticated (Development Only)

```bash
gcloud run services add-iam-policy-binding media-processor \
    --region us-central1 \
    --member="allUsers" \
    --role="roles/run.invoker"
```

## Endpoints

### Health Check

```
GET /health
```

Returns the service health status.

**Response:**
```json
{
    "status": "healthy",
    "service": "media-intelligence"
}
```

### Readiness Check

```
GET /ready
```

Returns whether the service is ready to accept requests.

**Response:**
```json
{
    "status": "ready"
}
```

### Process Single File

```
POST /process
```

Process a single audio file from Google Cloud Storage.

**Request Body:**
```json
{
    "gcs_uri": "gs://bucket/path/to/audio.wav",
    "output_bucket": "output-bucket-name",
    "config": {
        "language_code": "en-US",
        "model": "long",
        "min_speakers": 2,
        "max_speakers": 6
    }
}
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `gcs_uri` | string | Yes | GCS URI of the input audio file |
| `output_bucket` | string | No | Override output bucket |
| `config` | object | No | Processing configuration |

**Config Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `language_code` | string | `en-US` | Language code for transcription |
| `model` | string | `long` | Speech model: `long`, `short`, `telephony`, `video` |
| `min_speakers` | integer | 2 | Minimum number of speakers for diarization |
| `max_speakers` | integer | 6 | Maximum number of speakers for diarization |

**Success Response (200):**
```json
{
    "status": "success",
    "file_id": "20231201_123456_abc12345",
    "result_uri": "gs://output-bucket/results/20231201_123456_abc12345.json",
    "transcript_uri": "gs://output-bucket/transcripts/20231201_123456_abc12345.txt",
    "processing_time": 12.34,
    "cost_estimate": {
        "speech_to_text": 0.036,
        "situation_classification": 0.006,
        "storage": 0.001,
        "total": 0.043
    },
    "summary": {
        "duration": 60.5,
        "speaker_count": 2,
        "overall_situation": "meeting",
        "overall_situation_confidence": 0.85,
        "segment_count": 15
    }
}
```

**Error Response (400/500):**
```json
{
    "status": "error",
    "error": "File not found: gs://bucket/nonexistent.wav"
}
```

### Process Batch

```
POST /batch
```

Process multiple audio files.

**Request Body:**
```json
{
    "gcs_uris": [
        "gs://bucket/audio1.wav",
        "gs://bucket/audio2.wav"
    ],
    "output_bucket": "output-bucket-name",
    "config": {}
}
```

**Success Response (200):**
```json
{
    "status": "success",
    "results": [
        {
            "gcs_uri": "gs://bucket/audio1.wav",
            "status": "success",
            "file_id": "20231201_123456_abc12345",
            "result_uri": "gs://output-bucket/results/abc12345.json",
            "transcript_uri": "gs://output-bucket/transcripts/abc12345.txt"
        },
        {
            "gcs_uri": "gs://bucket/audio2.wav",
            "status": "error",
            "error": "Unsupported format"
        }
    ],
    "summary": {
        "total": 2,
        "successful": 1,
        "failed": 1
    }
}
```

### Service Info

```
GET /
```

Returns API information.

**Response:**
```json
{
    "service": "media-intelligence",
    "version": "1.0.0",
    "endpoints": {
        "POST /process": "Process a single audio file",
        "POST /batch": "Process multiple audio files",
        "GET /health": "Health check",
        "GET /ready": "Readiness check"
    }
}
```

## Output Formats

### JSON Result

Location: `gs://{output_bucket}/results/{file_id}.json`

```json
{
    "gcs_input_uri": "gs://input/audio.wav",
    "gcs_output_uri": "gs://output/results/abc.json",
    "file_id": "20231201_123456_abc12345",
    "duration": 62.5,
    "transcript_segments": [
        {
            "start_time": 0.0,
            "end_time": 5.2,
            "text": "Hello, welcome to the meeting.",
            "speaker_tag": 0,
            "confidence": 0.95,
            "language_code": "en-US",
            "words": [
                {
                    "word": "Hello",
                    "start_time": 0.0,
                    "end_time": 0.5,
                    "confidence": 0.98
                }
            ]
        }
    ],
    "situation_predictions": [
        {
            "situation": "meeting",
            "confidence": 0.87,
            "start_time": 0.0,
            "end_time": 30.0,
            "all_scores": {
                "meeting": 0.87,
                "office": 0.10,
                "quiet": 0.03
            }
        }
    ],
    "speaker_count": 2,
    "overall_situation": "meeting",
    "overall_situation_confidence": 0.85,
    "processing_time": 12.34,
    "cost_estimate": {
        "speech_to_text": 0.036,
        "situation_classification": 0.006,
        "total": 0.043
    },
    "metadata": {
        "input_file": "gs://input/audio.wav",
        "processed_at": "2023-12-01T12:34:56.789Z",
        "model_used": "long",
        "language_code": "en-US",
        "diarization_enabled": true
    }
}
```

### Text Transcript

Location: `gs://{output_bucket}/transcripts/{file_id}.txt`

```
[00:00:00.000] Speaker 1: Hello, welcome to the meeting.
[00:00:05.200] Speaker 1: Today we'll discuss the project timeline.
[00:00:12.500] Speaker 2: Thanks for having me.
[00:00:15.800] Speaker 2: I have some updates on the development progress.
```

## Error Codes

| HTTP Status | Error | Description |
|-------------|-------|-------------|
| 400 | Bad Request | Invalid request body or missing required fields |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | File not found in GCS |
| 413 | Payload Too Large | Audio file exceeds maximum duration |
| 415 | Unsupported Media Type | Unsupported audio format |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Processing failed |
| 503 | Service Unavailable | Service temporarily unavailable |

## Rate Limits

Cloud Run handles auto-scaling, but consider these limits:

- **Speech-to-Text API**: 300 requests/minute (default quota)
- **Cloud Run**: 80 concurrent requests per instance
- **File Size**: Up to 480 minutes of audio per request

## Examples

### Python

```python
import requests

SERVICE_URL = "https://media-processor-xxx.a.run.app"

# Get identity token
import google.auth.transport.requests
import google.oauth2.id_token

request = google.auth.transport.requests.Request()
token = google.oauth2.id_token.fetch_id_token(request, SERVICE_URL)

# Process file
response = requests.post(
    f"{SERVICE_URL}/process",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "gcs_uri": "gs://my-bucket/audio.wav",
        "config": {"language_code": "en-US"}
    }
)

result = response.json()
print(f"Transcript: {result['transcript_uri']}")
```

### Node.js

```javascript
const { GoogleAuth } = require('google-auth-library');
const fetch = require('node-fetch');

const SERVICE_URL = 'https://media-processor-xxx.a.run.app';

async function processAudio() {
    const auth = new GoogleAuth();
    const client = await auth.getIdTokenClient(SERVICE_URL);
    const headers = await client.getRequestHeaders();

    const response = await fetch(`${SERVICE_URL}/process`, {
        method: 'POST',
        headers: {
            ...headers,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            gcs_uri: 'gs://my-bucket/audio.wav'
        })
    });

    return response.json();
}
```

### cURL

```bash
# Get token
TOKEN=$(gcloud auth print-identity-token)

# Process file
curl -X POST "$SERVICE_URL/process" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "gcs_uri": "gs://my-bucket/audio.wav",
        "config": {
            "language_code": "en-US",
            "model": "long"
        }
    }'
```
