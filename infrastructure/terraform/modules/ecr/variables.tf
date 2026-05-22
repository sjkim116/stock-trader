variable "project_name" {
  description = "Project name used to prefix repository names"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "repositories" {
  description = "List of ECR repository short names (will be prefixed with project_name)"
  type        = list(string)
}

variable "image_tag_mutability" {
  description = "ECR image tag mutability (MUTABLE or IMMUTABLE)"
  type        = string
  default     = "IMMUTABLE"

  validation {
    condition     = contains(["MUTABLE", "IMMUTABLE"], var.image_tag_mutability)
    error_message = "image_tag_mutability must be MUTABLE or IMMUTABLE."
  }
}

variable "scan_on_push" {
  description = "Enable image scanning on push"
  type        = bool
  default     = true
}

variable "encryption_type" {
  description = "Encryption type (AES256 or KMS)"
  type        = string
  default     = "AES256"

  validation {
    condition     = contains(["AES256", "KMS"], var.encryption_type)
    error_message = "encryption_type must be AES256 or KMS."
  }
}

variable "kms_key_arn" {
  description = "KMS key ARN when encryption_type is KMS. Empty to use AWS-managed key."
  type        = string
  default     = ""
}

variable "untagged_image_expiry_days" {
  description = "Days after which untagged images are expired"
  type        = number
  default     = 14
}

variable "max_tagged_image_count" {
  description = "Maximum number of tagged images to retain per repository"
  type        = number
  default     = 30
}

variable "force_delete" {
  description = "Allow deleting repository even when it contains images (use with care)"
  type        = bool
  default     = false
}
