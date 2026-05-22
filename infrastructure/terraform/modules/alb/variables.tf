variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID hosting the ALB and target group"
  type        = string
}

variable "subnet_ids" {
  description = "Public subnet IDs for the ALB"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security groups to attach to the ALB"
  type        = list(string)
}

variable "internal" {
  description = "Whether the ALB is internal-only"
  type        = bool
  default     = false
}

variable "idle_timeout" {
  description = "Connection idle timeout in seconds"
  type        = number
  default     = 60
}

variable "deletion_protection" {
  description = "Enable deletion protection on the ALB"
  type        = bool
  default     = true
}

variable "target_port" {
  description = "Target port the backend listens on (ECS task port)"
  type        = number
  default     = 8000
}

variable "target_protocol" {
  description = "Target protocol (HTTP or HTTPS)"
  type        = string
  default     = "HTTP"
}

variable "health_check_path" {
  description = "Health check path on the targets"
  type        = string
  default     = "/health"
}

variable "health_check_healthy_threshold" {
  description = "Consecutive successes before a target is healthy"
  type        = number
  default     = 2
}

variable "health_check_unhealthy_threshold" {
  description = "Consecutive failures before a target is unhealthy"
  type        = number
  default     = 3
}

variable "health_check_interval" {
  description = "Health check interval in seconds"
  type        = number
  default     = 30
}

variable "health_check_timeout" {
  description = "Health check timeout in seconds"
  type        = number
  default     = 5
}

variable "deregistration_delay" {
  description = "Time (seconds) to wait before deregistering a target"
  type        = number
  default     = 30
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS listener. Empty disables HTTPS (HTTP-only)."
  type        = string
  default     = ""
}

variable "ssl_policy" {
  description = "SSL policy for the HTTPS listener"
  type        = string
  default     = "ELBSecurityPolicy-TLS13-1-2-2021-06"
}

variable "access_logs_bucket" {
  description = "S3 bucket name for ALB access logs (empty disables access logs)"
  type        = string
  default     = ""
}

variable "access_logs_prefix" {
  description = "Prefix within the access logs bucket"
  type        = string
  default     = "alb"
}
