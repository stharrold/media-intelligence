# Quick Start Guide

Get the Media Intelligence Pipeline running in 5 minutes.

## Prerequisites

- Google Cloud account with billing enabled
- `gcloud` CLI installed and authenticated
- Python 3.11+

## Step 1: Set Up GCP Project

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
export REGION="us-central1"

# Login and set project
gcloud auth login
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
    speech.googleapis.com \
    storage.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    pubsub.googleapis.com \
    artifactregistry.googleapis.com
```

## Step 2: Deploy

```bash
# Clone the repository
git clone https://github.com/your-org/media-intelligence-gcp.git
cd media-intelligence-gcp

# Run the deployment script
./deploy.sh --project $PROJECT_ID --region $REGION
```

This will:
1. Create Cloud Storage buckets for input/output
2. Set up Pub/Sub topics for event-driven processing
3. Build and deploy the Cloud Run service
4. Configure IAM permissions

## Step 3: Process Your First Audio File

```bash
# Upload an audio file
gsutil cp your-audio.wav gs://$PROJECT_ID-media-input/

# Wait a few seconds for processing...

# Check the results
gsutil ls gs://$PROJECT_ID-media-output/results/
gsutil ls gs://$PROJECT_ID-media-output/transcripts/
```

## Step 4: View Results

```bash
# Download the JSON result
gsutil cp gs://$PROJECT_ID-media-output/results/*.json ./

# Or download the transcript
gsutil cp gs://$PROJECT_ID-media-output/transcripts/*.txt ./
```

## Using the API Directly

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe media-processor \
    --region $REGION --format 'value(status.url)')

# Process a specific file
curl -X POST "$SERVICE_URL/process" \
    -H "Content-Type: application/json" \
    -d '{
        "gcs_uri": "gs://'"$PROJECT_ID"'-media-input/your-audio.wav"
    }'
```

## Example Response

```json
{
    "status": "success",
    "file_id": "20231201_143052_a1b2c3d4",
    "result_uri": "gs://your-project-media-output/results/20231201_143052_a1b2c3d4.json",
    "transcript_uri": "gs://your-project-media-output/transcripts/20231201_143052_a1b2c3d4.txt",
    "processing_time": 8.42,
    "summary": {
        "duration": 62.5,
        "speaker_count": 2,
        "overall_situation": "meeting"
    }
}
```

## Configuration Options

Customize processing by passing a config object:

```bash
curl -X POST "$SERVICE_URL/process" \
    -H "Content-Type: application/json" \
    -d '{
        "gcs_uri": "gs://bucket/audio.wav",
        "config": {
            "language_code": "en-US",
            "model": "long",
            "min_speakers": 2,
            "max_speakers": 6
        }
    }'
```

### Available Models

| Model | Use Case |
|-------|----------|
| `long` | Recordings > 60 seconds (default) |
| `short` | Recordings < 60 seconds |
| `telephony` | Phone calls |
| `video` | Video soundtracks |

## Next Steps

- Read the full [Deployment Guide](DEPLOYMENT.md)
- Check the [API Documentation](docs/API.md)
- Review [Cost Analysis](docs/COST_ANALYSIS.md)
- Configure [Terraform variables](terraform/variables.tf) for production

## Troubleshooting

### "Permission denied" errors

Ensure the service account has the required permissions:

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:media-processor@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/speech.client"
```

### File not processing

Check Cloud Run logs:

```bash
gcloud run services logs read media-processor --region $REGION
```

### Slow processing

- Check if you're using the correct model (use `short` for files < 60s)
- Ensure the audio format is supported
- Check Cloud Run scaling settings

## Need Help?

- [Full Documentation](README.md)
- [GitHub Issues](https://github.com/your-org/media-intelligence-gcp/issues)
