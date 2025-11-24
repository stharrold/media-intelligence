# Security Best Practices

This document outlines security considerations and best practices for the Media Intelligence Pipeline.

## Overview

The pipeline processes potentially sensitive audio content. Following these practices ensures data protection and compliance.

## Authentication & Authorization

### Service Account Configuration

Use dedicated service accounts with minimal permissions:

```bash
# Create service account
gcloud iam service-accounts create media-processor \
    --description="Media Processor Service Account" \
    --display-name="Media Processor"

# Grant only required roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:media-processor@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/speech.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:media-processor@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin" \
    --condition="expression=resource.name.startsWith('projects/_/buckets/$PROJECT_ID-media'),title=Media buckets only"
```

### Required IAM Roles

| Role | Purpose |
|------|---------|
| `roles/speech.client` | Call Speech-to-Text API |
| `roles/storage.objectAdmin` | Read/write GCS objects |
| `roles/aiplatform.user` | Call Vertex AI endpoints |
| `roles/logging.logWriter` | Write logs |
| `roles/errorreporting.writer` | Report errors |

### API Authentication

Always require authentication for production:

```bash
# Remove public access
gcloud run services remove-iam-policy-binding media-processor \
    --region=$REGION \
    --member="allUsers" \
    --role="roles/run.invoker"

# Grant access to specific users/services
gcloud run services add-iam-policy-binding media-processor \
    --region=$REGION \
    --member="user:developer@company.com" \
    --role="roles/run.invoker"
```

## Data Encryption

### At Rest

All GCP services encrypt data at rest by default. For additional security:

```bash
# Create Customer-Managed Encryption Key (CMEK)
gcloud kms keyrings create media-intelligence \
    --location=us-central1

gcloud kms keys create media-key \
    --keyring=media-intelligence \
    --location=us-central1 \
    --purpose=encryption

# Use CMEK for Cloud Storage
gsutil kms encryption -k projects/$PROJECT_ID/locations/us-central1/keyRings/media-intelligence/cryptoKeys/media-key \
    gs://$PROJECT_ID-media-input

gsutil kms encryption -k projects/$PROJECT_ID/locations/us-central1/keyRings/media-intelligence/cryptoKeys/media-key \
    gs://$PROJECT_ID-media-output
```

### In Transit

All traffic uses TLS 1.2+:

```yaml
# Cloud Run enforces HTTPS
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/ingress: "all"  # or "internal" for VPC-only
```

## Network Security

### VPC Service Controls

Prevent data exfiltration:

```bash
# Create service perimeter
gcloud access-context-manager perimeters create media-intelligence-perimeter \
    --title="Media Intelligence Perimeter" \
    --resources="projects/$PROJECT_NUMBER" \
    --restricted-services="speech.googleapis.com,storage.googleapis.com" \
    --access-levels="accessPolicies/$POLICY_ID/accessLevels/trusted-locations"
```

### Private Google Access

Keep traffic within Google's network:

```bash
# Enable Private Google Access for subnet
gcloud compute networks subnets update default \
    --region=$REGION \
    --enable-private-ip-google-access
```

### Cloud Run Ingress

```bash
# Internal only (VPC traffic only)
gcloud run services update media-processor \
    --region=$REGION \
    --ingress=internal

# Internal and Cloud Load Balancing
gcloud run services update media-processor \
    --region=$REGION \
    --ingress=internal-and-cloud-load-balancing
```

## Secrets Management

### Use Secret Manager

Never store secrets in environment variables or code:

```bash
# Create secret
echo -n "api-key-value" | gcloud secrets create api-key --data-file=-

# Grant access to service account
gcloud secrets add-iam-policy-binding api-key \
    --member="serviceAccount:media-processor@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Access in Cloud Run
gcloud run services update media-processor \
    --set-secrets="API_KEY=api-key:latest"
```

### Environment Variable Security

```python
# Good: Use Secret Manager
from google.cloud import secretmanager

def get_secret(secret_id):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Bad: Hardcoded secrets
API_KEY = "sk-1234567890"  # Never do this!
```

## Audit Logging

### Enable Data Access Logs

```bash
# Enable audit logs for all services
gcloud projects set-iam-policy $PROJECT_ID policy.yaml

# policy.yaml
auditConfigs:
- auditLogConfigs:
  - logType: ADMIN_READ
  - logType: DATA_READ
  - logType: DATA_WRITE
  service: speech.googleapis.com
- auditLogConfigs:
  - logType: ADMIN_READ
  - logType: DATA_READ
  - logType: DATA_WRITE
  service: storage.googleapis.com
```

