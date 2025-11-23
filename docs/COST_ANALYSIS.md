# Cost Analysis

This document provides a detailed breakdown of costs for running the Media Intelligence Pipeline on GCP.

## Pricing Overview (as of November 2024)

### Speech-to-Text V2

| Feature | Price | Notes |
|---------|-------|-------|
| Standard recognition | $0.006/15 seconds | Basic transcription |
| Enhanced recognition | $0.009/15 seconds | Improved accuracy |
| Speaker diarization | Included | With enhanced models |
| Data logging | $0.004/15 seconds | Optional |

### Vertex AI

| Feature | Price | Notes |
|---------|-------|-------|
| AutoML Audio prediction | $0.30/1,000 predictions | Per API call |
| Training | $3.15/node hour | For custom models |

### Cloud Storage

| Feature | Price | Notes |
|---------|-------|-------|
| Standard storage | $0.020/GB/month | us-central1 |
| Class A operations (write) | $0.05/10,000 | Upload, copy |
| Class B operations (read) | $0.004/10,000 | Download, list |
| Network egress | $0.12/GB | To internet |

### Cloud Run

| Feature | Price | Notes |
|---------|-------|-------|
| vCPU | $0.00002400/vCPU-second | Per second billing |
| Memory | $0.00000250/GiB-second | Per second billing |
| Requests | $0.40/million | Per request |

### Pub/Sub

| Feature | Price | Notes |
|---------|-------|-------|
| Message delivery | $40/TiB | First 10 GiB free |

## Cost Calculator

### Per-Recording Costs

For a **3-minute (180 second) audio recording**:

| Component | Calculation | Cost |
|-----------|-------------|------|
| Speech-to-Text (Enhanced) | 12 × $0.009 | $0.108 |
| Vertex AI (6 segments) | 6 × $0.0003 | $0.0018 |
| Cloud Storage (10 MB) | ~$0.0002 | $0.0002 |
| Cloud Run (15s @ 2 vCPU, 4GB) | 15 × $0.0001 | $0.0015 |
| **Total per recording** | | **$0.1115** |

### Monthly Cost Examples

#### Small Scale: 1,000 recordings/month

| Component | Monthly Cost |
|-----------|--------------|
| Speech-to-Text | $108 |
| Vertex AI | $1.80 |
| Cloud Storage | $0.50 |
| Cloud Run | $1.50 |
| Pub/Sub | Free tier |
| **Total** | **~$112/month** |

#### Medium Scale: 10,000 recordings/month

| Component | Monthly Cost |
|-----------|--------------|
| Speech-to-Text | $1,080 |
| Vertex AI | $18 |
| Cloud Storage | $5 |
| Cloud Run | $15 |
| Pub/Sub | $0.40 |
| **Total** | **~$1,118/month** |

#### Large Scale: 100,000 recordings/month

| Component | Monthly Cost |
|-----------|--------------|
| Speech-to-Text | $10,800 |
| Vertex AI | $180 |
| Cloud Storage | $50 |
| Cloud Run | $150 |
| Pub/Sub | $4 |
| Networking | $24 |
| **Total** | **~$11,208/month** |

## Cost Breakdown by Audio Duration

| Duration | Speech-to-Text | Vertex AI | Total |
|----------|---------------|-----------|-------|
| 30 sec | $0.018 | $0.0003 | ~$0.02 |
| 1 min | $0.036 | $0.0006 | ~$0.04 |
| 3 min | $0.108 | $0.0018 | ~$0.11 |
| 5 min | $0.180 | $0.0030 | ~$0.18 |
| 10 min | $0.360 | $0.0060 | ~$0.37 |
| 30 min | $1.080 | $0.0180 | ~$1.10 |
| 1 hour | $2.160 | $0.0360 | ~$2.20 |

## Cost Optimization Strategies

### 1. Use Appropriate Models

