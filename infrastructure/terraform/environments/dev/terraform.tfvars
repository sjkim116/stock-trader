# Development Environment Configuration

project_name = "algotrader"
environment  = "dev"
aws_region   = "ap-northeast-2"

# VPC
vpc_cidr           = "10.0.0.0/16"
availability_zones = ["ap-northeast-2a", "ap-northeast-2b"]

# RDS
rds_instance_class    = "db.t3.micro"
rds_allocated_storage = 20
rds_multi_az          = false

# Redis
redis_node_type          = "cache.t3.micro"
redis_num_cache_clusters = 1

# ECS
ecs_task_cpu           = 256
ecs_task_memory        = 512
user_api_desired_count = 1

# Domain
domain_name = "dev.algotrader.dev"
alert_email = "dev-alerts@algotrader.dev"

# Container image
container_image_tag = "latest"

# Dev hardening — relaxed so tear-down is cheap
rds_deletion_protection   = false
rds_skip_final_snapshot   = true
alb_deletion_protection   = false
rds_max_allocated_storage = 50

# GitHub Actions OIDC
github_repository           = "sjkim116/stock-trader"
github_oidc_allowed_refs    = ["refs/heads/main"]
github_oidc_create_provider = true