### Log Analysis

```bash
# View access logs
gcloud logging read 'resource.type="cloud_run_revision" AND protoPayload.methodName:"run.googleapis.com"' \
    --project=$PROJECT_ID \
    --limit=100

# Export logs for compliance
gcloud logging sinks create audit-sink \
    bigquery.googleapis.com/projects/$PROJECT_ID/datasets/audit_logs \
    --log-filter='logName:"cloudaudit.googleapis.com"'
```

## Data Privacy

### Data Retention

Configure lifecycle policies:

```json
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 30}
      }
    ]
  }
}
```

### Data Location

For compliance (GDPR, HIPAA):

```bash
# Deploy to specific region
gcloud run deploy media-processor \
    --region=europe-west1  # For GDPR

# Use regional storage
gsutil mb -l europe-west1 gs://$PROJECT_ID-media-eu
```

### Data Masking

For sensitive content detection:

```python
from google.cloud import dlp_v2

def mask_sensitive_data(text):
    dlp_client = dlp_v2.DlpServiceClient()

    item = {"value": text}
    inspect_config = {
        "info_types": [
            {"name": "EMAIL_ADDRESS"},
            {"name": "PHONE_NUMBER"},
            {"name": "CREDIT_CARD_NUMBER"},
        ]
    }
    deidentify_config = {
        "info_type_transformations": {
            "transformations": [{
                "primitive_transformation": {
                    "replace_config": {
                        "new_value": {"string_value": "[REDACTED]"}
                    }
                }
            }]
        }
    }

    response = dlp_client.deidentify_content(
        request={
            "parent": f"projects/{PROJECT_ID}",
            "deidentify_config": deidentify_config,
            "inspect_config": inspect_config,
            "item": item,
        }
    )

    return response.item.value
```

## Container Security

### Binary Authorization

Ensure only trusted images are deployed:

```bash
# Enable Binary Authorization
gcloud services enable binaryauthorization.googleapis.com

# Create policy
cat > policy.yaml << EOF
admissionWhitelistPatterns:
- namePattern: gcr.io/$PROJECT_ID/*
- namePattern: us-central1-docker.pkg.dev/$PROJECT_ID/*
defaultAdmissionRule:
  evaluationMode: REQUIRE_ATTESTATION
  enforcementMode: ENFORCED_BLOCK_AND_AUDIT_LOG
  requireAttestationsBy:
  - projects/$PROJECT_ID/attestors/built-by-cloud-build
EOF

gcloud container binauthz policy import policy.yaml
```

### Image Scanning

```bash
# Enable vulnerability scanning
gcloud artifacts docker images scan \
    $REGION-docker.pkg.dev/$PROJECT_ID/media-processor/media-processor:latest \
    --remote
```

### Non-Root Container

The Dockerfile runs as non-root:

```dockerfile
# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
```

## Compliance Frameworks

### HIPAA

For healthcare applications:

1. Sign BAA with Google Cloud
2. Use HIPAA-eligible services only
3. Enable audit logging
4. Implement access controls
5. Use encryption (CMEK recommended)

### GDPR

For EU data:

1. Deploy to EU regions
2. Implement data retention policies
3. Enable data subject access requests
4. Document processing activities

### SOC 2

1. Enable audit logging
2. Implement access controls
3. Regular security assessments
4. Incident response procedures

## Security Checklist

### Deployment

- [ ] Service account has minimal permissions
- [ ] Cloud Run requires authentication
- [ ] HTTPS enforced
- [ ] Audit logging enabled
- [ ] VPC Service Controls configured
- [ ] Binary Authorization enabled

### Data Protection

- [ ] CMEK enabled for storage
- [ ] Data retention policies set
- [ ] DLP scanning configured
- [ ] Regional deployment for compliance

### Monitoring

- [ ] Security alerts configured
- [ ] Log exports to SIEM
- [ ] Regular access reviews
- [ ] Vulnerability scanning enabled

## Incident Response

### Suspected Breach

1. **Contain**: Revoke compromised credentials
   ```bash
   gcloud iam service-accounts keys delete KEY_ID \
       --iam-account=SA_EMAIL
   ```

2. **Investigate**: Check audit logs
   ```bash
   gcloud logging read 'severity>=WARNING' --limit=1000
   ```

3. **Remediate**: Rotate secrets, update permissions

4. **Report**: Document and notify stakeholders

### Contact

For security issues, contact:
- Google Cloud Security: security@google.com
- Project Security Team: security@yourcompany.com
