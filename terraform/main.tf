terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "speech.googleapis.com",
    "storage.googleapis.com",
    "run.googleapis.com",
    "cloudfunctions.googleapis.com",
    "aiplatform.googleapis.com",
    "cloudbuild.googleapis.com",
    "pubsub.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "firestore.googleapis.com",
    "bigquery.googleapis.com",
    "artifactregistry.googleapis.com",
  ])

  service            = each.value
  disable_on_destroy = false
}

# Cloud Storage bucket for input media files
resource "google_storage_bucket" "input" {
  name          = "${var.project_id}-media-input"
  location      = var.region
  force_destroy = var.force_destroy_buckets

  uniform_bucket_level_access = true

  versioning {
    enabled = false
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = var.input_retention_days
    }
  }

  labels = var.labels

  depends_on = [google_project_service.apis]
}

# Cloud Storage bucket for output results
resource "google_storage_bucket" "output" {
  name          = "${var.project_id}-media-output"
  location      = var.region
  force_destroy = var.force_destroy_buckets

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = var.output_retention_days
    }
  }

  labels = var.labels

  depends_on = [google_project_service.apis]
}

# Pub/Sub topic for processing queue
resource "google_pubsub_topic" "media_upload" {
  name = "media-upload"

  message_retention_duration = "86400s" # 24 hours

  labels = var.labels

  depends_on = [google_project_service.apis]
}

# Pub/Sub subscription for Cloud Run
resource "google_pubsub_subscription" "media_upload_push" {
  name  = "media-upload-push"
  topic = google_pubsub_topic.media_upload.id

  ack_deadline_seconds = 600 # 10 minutes for long processing

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.media_processor.uri}/process"

    oidc_token {
      service_account_email = google_service_account.pubsub_invoker.email
    }
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  labels = var.labels

  depends_on = [google_cloud_run_v2_service.media_processor]
}

# IAM: Allow GCS to publish to Pub/Sub
data "google_storage_project_service_account" "gcs_account" {}

resource "google_pubsub_topic_iam_member" "gcs_publisher" {
  topic  = google_pubsub_topic.media_upload.id
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${data.google_storage_project_service_account.gcs_account.email_address}"
}

# Cloud Storage notification to Pub/Sub
resource "google_storage_notification" "upload_notification" {
  bucket         = google_storage_bucket.input.name
  payload_format = "JSON_API_V1"
  topic          = google_pubsub_topic.media_upload.id

  event_types = ["OBJECT_FINALIZE"]

  depends_on = [google_pubsub_topic_iam_member.gcs_publisher]
}

# Artifact Registry for container images
resource "google_artifact_registry_repository" "media_processor" {
  location      = var.region
  repository_id = "media-processor"
  description   = "Docker repository for media processor images"
  format        = "DOCKER"

  labels = var.labels

  depends_on = [google_project_service.apis]
}

# Cloud Run service
resource "google_cloud_run_v2_service" "media_processor" {
  name     = "media-processor"
  location = var.region

  template {
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    timeout = "3600s" # 1 hour timeout for long audio files

    containers {
      image = var.container_image != "" ? var.container_image : "${var.region}-docker.pkg.dev/${var.project_id}/media-processor/media-processor:latest"

      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
        cpu_idle = true
      }

      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "REGION"
        value = var.region
      }

      env {
        name  = "INPUT_BUCKET"
        value = google_storage_bucket.input.name
      }

      env {
        name  = "OUTPUT_BUCKET"
        value = google_storage_bucket.output.name
      }

      env {
        name  = "LOG_LEVEL"
        value = var.log_level
      }

      env {
        name  = "ENABLE_STRUCTURED_LOGGING"
        value = "true"
      }

      # Vertex AI endpoint (if configured)
      dynamic "env" {
        for_each = var.vertex_ai_endpoint_id != "" ? [1] : []
        content {
          name  = "VERTEX_AI_ENDPOINT_ID"
          value = var.vertex_ai_endpoint_id
        }
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 10
        period_seconds        = 10
        timeout_seconds       = 5
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        period_seconds    = 30
        timeout_seconds   = 5
        failure_threshold = 3
      }
    }

    service_account = google_service_account.processor.email
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  labels = var.labels

  depends_on = [
    google_project_service.apis,
    google_artifact_registry_repository.media_processor,
  ]
}

# Allow unauthenticated access (or configure IAM for authenticated access)
resource "google_cloud_run_v2_service_iam_member" "invoker" {
  count    = var.allow_unauthenticated ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.media_processor.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Firestore database (optional)
resource "google_firestore_database" "media_results" {
  count       = var.enable_firestore ? 1 : 0
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.apis]
}

# BigQuery dataset (optional)
resource "google_bigquery_dataset" "media_intelligence" {
  count       = var.enable_bigquery ? 1 : 0
  dataset_id  = "media_intelligence"
  description = "Media Intelligence Pipeline results"
  location    = var.region

  labels = var.labels

  depends_on = [google_project_service.apis]
}

# BigQuery table for transcripts
resource "google_bigquery_table" "transcripts" {
  count               = var.enable_bigquery ? 1 : 0
  dataset_id          = google_bigquery_dataset.media_intelligence[0].dataset_id
  table_id            = "transcripts"
  deletion_protection = false

  schema = jsonencode([
    {
      name = "file_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "gcs_input_uri"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "processed_at"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    },
    {
      name = "duration"
      type = "FLOAT64"
      mode = "NULLABLE"
    },
    {
      name = "speaker_count"
      type = "INT64"
      mode = "NULLABLE"
    },
    {
      name = "overall_situation"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "transcript_text"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "cost_estimate"
      type = "FLOAT64"
      mode = "NULLABLE"
    },
  ])

  labels = var.labels
}

# Vertex AI dataset for situation classification (optional)
resource "google_vertex_ai_dataset" "audio_situations" {
  count              = var.enable_vertex_ai_dataset ? 1 : 0
  display_name       = "audio-situations"
  metadata_schema_uri = "gs://google-cloud-aiplatform/schema/dataset/metadata/audio_1.0.0.yaml"
  region             = var.region

  labels = var.labels

  depends_on = [google_project_service.apis]
}
