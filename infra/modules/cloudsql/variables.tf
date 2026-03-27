# infra/modules/cloudsql/variables.tf

variable "project_id"    { type = string }
variable "region"        { type = string; default = "us-central1" }
variable "instance_name" { type = string }
variable "database_version" { type = string; default = "POSTGRES_15" }
variable "tier"          { type = string; default = "db-f1-micro" }
variable "db_name"       { type = string }
variable "db_user"       { type = string }
variable "db_password"   { type = string; sensitive = true }
variable "deletion_protection" { type = bool; default = true }