| Model | Best For | Cost Savings |
|-------|----------|--------------|
| `short` | < 60 second recordings | ~10% faster |
| `long` | > 60 second recordings | Optimized |
| `telephony` | Phone calls (8kHz) | Better accuracy |

### 2. Disable Unused Features

```yaml
# config.yaml
speech:
  features:
    enable_word_confidence: false  # Disable if not needed
    enable_word_time_offsets: false  # Disable if not needed

situation:
  enabled: false  # Skip situation classification
```

Savings: ~15-20% per recording

### 3. Batch Processing

Process files in batches to reduce Cloud Run overhead:

```bash
# Instead of individual requests
curl /process -d '{"gcs_uri": "file1.wav"}'
curl /process -d '{"gcs_uri": "file2.wav"}'

# Use batch endpoint
curl /batch -d '{"gcs_uris": ["file1.wav", "file2.wav"]}'
```

Savings: ~5-10% on Cloud Run costs

### 4. Lifecycle Policies

Automatically delete old files:

```bash
gsutil lifecycle set lifecycle.json gs://bucket

# lifecycle.json
{
  "rule": [{
    "action": {"type": "Delete"},
    "condition": {"age": 30}
  }]
}
```

Savings: Variable based on storage

### 5. Regional vs Multi-Regional Storage

| Type | Price | Use Case |
|------|-------|----------|
| Regional | $0.020/GB | Single region access |
| Multi-regional | $0.026/GB | Global access |
| Nearline | $0.010/GB | Infrequent access |
| Coldline | $0.004/GB | Archival |

### 6. Committed Use Discounts

For predictable workloads:

| Commitment | Cloud Run Discount |
|------------|-------------------|
| 1 year | 17% |
| 3 years | 28% |

### 7. Min Instances Optimization

```bash
# Development: No min instances
gcloud run services update media-processor --min-instances 0

# Production: Keep warm for faster response
gcloud run services update media-processor --min-instances 1
```

Cold start cost: ~$0.01/day for 1 instance kept warm

## Free Tier Allowances

### Monthly Free Tier

| Service | Free Allowance |
|---------|----------------|
| Cloud Run | 180,000 vCPU-seconds |
| Cloud Run | 360,000 GiB-seconds |
| Cloud Storage | 5 GB |
| Speech-to-Text | 60 minutes |
| Pub/Sub | 10 GB |

### Always Free

- Cloud Logging: 50 GB/month
- Cloud Monitoring: 150 MB metrics
- Error Reporting: Unlimited

## Cost Monitoring

### Set Up Budget Alerts

```bash
gcloud billing budgets create \
    --billing-account=ACCOUNT_ID \
    --display-name="Media Intelligence Budget" \
    --budget-amount=1000USD \
    --threshold-rules=percent=50,basis=current-spend \
    --threshold-rules=percent=90,basis=current-spend \
    --threshold-rules=percent=100,basis=forecasted-spend
```

### View Costs by Service

```bash
# Export billing to BigQuery
bq query --use_legacy_sql=false '
SELECT
  service.description,
  SUM(cost) as total_cost
FROM `project.billing_export.gcp_billing_export_v1_XXXXX`
WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY service.description
ORDER BY total_cost DESC
'
```

### Cost Estimation API

The API returns cost estimates for each request:

```json
{
    "cost_estimate": {
        "speech_to_text": 0.108,
        "situation_classification": 0.002,
        "storage": 0.001,
        "total": 0.111
    }
}
```

## ROI Considerations

### Manual Transcription Comparison

| Method | Cost per Hour | Turnaround |
|--------|---------------|------------|
| Professional transcriptionist | $60-120 | 24-48 hours |
| Crowdsourced | $30-60 | 12-24 hours |
| Media Intelligence Pipeline | ~$2.20 | < 1 minute |

**Potential savings: 95%+**

### Time Savings

- Automated processing: No manual intervention
- Real-time results: Available in seconds
- Scalability: Handle thousands of files simultaneously
