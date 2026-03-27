# infra/envs/qa/variables.tf

variable "project_id" {
  description = "GCP Project ID para QA"
  type        = string
  default     = "atlas-datos-estadisticos-qa"
}

variable "db_password" {
  description = "Database password (set via TF_VAR_db_password o Secret Manager)"
  type        = string
  sensitive   = true
}
