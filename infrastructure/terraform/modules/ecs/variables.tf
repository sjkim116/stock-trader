variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "aws_region" {
  description = "AWS region (passed as env var to tasks)"
  type        = string
}

variable "subnet_ids" {
  description = "Private subnet IDs for Fargate tasks"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security groups for ECS tasks"
  type        = list(string)
}

variable "target_group_arn" {
  description = "ALB target group ARN for the user-api service"
  type        = string
}

variable "container_image" {
  description = "Container image (ECR repo URL : tag) for user-api"
  type        = string
}

variable "container_port" {
  description = "Container port the application listens on"
  type        = number
  default     = 8000
}

variable "task_cpu" {
  description = "Fargate task CPU units (256, 512, 1024, ...)"
  type        = number
}

variable "task_memory" {
  description = "Fargate task memory in MB"
  type        = number
}

variable "desired_count" {
  description = "Initial desired task count"
  type        = number
  default     = 1
}

variable "min_capacity" {
  description = "Minimum capacity for autoscaling"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum capacity for autoscaling"
  type        = number
  default     = 4
}

variable "autoscaling_cpu_target" {
  description = "Target average CPU utilization (%) for autoscaling"
  type        = number
  default     = 60
}

variable "capacity_providers" {
  description = "Capacity providers to enable on the cluster"
  type        = list(string)
  default     = ["FARGATE", "FARGATE_SPOT"]
}

variable "default_capacity_provider_strategy" {
  description = "Default capacity provider strategy (list of {capacity_provider, weight, base})"
  type = list(object({
    capacity_provider = string
    weight            = number
    base              = optional(number, 0)
  }))
  default = [
    { capacity_provider = "FARGATE", weight = 1, base = 1 }
  ]
}

variable "enable_container_insights" {
  description = "Enable CloudWatch Container Insights on the cluster"
  type        = bool
  default     = true
}

variable "database_endpoint" {
  description = "RDS endpoint (host name only, no port)"
  type        = string
}

variable "database_port" {
  description = "RDS port"
  type        = number
  default     = 5432
}

variable "database_name" {
  description = "Database name"
  type        = string
}

variable "database_username" {
  description = "Database master username (read from secret in app or passed in)"
  type        = string
}

variable "database_secret_arn" {
  description = "Secrets Manager ARN containing database credentials JSON (must include 'password' key)"
  type        = string
}

variable "redis_host" {
  description = "Redis primary endpoint host"
  type        = string
}

variable "redis_port" {
  description = "Redis port"
  type        = number
  default     = 6379
}

variable "redis_tls_enabled" {
  description = "Whether the Redis endpoint requires TLS"
  type        = bool
  default     = true
}

variable "redis_auth_secret_arn" {
  description = "Secrets Manager ARN containing Redis AUTH token (must include 'auth_token' key). Empty disables Redis AUTH."
  type        = string
  default     = ""
}

variable "additional_environment_variables" {
  description = "Extra environment variables for the container (map of name → value)"
  type        = map(string)
  default     = {}
}

variable "additional_secret_environment_variables" {
  description = "Extra secret env vars (map of env var name → Secrets Manager value_from string, e.g. arn:...:JSON_KEY::)"
  type        = map(string)
  default     = {}
}

variable "additional_secret_arns" {
  description = "Extra Secrets Manager ARNs the task execution role can GetSecretValue on. Required when additional_secret_environment_variables references secrets outside the base RDS/Redis ones."
  type        = list(string)
  default     = []
}

variable "log_retention_days" {
  description = "Retention in days for the task log group"
  type        = number
  default     = 30
}

variable "deployment_minimum_healthy_percent" {
  description = "Deployment minimum healthy percent"
  type        = number
  default     = 100
}

variable "deployment_maximum_percent" {
  description = "Deployment maximum percent"
  type        = number
  default     = 200
}

variable "enable_deployment_circuit_breaker" {
  description = "Enable deployment circuit breaker with auto rollback"
  type        = bool
  default     = true
}

variable "service_name" {
  description = "ECS service short name"
  type        = string
  default     = "user-api"
}
