# infra/envs/desa/main.tf

provider "google" {
  project = var.project_id
  region  = "us-central1"
}

module "database" {
  source        = "../../modules/cloudsql"
  project_id    = var.project_id
  instance_name = "ade-db-desa"
  db_name       = "ade"
  db_user       = "ade_user"
  db_password   = var.db_password
  tier          = "db-f1-micro"
  deletion_protection = false # No protection for development env
}

module "backend" {
  source       = "../../modules/cloudrun"
  project_id   = var.project_id
  service_name = "ade-backend-desa"
  image_uri    = "gcr.io/${var.project_id}/ade-backend:latest"
  
  env_vars = {
    ENV          = "desa"
    DATABASE_URL = "postgresql://ade_user:${var.db_password}@/ade?host=/cloudsql/${var.project_id}:us-central1:ade-db-desa"
  }

  allow_unauthenticated = true
}
