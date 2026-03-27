# infra/envs/qa/main.tf — Ambiente de Pruebas (QA)

terraform {
  backend "gcs" {
    bucket = "ade-terraform-state"
    prefix = "envs/qa"
  }
}

provider "google" {
  project = var.project_id
  region  = "us-central1"
}

module "database" {
  source        = "../../modules/cloudsql"
  project_id    = var.project_id
  instance_name = "ade-db-qa"
  db_name       = "ade"
  db_user       = "ade_user"
  db_password   = var.db_password
  tier          = "db-g1-small"  # Más capacidad que DESA para pruebas realistas
  deletion_protection = true
}

module "backend" {
  source       = "../../modules/cloudrun"
  project_id   = var.project_id
  service_name = "ade-backend-qa"
  image_uri    = "us-central1-docker.pkg.dev/${var.project_id}/ade-repo/ade-backend:qa"
  cpu_limit    = "1"
  memory_limit = "1024Mi"

  env_vars = {
    ENV          = "qa"
    DATABASE_URL = "postgresql://ade_user:${var.db_password}@/ade?host=/cloudsql/${var.project_id}:us-central1:ade-db-qa"
  }

  allow_unauthenticated = true
}
