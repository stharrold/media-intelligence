output "cloud_run_url" {
  description = "URL of the Cloud Run service"
  value       = google_cloud_run_v2_service.media_processor.uri
}

output "input_bucket" {
  description = "Name of the input storage bucket"
  value       = google_storage_bucket.input.name
}

output "input_bucket_url" {
  description = "URL of the input storage bucket"
  value       = google_storage_bucket.input.url
}

output "output_bucket" {
  description = "Name of the output storage bucket"
  value       = google_storage_bucket.output.name
}

output "output_bucket_url" {
  description = "URL of the output storage bucket"
  value       = google_storage_bucket.output.url
}

output "pubsub_topic" {
  description = "Name of the Pub/Sub topic"
  value       = google_pubsub_topic.media_upload.name
}

output "service_account_email" {
  description = "Email of the processor service account"
  value       = google_service_account.processor.email
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.media_processor.repository_id}"
}

output "bigquery_dataset" {
  description = "BigQuery dataset ID"
  value       = var.enable_bigquery ? google_bigquery_dataset.media_intelligence[0].dataset_id : null
}

output "firestore_database" {
  description = "Firestore database name"
  value       = var.enable_firestore ? google_firestore_database.media_results[0].name : null
}

output "vertex_ai_dataset" {
  description = "Vertex AI dataset name"
  value       = var.enable_vertex_ai_dataset ? google_vertex_ai_dataset.audio_situations[0].name : null
}

# Useful commands
output "upload_command" {
  description = "Command to upload a file for processing"
  value       = "gsutil cp <local_file> gs://${google_storage_bucket.input.name}/"
}

output "process_command" {
  description = "Command to manually trigger processing"
  value       = "curl -X POST ${google_cloud_run_v2_service.media_processor.uri}/process -H 'Content-Type: application/json' -d '{\"gcs_uri\": \"gs://${google_storage_bucket.input.name}/<filename>\"}'"
}

output "build_and_deploy_command" {
  description = "Command to build and deploy the container"
  value       = "gcloud builds submit --tag ${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.media_processor.repository_id}/media-processor:latest && gcloud run deploy media-processor --image ${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.media_processor.repository_id}/media-processor:latest --region ${var.region}"
}
