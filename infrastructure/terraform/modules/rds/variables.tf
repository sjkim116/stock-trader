variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "subnet_ids" {
  description = "List of database subnet IDs (private, isolated)"
  type        = list(string)
}

variable "security_group_ids" {
  description = "List of security group IDs to attach to the RDS instance"
  type        = list(string)
}

variable "engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15.7"
}

variable "family" {
  description = "DB parameter group family"
  type        = string
  default     = "postgres15"
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
}

variable "allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
}

variable "max_allocated_storage" {
  description = "Upper bound for storage autoscaling in GB. 0 disables autoscaling."
  type        = number
  default     = 0
}

variable "storage_type" {
  description = "Storage type (gp3 recommended)"
  type        = string
  default     = "gp3"
}

variable "db_name" {
  description = "Initial database name"
  type        = string
  default     = "algotrader"
}

variable "username" {
  description = "Master username"
  type        = string
  default     = "algotrader"
}

variable "port" {
  description = "Database port"
  type        = number
  default     = 5432
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment"
  type        = bool
  default     = false
}

variable "backup_retention_period" {
  description = "Number of days to retain automated backups"
  type        = number
  default     = 7
}

variable "backup_window" {
  description = "Daily backup window (UTC). Korean market is closed during this window."
  type        = string
  default     = "17:00-18:00"
}

variable "maintenance_window" {
  description = "Weekly maintenance window (UTC)"
  type        = string
  default     = "sun:18:00-sun:19:00"
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot on destroy (DO NOT enable in production)"
  type        = bool
  default     = false
}

variable "performance_insights_enabled" {
  description = "Enable RDS Performance Insights"
  type        = bool
  default     = true
}

variable "performance_insights_retention_period" {
  description = "Performance Insights retention in days (7 or 731)"
  type        = number
  default     = 7
}

variable "monitoring_interval" {
  description = "Enhanced monitoring interval in seconds (0 to disable; 1, 5, 10, 15, 30, 60)"
  type        = number
  default     = 60
}

variable "log_retention_days" {
  description = "CloudWatch log group retention in days for exported PostgreSQL logs"
  type        = number
  default     = 30
}

variable "enabled_cloudwatch_logs_exports" {
  description = "Log types to export to CloudWatch"
  type        = list(string)
  default     = ["postgresql", "upgrade"]
}

variable "parameter_overrides" {
  description = "Additional DB parameter group settings (name → value)"
  type        = map(string)
  default     = {}
}

variable "apply_immediately" {
  description = "Apply parameter changes immediately rather than during the next maintenance window"
  type        = bool
  default     = false
}
