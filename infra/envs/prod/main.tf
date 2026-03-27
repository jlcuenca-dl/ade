# infra/envs/prod/main.tf — Ambiente de Producción (PROD)

terraform {
  backend "gcs" {
    bucket = "ade-terraform-state"
    prefix = "envs/prod"
  }
}

provider "google" {
  project = var.project_id
  region  = "us-central1"
}

module "database" {
  source        = "../../modules/cloudsql"
  project_id    = var.project_id
  instance_name = "ade-db-prod"
  db_name       = "ade"
  db_user       = "ade_user"
  db_password   = var.db_password
  tier              = "db-custom-2-3840"  # 2 vCPU, 3.75 GB RAM
  deletion_protection = true              # Protección activa en PROD
}

module "backend" {
  source       = "../../modules/cloudrun"
  project_id   = var.project_id
  service_name = "ade-backend-prod"
  image_uri    = "us-central1-docker.pkg.dev/${var.project_id}/ade-repo/ade-backend:prod"
  cpu_limit    = "2"
  memory_limit = "2048Mi"

  env_vars = {
    ENV          = "prod"
    DATABASE_URL = "postgresql://ade_user:${var.db_password}@/ade?host=/cloudsql/${var.project_id}:us-central1:ade-db-prod"
  }

  allow_unauthenticated = true
}
