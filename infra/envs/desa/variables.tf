# infra/envs/desa/variables.tf

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "atlas-datos-estadisticos-desa"
}

variable "db_password" {
  description = "Database password (set via TF_VAR_db_password)"
  type        = string
  sensitive   = true
}
