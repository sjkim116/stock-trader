variable "project_name" {
  description = "Project name"
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
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["ap-northeast-2a", "ap-northeast-2b"]
}

# RDS Variables
variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "rds_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 100
}

variable "rds_multi_az" {
  description = "Enable Multi-AZ for RDS"
  type        = bool
  default     = false
}

# Redis Variables
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_cache_clusters" {
  description = "Number of cache clusters"
  type        = number
  default     = 1
}

# ECS Variables
variable "ecs_task_cpu" {
  description = "ECS task CPU units"
  type        = number
  default     = 512
}

variable "ecs_task_memory" {
  description = "ECS task memory in MB"
  type        = number
  default     = 1024
}

variable "user_api_desired_count" {
  description = "Desired count for User API service"
  type        = number
  default     = 1
}

# Domain Variables
variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "algotrader.local"
}

variable "certificate_arn" {
  description = "ARN of ACM certificate for HTTPS"
  type        = string
  default     = ""
}

# Alert Variables
variable "alert_email" {
  description = "Email address for alerts"
  type        = string
  default     = "alerts@algotrader.dev"
}

# ECR Variables
variable "ecr_repositories" {
  description = "ECR repository short names (will be prefixed with project_name)"
  type        = list(string)
  default     = ["user-api", "market-data-collector"]
}

variable "container_image_tag" {
  description = "Image tag deployed to ECS (typically a git SHA in CI, 'latest' for bootstrap)"
  type        = string
  default     = "latest"
}

# RDS additional variables
variable "rds_engine_version" {
  description = "PostgreSQL engine version for RDS"
  type        = string
  default     = "15.7"
}

variable "rds_max_allocated_storage" {
  description = "RDS storage autoscaling upper bound in GB (0 = disabled)"
  type        = number
  default     = 0
}

# Production hardening toggles (override in tfvars for prod)
variable "rds_deletion_protection" {
  description = "Enable RDS deletion protection"
  type        = bool
  default     = false
}

variable "rds_skip_final_snapshot" {
  description = "Skip final RDS snapshot on destroy"
  type        = bool
  default     = true
}

variable "alb_deletion_protection" {
  description = "Enable ALB deletion protection"
  type        = bool
  default     = false
}

# GitHub Actions OIDC
variable "github_repository" {
  description = "GitHub repository in OWNER/REPO form for OIDC role trust. Empty disables the OIDC role."
  type        = string
  default     = ""
}

variable "github_oidc_allowed_refs" {
  description = "Git refs allowed to assume the OIDC role"
  type        = list(string)
  default     = ["refs/heads/main"]
}

variable "github_oidc_create_provider" {
  description = "Create the GitHub OIDC provider in this account. Set false if it already exists."
  type        = bool
  default     = true
}
