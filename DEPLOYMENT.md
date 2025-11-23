# Deployment Guide

This guide covers deploying the Media Intelligence Pipeline to Google Cloud Platform.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [GCP Setup](#gcp-setup)
3. [Terraform Deployment](#terraform-deployment)
4. [Manual Deployment](#manual-deployment)
5. [CI/CD Setup](#cicd-setup)
6. [Post-Deployment Configuration](#post-deployment-configuration)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

```bash
# Google Cloud SDK
gcloud --version  # v400+

# Terraform
terraform --version  # v1.5+

# Docker (for local development)
docker --version  # v20+

# Python
python --version  # v3.11+
```

### GCP Permissions

The deploying user/service account needs these roles:

- `roles/owner` or a combination of:
  - `roles/storage.admin`
  - `roles/pubsub.admin`
  - `roles/run.admin`
  - `roles/iam.serviceAccountAdmin`
  - `roles/artifactregistry.admin`
  - `roles/cloudbuild.builds.editor`

## GCP Setup

### 1. Create or Select Project

```bash
# Create a new project
gcloud projects create $PROJECT_ID --name="Media Intelligence"

# Or select existing project
gcloud config set project $PROJECT_ID

# Enable billing (required for APIs)
gcloud alpha billing accounts list
gcloud alpha billing projects link $PROJECT_ID \
    --billing-account=BILLING_ACCOUNT_ID
```

### 2. Enable APIs

```bash
gcloud services enable \
    speech.googleapis.com \
    storage.googleapis.com \
    run.googleapis.com \
    cloudfunctions.googleapis.com \
    aiplatform.googleapis.com \
    cloudbuild.googleapis.com \
    pubsub.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com \
    firestore.googleapis.com \
    bigquery.googleapis.com \
    artifactregistry.googleapis.com
```

### 3. Set Up Authentication

```bash
# For local development
gcloud auth application-default login

# Create service account for production
gcloud iam service-accounts create media-processor \
    --display-name="Media Processor Service Account"

# Download key (for local testing only - use Workload Identity in production)
gcloud iam service-accounts keys create key.json \
    --iam-account=media-processor@$PROJECT_ID.iam.gserviceaccount.com
```

## Terraform Deployment

### 1. Configure Variables

Create `terraform/terraform.tfvars`:

```hcl
project_id = "your-project-id"
region     = "us-central1"

# Optional customization
min_instances = 0
max_instances = 10
cpu_limit     = "2"
memory_limit  = "4Gi"

# Enable additional services
enable_firestore = false
enable_bigquery  = false
```

### 2. Initialize and Apply

```bash
cd terraform

# Initialize Terraform
terraform init

# Review the plan
terraform plan -var-file="terraform.tfvars"

# Apply changes
terraform apply -var-file="terraform.tfvars"
```

### 3. Get Outputs

```bash
# View all outputs
terraform output

# Get specific values
terraform output cloud_run_url
terraform output input_bucket
terraform output output_bucket
```

## Manual Deployment

If you prefer not to use Terraform:

### 1. Create Storage Buckets

```bash
# Input bucket
gsutil mb -l $REGION gs://$PROJECT_ID-media-input
gsutil lifecycle set lifecycle.json gs://$PROJECT_ID-media-input

# Output bucket
gsutil mb -l $REGION gs://$PROJECT_ID-media-output
```

### 2. Create Pub/Sub Topic

```bash
gcloud pubsub topics create media-upload

# Create notification
gsutil notification create \
    -t media-upload \
    -f json \
    -e OBJECT_FINALIZE \
    gs://$PROJECT_ID-media-input
```

### 3. Build and Push Container

```bash
# Create Artifact Registry repository
gcloud artifacts repositories create media-processor \
    --repository-format=docker \
    --location=$REGION

# Build and push
gcloud builds submit \
    --tag $REGION-docker.pkg.dev/$PROJECT_ID/media-processor/media-processor:latest
```

### 4. Deploy Cloud Run

```bash
gcloud run deploy media-processor \
    --image $REGION-docker.pkg.dev/$PROJECT_ID/media-processor/media-processor:latest \
    --platform managed \
    --region $REGION \
    --memory 4Gi \
    --cpu 2 \
    --timeout 3600 \
    --min-instances 0 \
    --max-instances 10 \
    --service-account media-processor@$PROJECT_ID.iam.gserviceaccount.com \
    --set-env-vars "PROJECT_ID=$PROJECT_ID,OUTPUT_BUCKET=$PROJECT_ID-media-output"
```

## CI/CD Setup

### Cloud Build Trigger

```bash
# Connect GitHub repository
gcloud source repos create media-intelligence

# Create trigger
gcloud builds triggers create github \
    --name="media-processor-deploy" \
    --repo-name="media-intelligence" \
    --repo-owner="your-org" \
    --branch-pattern="^main$" \
    --build-config="cloudbuild.yaml"
```

### GitHub Actions Alternative

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - uses: google-github-actions/setup-gcloud@v1

      - name: Build and Deploy
        run: |
          gcloud builds submit --config cloudbuild.yaml
```

## Post-Deployment Configuration

### 1. Configure Vertex AI (Optional)

For situation classification, train an AutoML model:

```bash
# Create dataset
gcloud ai custom-jobs create \
    --region=$REGION \
    --display-name=audio-situation-training \
    --config=automl_config.yaml

# After training, get endpoint ID
gcloud ai endpoints list --region=$REGION
```

Update the deployment with the endpoint ID:

```bash
gcloud run services update media-processor \
    --region $REGION \
    --set-env-vars "VERTEX_AI_ENDPOINT_ID=your-endpoint-id"
```

### 2. Configure Domain (Optional)

```bash
# Map custom domain
gcloud beta run domain-mappings create \
    --service media-processor \
    --domain api.yourdomain.com \
    --region $REGION
```

### 3. Set Up Alerts

```bash
# Create notification channel
gcloud alpha monitoring channels create \
    --display-name="Media Processor Alerts" \
    --type=email \
    --channel-labels=email_address=alerts@yourdomain.com

# Create alert policy
gcloud alpha monitoring policies create \
    --display-name="High Error Rate" \
    --condition-display-name="Error rate > 1%" \
    --condition-filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count" AND metric.labels.response_code_class="5xx"'
```

## Monitoring

### Cloud Console

- [Cloud Run Dashboard](https://console.cloud.google.com/run)
- [Cloud Logging](https://console.cloud.google.com/logs)
- [Error Reporting](https://console.cloud.google.com/errors)

### CLI Commands

```bash
# View logs
gcloud run services logs read media-processor --region $REGION

# View metrics
gcloud monitoring metrics list --filter="resource.type=cloud_run_revision"

# Check service status
gcloud run services describe media-processor --region $REGION
```

## Troubleshooting

### Common Issues

#### 1. Permission Denied

```bash
# Check IAM bindings
gcloud projects get-iam-policy $PROJECT_ID

# Add missing role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:media-processor@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/speech.client"
```

#### 2. Container Fails to Start

```bash
# Check container logs
gcloud run revisions logs media-processor-00001 --region $REGION

# Test locally
docker build -t media-processor .
docker run -p 8080:8080 \
    -e PROJECT_ID=$PROJECT_ID \
    -e GOOGLE_APPLICATION_CREDENTIALS=/key.json \
    -v $(pwd)/key.json:/key.json \
    media-processor
```

#### 3. Pub/Sub Not Triggering

```bash
# Verify notification
gsutil notification list gs://$PROJECT_ID-media-input

# Check subscription
gcloud pubsub subscriptions list

# Test manually
gcloud pubsub topics publish media-upload \
    --message='{"bucket":"test","name":"test.wav"}'
```

#### 4. Speech API Errors

```bash
# Verify API is enabled
gcloud services list --enabled | grep speech

# Check quotas
gcloud compute project-info describe --project $PROJECT_ID
```

### Performance Tuning

#### Increase Processing Speed

```bash
# Increase CPU/Memory
gcloud run services update media-processor \
    --region $REGION \
    --cpu 4 \
    --memory 8Gi

# Keep instances warm
gcloud run services update media-processor \
    --region $REGION \
    --min-instances 1
```

#### Reduce Costs

```bash
# Use shorter timeout
gcloud run services update media-processor \
    --region $REGION \
    --timeout 600

# Enable CPU throttling
gcloud run services update media-processor \
    --region $REGION \
    --cpu-throttling
```

## Cleanup

To delete all resources:

```bash
# Using Terraform
cd terraform
terraform destroy -var-file="terraform.tfvars"

# Or manually
gcloud run services delete media-processor --region $REGION --quiet
gsutil rm -r gs://$PROJECT_ID-media-input
gsutil rm -r gs://$PROJECT_ID-media-output
gcloud pubsub topics delete media-upload --quiet
```
