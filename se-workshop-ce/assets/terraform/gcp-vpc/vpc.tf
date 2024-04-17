// Define the resources to create
// Provisions the following into a GCP Project: 
//    VPC

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
