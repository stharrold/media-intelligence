variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default = {
    app         = "media-intelligence"
    environment = "production"
    managed_by  = "terraform"
  }
}

# Storage configuration
variable "force_destroy_buckets" {
  description = "Allow deletion of non-empty buckets"
  type        = bool
  default     = false
}

variable "input_retention_days" {
  description = "Number of days to retain input files"
  type        = number
  default     = 30
}

variable "output_retention_days" {
  description = "Number of days to retain output files"
  type        = number
  default     = 90
}

# Cloud Run configuration
variable "container_image" {
  description = "Container image for Cloud Run (leave empty to use default)"
  type        = string
  default     = ""
}

variable "min_instances" {
  description = "Minimum number of Cloud Run instances"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 10
}

variable "cpu_limit" {
  description = "CPU limit per instance"
  type        = string
  default     = "2"
}

variable "memory_limit" {
  description = "Memory limit per instance"
  type        = string
  default     = "4Gi"
}

variable "log_level" {
  description = "Logging level"
  type        = string
  default     = "INFO"
}

variable "allow_unauthenticated" {
  description = "Allow unauthenticated access to Cloud Run"
  type        = bool
  default     = false
}

# Vertex AI configuration
variable "vertex_ai_endpoint_id" {
  description = "Vertex AI endpoint ID for situation classification"
  type        = string
  default     = ""
}

variable "enable_vertex_ai_dataset" {
  description = "Create Vertex AI dataset for training"
  type        = bool
  default     = false
}

# Optional services
variable "enable_firestore" {
  description = "Enable Firestore for metadata storage"
  type        = bool
  default     = false
}

variable "enable_bigquery" {
  description = "Enable BigQuery for analytics"
  type        = bool
  default     = false
}
