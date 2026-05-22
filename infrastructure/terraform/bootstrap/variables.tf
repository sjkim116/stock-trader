variable "project_name" {
  description = "Project name used in resource naming"
  type        = string
  default     = "algotrader"
}

variable "aws_region" {
  description = "AWS region to host the state backend"
  type        = string
  default     = "ap-northeast-2"
}

variable "state_bucket_name" {
  description = "S3 bucket name for Terraform state. Empty derives <project_name>-tfstate-<account_id>."
  type        = string
  default     = ""
}

variable "lock_table_name" {
  description = "DynamoDB table name for state locking"
  type        = string
  default     = "algotrader-terraform-locks"
}

variable "noncurrent_version_expiration_days" {
  description = "Days after which noncurrent state versions are expired"
  type        = number
  default     = 90
}

variable "use_kms_encryption" {
  description = "Use a customer-managed KMS key for state encryption (otherwise SSE-S3 / AES256)"
  type        = bool
  default     = false
}

variable "kms_deletion_window_days" {
  description = "Pending window when the KMS key is scheduled for deletion (only if use_kms_encryption=true)"
  type        = number
  default     = 30
}
