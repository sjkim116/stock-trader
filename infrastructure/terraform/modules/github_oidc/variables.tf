variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name (or 'shared' if the role is account-wide)"
  type        = string
  default     = "shared"
}

variable "github_repository" {
  description = "GitHub repository in the form OWNER/REPO (e.g. acme/stock-trader)"
  type        = string

  validation {
    condition     = can(regex("^[^/]+/[^/]+$", var.github_repository))
    error_message = "github_repository must be of the form OWNER/REPO."
  }
}

variable "allowed_refs" {
  description = "Git refs the role is allowed to be assumed from (e.g. refs/heads/main, refs/tags/v*)"
  type        = list(string)
  default     = ["refs/heads/main"]
}

variable "create_oidc_provider" {
  description = "Create the GitHub OIDC provider in this account. Set false if one already exists (an account can only have one)."
  type        = bool
  default     = true
}

variable "existing_oidc_provider_arn" {
  description = "ARN of an already-existing GitHub OIDC provider in the account (used when create_oidc_provider = false)"
  type        = string
  default     = ""
}

variable "ecr_repository_arns" {
  description = "ECR repository ARNs the role may push to. Pass [] for no ECR access."
  type        = list(string)
  default     = []
}

variable "role_name" {
  description = "IAM role name. Empty derives from project_name + environment."
  type        = string
  default     = ""
}

variable "oidc_thumbprints" {
  description = "GitHub OIDC root CA thumbprints (AWS validates against these). Default is GitHub's well-known thumbprint."
  type        = list(string)
  default     = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}
