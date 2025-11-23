#!/bin/bash
# Media Intelligence Pipeline - Deployment Script
# Usage: ./deploy.sh [--project PROJECT_ID] [--region REGION] [--terraform-only] [--cloud-run-only]

set -e

# Default values
PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-us-central1}"
TERRAFORM_ONLY=false
CLOUD_RUN_ONLY=false
SKIP_BUILD=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --project)
            PROJECT_ID="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --terraform-only)
            TERRAFORM_ONLY=true
            shift
            ;;
        --cloud-run-only)
            CLOUD_RUN_ONLY=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--project PROJECT_ID] [--region REGION] [--terraform-only] [--cloud-run-only] [--skip-build]"
            echo ""
            echo "Options:"
            echo "  --project        GCP Project ID (required)"
            echo "  --region         GCP Region (default: us-central1)"
            echo "  --terraform-only Only run Terraform deployment"
            echo "  --cloud-run-only Only deploy Cloud Run service"
            echo "  --skip-build     Skip container build (use existing image)"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Validate project ID
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: PROJECT_ID is required${NC}"
    echo "Set it via --project flag or PROJECT_ID environment variable"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Media Intelligence Pipeline Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Set gcloud project
echo -e "${YELLOW}Setting gcloud project...${NC}"
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo -e "${YELLOW}Enabling required APIs...${NC}"
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
    artifactregistry.googleapis.com \
    --quiet

# Deploy Terraform infrastructure
if [ "$CLOUD_RUN_ONLY" = false ]; then
    echo -e "${YELLOW}Deploying Terraform infrastructure...${NC}"
    cd terraform

    # Initialize Terraform
    terraform init

    # Plan and apply
    terraform plan \
        -var="project_id=$PROJECT_ID" \
        -var="region=$REGION" \
        -out=tfplan

    terraform apply tfplan

    cd ..

    echo -e "${GREEN}Terraform deployment complete${NC}"
fi

# Build and deploy Cloud Run
if [ "$TERRAFORM_ONLY" = false ]; then
    # Create Artifact Registry repository if it doesn't exist
    echo -e "${YELLOW}Ensuring Artifact Registry repository exists...${NC}"
    gcloud artifacts repositories describe media-processor \
        --location="$REGION" 2>/dev/null || \
    gcloud artifacts repositories create media-processor \
        --repository-format=docker \
        --location="$REGION" \
        --description="Media processor Docker images"

    if [ "$SKIP_BUILD" = false ]; then
        echo -e "${YELLOW}Building container image...${NC}"
        gcloud builds submit \
            --tag "$REGION-docker.pkg.dev/$PROJECT_ID/media-processor/media-processor:latest" \
            --quiet
    fi

    echo -e "${YELLOW}Deploying to Cloud Run...${NC}"
    gcloud run deploy media-processor \
        --image "$REGION-docker.pkg.dev/$PROJECT_ID/media-processor/media-processor:latest" \
        --platform managed \
        --region "$REGION" \
        --memory 4Gi \
        --cpu 2 \
        --timeout 3600 \
        --min-instances 0 \
        --max-instances 10 \
        --service-account "media-processor@$PROJECT_ID.iam.gserviceaccount.com" \
        --set-env-vars "PROJECT_ID=$PROJECT_ID,REGION=$REGION,OUTPUT_BUCKET=$PROJECT_ID-media-output,LOG_LEVEL=INFO,ENABLE_STRUCTURED_LOGGING=true" \
        --quiet

    echo -e "${GREEN}Cloud Run deployment complete${NC}"
fi

# Get service URL
SERVICE_URL=$(gcloud run services describe media-processor \
    --region "$REGION" \
    --format 'value(status.url)')

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Cloud Run URL: $SERVICE_URL"
echo ""
echo "Input Bucket: gs://$PROJECT_ID-media-input"
echo "Output Bucket: gs://$PROJECT_ID-media-output"
echo ""
echo "Test the deployment:"
echo "  curl $SERVICE_URL/health"
echo ""
echo "Process an audio file:"
echo "  gsutil cp your-audio.wav gs://$PROJECT_ID-media-input/"
echo ""
echo "Or use the API directly:"
echo "  curl -X POST $SERVICE_URL/process \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"gcs_uri\": \"gs://$PROJECT_ID-media-input/your-audio.wav\"}'"
