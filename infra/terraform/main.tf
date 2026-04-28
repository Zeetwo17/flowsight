# Terraform — provisions all GCP resources FlowSight needs.
#   - Artifact Registry (Docker images)
#   - Cloud Run (FastAPI backend)
#   - Pub/Sub (event ingestion topic + subscription)
#   - Firestore (live state)
#   - BigQuery (analytics)
#   - Secret Manager (Gemini API key)
#   - Firebase Hosting site (PWA frontend) — declared but not site-built here
#
# Usage:
#   terraform init
#   terraform apply -var="project_id=YOUR_PROJECT" -var="region=asia-south1"

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

variable "project_id" { type = string }
variable "region"     { type = string  default = "asia-south1" }
variable "image_tag"  { type = string  default = "latest" }
variable "gemini_api_key" {
  type      = string
  default   = ""
  sensitive = true
  description = "Gemini API key. Leave empty to skip secret creation."
}

# ----- APIs -----
resource "google_project_service" "services" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "pubsub.googleapis.com",
    "firestore.googleapis.com",
    "bigquery.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "firebase.googleapis.com",
    "firebasehosting.googleapis.com",
  ])
  service = each.key
  disable_on_destroy = false
}

# ----- Artifact Registry -----
resource "google_artifact_registry_repository" "flowsight" {
  location      = var.region
  repository_id = "flowsight"
  format        = "DOCKER"
  depends_on    = [google_project_service.services]
}

# ----- Pub/Sub: event ingestion -----
resource "google_pubsub_topic" "events" {
  name = "flowsight-events"
  depends_on = [google_project_service.services]
}

resource "google_pubsub_subscription" "events_sub" {
  name  = "flowsight-events-sub"
  topic = google_pubsub_topic.events.name
  ack_deadline_seconds = 30
  message_retention_duration = "604800s"  # 7 days
}

# ----- Firestore (Native mode) -----
resource "google_firestore_database" "live_state" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
  depends_on  = [google_project_service.services]
}

# ----- BigQuery: analytics -----
resource "google_bigquery_dataset" "analytics" {
  dataset_id  = "flowsight"
  location    = var.region
  description = "FlowSight cascade events, decisions, KPIs"
  depends_on  = [google_project_service.services]
}

resource "google_bigquery_table" "events" {
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  table_id   = "events"
  time_partitioning { type = "DAY" field = "timestamp" }
  schema = jsonencode([
    { name = "timestamp", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "node_id",   type = "INTEGER",   mode = "NULLABLE" },
    { name = "edge_u",    type = "INTEGER",   mode = "NULLABLE" },
    { name = "edge_v",    type = "INTEGER",   mode = "NULLABLE" },
    { name = "kind",      type = "STRING",    mode = "REQUIRED" },
    { name = "severity",  type = "FLOAT",     mode = "REQUIRED" },
    { name = "source",    type = "STRING",    mode = "REQUIRED" },
    { name = "metadata",  type = "JSON",      mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "decisions" {
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  table_id   = "decisions"
  time_partitioning { type = "DAY" field = "timestamp" }
  schema = jsonencode([
    { name = "timestamp",     type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "shipment_id",   type = "STRING",    mode = "REQUIRED" },
    { name = "naive_path",    type = "STRING",    mode = "REPEATED" },
    { name = "chosen_path",   type = "STRING",    mode = "REPEATED" },
    { name = "time_saved",    type = "FLOAT",     mode = "NULLABLE" },
    { name = "risk_avoided",  type = "FLOAT",     mode = "NULLABLE" },
    { name = "co2_saved",     type = "FLOAT",     mode = "NULLABLE" },
    { name = "explanation",   type = "STRING",    mode = "NULLABLE" },
  ])
}

# ----- Secret Manager: Gemini key -----
resource "google_secret_manager_secret" "gemini" {
  count     = var.gemini_api_key == "" ? 0 : 1
  secret_id = "gemini-api-key"
  replication { auto {} }
  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret_version" "gemini" {
  count       = var.gemini_api_key == "" ? 0 : 1
  secret      = google_secret_manager_secret.gemini[0].id
  secret_data = var.gemini_api_key
}

# ----- Cloud Run: backend -----
resource "google_cloud_run_v2_service" "backend" {
  name     = "flowsight-api"
  location = var.region
  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/flowsight/flowsight-api:${var.image_tag}"
      resources {
        limits = { cpu = "1", memory = "1Gi" }
      }
      ports { container_port = 8080 }
      dynamic "env" {
        for_each = var.gemini_api_key == "" ? [] : [1]
        content {
          name = "GEMINI_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.gemini[0].secret_id
              version = "latest"
            }
          }
        }
      }
    }
    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
  }
  depends_on = [google_artifact_registry_repository.flowsight]
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.backend.name
  location = google_cloud_run_v2_service.backend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ----- Firebase Hosting site (frontend PWA) -----
resource "google_firebase_hosting_site" "frontend" {
  provider = google-beta
  project  = var.project_id
  site_id  = "${var.project_id}-flowsight"
  depends_on = [google_project_service.services]
}

# ----- Outputs -----
output "backend_url" {
  value = google_cloud_run_v2_service.backend.uri
}
output "events_topic" {
  value = google_pubsub_topic.events.id
}
output "bigquery_dataset" {
  value = google_bigquery_dataset.analytics.id
}
output "frontend_site_id" {
  value = google_firebase_hosting_site.frontend.site_id
}
