variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "subnet_ids" {
  description = "Private subnet IDs for the cache subnet group"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security group IDs to attach to the replication group"
  type        = list(string)
}

variable "engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.0"
}

variable "parameter_group_family" {
  description = "Parameter group family"
  type        = string
  default     = "redis7"
}

variable "node_type" {
  description = "Cache node type"
  type        = string
}

variable "num_cache_clusters" {
  description = "Number of cache clusters (nodes) in the replication group. 1 for dev, >=2 for HA."
  type        = number
  default     = 1
}

variable "port" {
  description = "Redis port"
  type        = number
  default     = 6379
}

variable "snapshot_retention_limit" {
  description = "Days to retain automatic snapshots (0 disables)"
  type        = number
  default     = 5
}

variable "snapshot_window" {
  description = "Daily snapshot window (UTC)"
  type        = string
  default     = "17:30-18:30"
}

variable "maintenance_window" {
  description = "Weekly maintenance window"
  type        = string
  default     = "sun:19:00-sun:20:00"
}

variable "at_rest_encryption_enabled" {
  description = "Enable encryption at rest"
  type        = bool
  default     = true
}

variable "transit_encryption_enabled" {
  description = "Enable TLS for client connections"
  type        = bool
  default     = true
}

variable "auth_token_enabled" {
  description = "Enable Redis AUTH (requires transit_encryption_enabled)"
  type        = bool
  default     = true
}

variable "parameter_overrides" {
  description = "Additional Redis parameter group settings"
  type        = map(string)
  default     = {}
}

variable "apply_immediately" {
  description = "Apply changes immediately"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "Retention in days for slow-log CloudWatch log group"
  type        = number
  default     = 30
}
