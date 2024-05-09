// Define the resources to create
// Provisions the following into a GCP Project: 
//    GKE Cluster

// Generate Random ID for GKE Cluster
resource "random_string" "env" {
  length  = 4
  special = false
  upper   = false
  numeric = false
}

// Create GKE Cluster
resource "google_container_cluster" "boutique" {
  project            = var.gcp_project_id
  name               = "boutique-cluster-${random_string.env.result}"
  location           = "us-central1-a"
  initial_node_count = 1

  networking_mode = "VPC_NATIVE"
  ip_allocation_policy {}

  network    = "vpc-boutique" //vpc.output.network_name
  subnetwork = "app"

  master_auth {
    client_certificate_config {
      issue_client_certificate = false
    }
  }

  min_master_version = data.google_container_engine_versions.central1a.latest_master_version
  node_version       = data.google_container_engine_versions.central1a.latest_master_version

  maintenance_policy {
    recurring_window {
      start_time = "2022-12-11T13:00:00Z"
      end_time   = "2022-12-11T19:00:00Z"
      recurrence = "FREQ=WEEKLY;WKST=SU;BYDAY=SA,SU"
    }
  }

  node_config {
    service_account = var.gke_cluster_user
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
    ]
    machine_type = "n1-standard-2"
    metadata = {
      disable-legacy-endpoints = "true"
    }
    tags = ["boutique-cluster"]
  }

  enable_legacy_abac = true

  timeouts {
    create = "30m"
    update = "40m"
  }
}
