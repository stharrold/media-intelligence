# Media Intelligence Pipeline (GCP)

A cloud-native media processing pipeline using Google Cloud Platform managed services for audio transcription, speaker diarization, and situation detection.

## Features

- **Transcription**: Google Cloud Speech-to-Text V2 with enhanced models
- **Speaker Diarization**: Built-in speaker identification (2-6 speakers)
- **Situation Detection**: Vertex AI AutoML for acoustic scene classification
- **Batch & Streaming**: Process files from GCS or real-time audio streams
- **Multiple Output Formats**: JSON (structured), TXT (human-readable), BigQuery export
- **Serverless Architecture**: Auto-scaling Cloud Run deployment
- **Event-Driven Processing**: GCS triggers via Pub/Sub

## Quick Start

See [QUICKSTART.md](QUICKSTART.md) for a 5-minute getting started guide.

## Architecture

```
Input Audio (GCS: gs://bucket/input/*.{wav,mp3,m4a,flac,opus})
    │
    ├──► Cloud Storage Trigger
    │    └─► Pub/Sub Topic: "media-upload"
    │
    ▼
Cloud Run: Media Processor
    │
    ├──────────────┬──────────────┬─────────────
    │              │              │             │
    ▼              ▼              ▼             ▼
Speech-to-Text   (built-in      Vertex AI     (Future)
API V2           diarization)    AutoML        Video
Enhanced Model                   Audio         Intelligence
+ Speaker                        Classifier    API
  Diarization
    │              │              │             │
    └──────────────┴──────────────┴─────────────┘
                │
                ▼
         Output Storage
                │
    ┌───────────┼───────────┐
    │           │           │
    ▼           ▼           ▼
Cloud Storage BigQuery   Firestore
(JSON/TXT)   (Analytics) (Metadata)
```

## Project Structure

```
media-intelligence-gcp/
├── LICENSE                     # Apache 2.0 license
├── README.md                   # This file
├── QUICKSTART.md              # 5-minute getting started guide
├── DEPLOYMENT.md              # Full deployment guide
│
├── requirements.txt           # Python dependencies
├── Containerfile.gcp          # Cloud Run container (OCI)
├── cloudbuild.yaml           # Cloud Build CI/CD
│
├── terraform/                 # Infrastructure as Code
│   ├── main.tf               # Main infrastructure
│   ├── variables.tf          # Configuration variables
│   ├── outputs.tf            # Output values
│   └── iam.tf                # IAM configuration
│
├── .env.example              # Environment template
├── config.yaml               # Processing configuration
│
├── deploy.sh                 # Automated deployment
├── test.sh                   # Test runner
│
├── src/
│   ├── __init__.py
│   ├── main.py               # Cloud Run entry point
│   ├── audio_processor.py    # Main orchestrator
│   ├── speech_client.py      # Speech-to-Text wrapper
│   ├── situation_classifier.py # Vertex AI client
│   ├── storage_manager.py    # GCS operations
│   └── utils.py              # Shared utilities
│
├── tests/
│   ├── __init__.py
│   ├── test_speech_client.py
│   ├── test_situation_classifier.py
│   └── test_integration.py
│
└── docs/
    ├── API.md                # API documentation
    ├── COST_ANALYSIS.md      # Cost breakdown
    └── SECURITY.md           # Security best practices
```

## Requirements

### Platform
- Python 3.11+
- Docker (for local development)
- Google Cloud SDK (`gcloud`)
- Terraform 1.5+ (for infrastructure deployment)

### GCP Services
- Cloud Run
- Cloud Storage
- Speech-to-Text API
- Vertex AI
- Pub/Sub
- Cloud Build
- Artifact Registry

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/media-intelligence-gcp.git
cd media-intelligence-gcp
```

### 2. Set Up Python Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 3. Configure GCP

```bash
# Login to GCP
gcloud auth login
gcloud auth application-default login

# Set project
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable APIs
gcloud services enable speech.googleapis.com storage.googleapis.com \
    run.googleapis.com aiplatform.googleapis.com cloudbuild.googleapis.com \
    pubsub.googleapis.com
```

### 4. Deploy Infrastructure

```bash
# Using the deploy script
./deploy.sh --project $PROJECT_ID --region us-central1

