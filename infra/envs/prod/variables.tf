# infra/envs/prod/variables.tf

variable "project_id" {
  description = "GCP Project ID para Producción"
  type        = string
  default     = "atlas-datos-estadisticos-prod"
}

variable "db_password" {
  description = "Database password (set via TF_VAR_db_password o Secret Manager)"
  type        = string
  sensitive   = true
}
