//Define the provider and any data sources
provider "google" {
  region  = "us-central1"
  project = var.gcp_project_id
}

// Get Supported K8s Versions
data "google_container_engine_versions" "central1a" {
  project        = var.gcp_project_id
  location       = "us-central1-a"
  version_prefix = "1.23.17-gke."
}
