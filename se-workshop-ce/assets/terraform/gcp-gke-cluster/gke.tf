// Define the resources to create
// Provisions Azure Resource Group along with: 
//    VPC, Service Account, IAM Member, GKE Cluster

// Create VPC
module "vpc" {
  source       = "terraform-google-modules/network/google"
  version      = "~> 9.0"
  project_id   = var.gcp_project_id
  network_name = "vpc-boutique"
  subnets = [
    {
      subnet_name           = "app"
      subnet_ip             = "10.1.0.0/24"
      subnet_region         = "us-central1"
      subnet_private_access = "false"
      subnet_flow_logs      = "true"
    },
  ]
}

// Generate Random ID for GKE Cluster
resource "random_string" "env" {
  length  = 4
  special = false
  upper   = false
  number  = false
}

// Create Service Account
resource "google_service_account" "harness" {
  account_id   = "harness-${random_string.env}"
  display_name = "harness"
}

// Configure IAM Member
resource "google_project_iam_member" "harness" {
  project = var.gcp_project_id
  role    = "roles/viewer"
  member  = "serviceAccount:${google_service_account.harness.email}"
}

// Create GKE Cluster
resource "google_container_cluster" "boutique" {
  project            = var.gcp_project_id
  name               = "boutique-cluster-${random_string.env}"
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
    service_account = google_service_account.harness.email
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