# Or using Terraform directly
cd terraform
terraform init
terraform apply -var="project_id=$PROJECT_ID"
```

## Usage

### Process a Single File

```bash
# Upload audio file
gsutil cp your-audio.wav gs://$PROJECT_ID-media-input/

# The file will be automatically processed via Pub/Sub trigger
# Results appear in gs://$PROJECT_ID-media-output/
```

### Process via API

```bash
# Get the Cloud Run URL
SERVICE_URL=$(gcloud run services describe media-processor \
    --region us-central1 --format 'value(status.url)')

# Process a file
curl -X POST "$SERVICE_URL/process" \
    -H "Content-Type: application/json" \
    -d '{
        "gcs_uri": "gs://your-bucket/audio.wav",
        "config": {
            "language_code": "en-US",
            "min_speakers": 2,
            "max_speakers": 4
        }
    }'
```

### Response Format

```json
{
    "status": "success",
    "file_id": "20231201_123456_abc12345",
    "result_uri": "gs://bucket/results/20231201_123456_abc12345.json",
    "transcript_uri": "gs://bucket/transcripts/20231201_123456_abc12345.txt",
    "processing_time": 12.34,
    "cost_estimate": {
        "speech_to_text": 0.036,
        "situation_classification": 0.006,
        "total": 0.043
    },
    "summary": {
        "duration": 60.5,
        "speaker_count": 2,
        "overall_situation": "meeting"
    }
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROJECT_ID` | GCP Project ID | Required |
| `REGION` | GCP Region | `us-central1` |
| `INPUT_BUCKET` | Input storage bucket | `{PROJECT_ID}-media-input` |
| `OUTPUT_BUCKET` | Output storage bucket | `{PROJECT_ID}-media-output` |
| `VERTEX_AI_ENDPOINT_ID` | Vertex AI endpoint for situation classification | Optional |
| `LOG_LEVEL` | Logging level | `INFO` |

### Processing Options

See `config.yaml` for all configuration options:

```yaml
speech:
  model: long  # long, short, telephony, video
  language_codes:
    - en-US
  diarization:
    enabled: true
    min_speaker_count: 2
    max_speaker_count: 6

situation:
  enabled: true
  labels:
    - airplane
    - car
    - meeting
    - office
    - outdoor
    - quiet
```

## Supported Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| WAV | `.wav` | Recommended |
| MP3 | `.mp3` | Compressed audio |
| M4A | `.m4a` | Apple format |
| FLAC | `.flac` | Lossless |
| Opus | `.opus` | Efficient codec |
| OGG | `.ogg` | Open format |
| AAC | `.aac` | Advanced Audio Coding |

## Performance

| Metric | Target | Notes |
|--------|--------|-------|
| Processing Speed | <10s for 60s audio | Batch mode |
| Transcription WER | 7-12% | Enhanced models |
| Diarization DER | 10-15% | 2-6 speakers |
| Scalability | 100+ concurrent | Auto-scaling |
| Availability | 99.9% | Cloud Run SLA |

## Cost Estimation

For 10,000 recordings (average 3 minutes each):

| Service | Monthly Cost |
|---------|--------------|
| Speech-to-Text V2 | ~$1,080 |
| Vertex AI | ~$18 |
| Cloud Storage | ~$1 |
| Cloud Run | ~$7 |
| **Total** | **~$1,108** |

See [docs/COST_ANALYSIS.md](docs/COST_ANALYSIS.md) for detailed breakdown.

## Testing

```bash
# Run unit tests
./test.sh --unit

# Run integration tests (requires GCP credentials)
export PROJECT_ID="your-project-id"
./test.sh --integration

# Run all tests
./test.sh --all
```

## Documentation

- [QUICKSTART.md](QUICKSTART.md) - Get started in 5 minutes
- [DEPLOYMENT.md](DEPLOYMENT.md) - Full deployment guide
- [docs/API.md](docs/API.md) - API reference
- [docs/COST_ANALYSIS.md](docs/COST_ANALYSIS.md) - Cost breakdown
- [docs/SECURITY.md](docs/SECURITY.md) - Security best practices

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Support

- [GitHub Issues](https://github.com/your-org/media-intelligence-gcp/issues)
- [Documentation](docs/)
