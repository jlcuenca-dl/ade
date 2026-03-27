# infra/modules/cloudrun/variables.tf

variable "project_id" { type = string }
variable "region"     { type = string; default = "us-central1" }
variable "service_name" { type = string }
variable "image_uri"    { type = string }
variable "cpu_limit"    { type = string; default = "1" }
variable "memory_limit" { type = string; default = "512Mi" }

variable "env_vars" {
  type    = map(string)
  default = {}
}

variable "allow_unauthenticated" {
  type    = bool
  default = false
}
