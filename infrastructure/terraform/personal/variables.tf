variable "project_name" {
  description = "Project name (tag prefix + Secrets Manager namespace)"
  type        = string
  default     = "algotrader"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-2"
}

variable "vpc_cidr" {
  description = "CIDR block for the (small, single-AZ) VPC"
  type        = string
  default     = "10.10.0.0/24"
}

variable "instance_type" {
  description = "EC2 instance type for the personal host. t4g.small for the default 1-user workload; bump to t4g.medium if RAM gets tight."
  type        = string
  default     = "t4g.small"
}

variable "data_volume_size_gb" {
  description = "Initial EBS data volume size. Grow online via aws_ebs_volume modify."
  type        = number
  default     = 50
}

variable "allowed_ssh_cidrs" {
  description = "CIDR blocks allowed to SSH on 22. Empty list disables SSH ingress (use SSM Session Manager instead)."
  type        = list(string)
  default     = []
}

variable "github_repo_url" {
  description = "HTTPS git clone URL the host pulls on every restart. Empty skips auto-clone."
  type        = string
  default     = ""
}

variable "github_repo_branch" {
  description = "Branch the host checks out"
  type        = string
  default     = "main"
}

variable "snapshot_retention_count" {
  description = "Number of daily DLM snapshots to retain for the data volume"
  type        = number
  default     = 14
}

variable "kis_app_secret_arn" {
  description = "Optional pre-existing Secrets Manager ARN holding KIS app key/secret JSON. Granted to the instance role so the app can read it at runtime."
  type        = string
  default     = ""
}
