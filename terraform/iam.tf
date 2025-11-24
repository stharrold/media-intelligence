# Service account for Cloud Run media processor
resource "google_service_account" "processor" {
  account_id   = "media-processor"
  display_name = "Media Processor Service Account"
  description  = "Service account for the Media Intelligence Pipeline"
}

# Service account for Pub/Sub to invoke Cloud Run
resource "google_service_account" "pubsub_invoker" {
  account_id   = "pubsub-invoker"
  display_name = "Pub/Sub Invoker Service Account"
  description  = "Service account for Pub/Sub to invoke Cloud Run"
}

# IAM: Processor can use Speech-to-Text
resource "google_project_iam_member" "speech_user" {
  project = var.project_id
  role    = "roles/speech.client"
  member  = "serviceAccount:${google_service_account.processor.email}"
}

# IAM: Processor can access Cloud Storage
resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.processor.email}"
}

# IAM: Processor can use Vertex AI
resource "google_project_iam_member" "aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.processor.email}"
}

# IAM: Processor can write logs
resource "google_project_iam_member" "logging_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.processor.email}"
}

# IAM: Processor can report errors
resource "google_project_iam_member" "error_reporting" {
  project = var.project_id
  role    = "roles/errorreporting.writer"
  member  = "serviceAccount:${google_service_account.processor.email}"
}

# IAM: Processor can write metrics
resource "google_project_iam_member" "monitoring_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.processor.email}"
}

# IAM: Processor can access Firestore (if enabled)
resource "google_project_iam_member" "firestore_user" {
  count   = var.enable_firestore ? 1 : 0
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.processor.email}"
}

# IAM: Processor can access BigQuery (if enabled)
resource "google_project_iam_member" "bigquery_user" {
  count   = var.enable_bigquery ? 1 : 0
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.processor.email}"
}

# IAM: Pub/Sub invoker can invoke Cloud Run
resource "google_cloud_run_v2_service_iam_member" "pubsub_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.media_processor.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pubsub_invoker.email}"
}

# IAM: Pub/Sub service can use the invoker service account
resource "google_service_account_iam_member" "pubsub_token_creator" {
  service_account_id = google_service_account.pubsub_invoker.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# Get project information
data "google_project" "project" {
  project_id = var.project_id
}

# Optional: Workload Identity for GKE (if needed)
resource "google_service_account_iam_member" "workload_identity" {
  count              = var.enable_workload_identity ? 1 : 0
  service_account_id = google_service_account.processor.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[${var.workload_identity_namespace}/media-processor]"
}

variable "enable_workload_identity" {
  description = "Enable Workload Identity for GKE"
  type        = bool
  default     = false
}

variable "workload_identity_namespace" {
  description = "Kubernetes namespace for Workload Identity"
  type        = string
  default     = "default"
}
