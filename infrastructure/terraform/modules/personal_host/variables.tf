variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the instance lives"
  type        = string
}

variable "subnet_id" {
  description = "Public subnet ID — the instance gets an EIP and is reached over the open internet (Caddy handles HTTPS)."
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type. t4g.small is enough for a 1-user docker-compose stack (2 vCPU / 2 GB RAM)."
  type        = string
  default     = "t4g.small"
}

variable "data_volume_size_gb" {
  description = "Initial size of the EBS gp3 data volume (mounted at /data on the host)."
  type        = number
  default     = 50
}

variable "kms_key_id" {
  description = "KMS key ID for EBS + Secrets Manager. Empty uses the AWS-managed default."
  type        = string
  default     = ""
}

variable "allowed_ssh_cidrs" {
  description = "CIDR blocks allowed to SSH on port 22. Empty list disables SSH ingress (use SSM Session Manager instead)."
  type        = list(string)
  default     = []
}

variable "github_repo_url" {
  description = "git clone URL the cloud-init script pulls the stack from. Empty skips the auto-clone step (user installs the stack manually)."
  type        = string
  default     = ""
}

variable "github_repo_branch" {
  description = "Branch the cloud-init script checks out from github_repo_url."
  type        = string
  default     = "main"
}

variable "snapshot_retention_count" {
  description = "Number of daily EBS snapshots to retain via Data Lifecycle Manager."
  type        = number
  default     = 14
}

variable "snapshot_schedule_cron" {
  description = "DLM cron expression. Default 03:00 KST = 18:00 UTC (after KR market close)."
  type        = string
  default     = "cron(0 18 * * ? *)"
}

variable "log_retention_days" {
  description = "CloudWatch log group retention in days for forwarded application/system logs."
  type        = number
  default     = 30
}

variable "secrets_to_grant_read" {
  description = "Additional Secrets Manager ARNs the instance role can read (e.g. KIS app keys). The instance's own credential secret is always readable."
  type        = list(string)
  default     = []
}
