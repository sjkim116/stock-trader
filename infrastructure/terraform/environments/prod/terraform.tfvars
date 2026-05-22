# Production Environment Configuration

project_name = "algotrader"
environment  = "production"
aws_region   = "ap-northeast-2"

# VPC
vpc_cidr           = "10.10.0.0/16"
availability_zones = ["ap-northeast-2a", "ap-northeast-2b"]

# RDS — production hardening
rds_instance_class        = "db.t3.medium"
rds_allocated_storage     = 100
rds_max_allocated_storage = 500
rds_multi_az              = true
rds_deletion_protection   = true
rds_skip_final_snapshot   = false

# Redis — multi-node for HA
redis_node_type          = "cache.t3.small"
redis_num_cache_clusters = 2

# ECS
ecs_task_cpu           = 512
ecs_task_memory        = 1024
user_api_desired_count = 2

# Domain
domain_name = "algotrader.dev"
alert_email = "alerts@algotrader.dev"

# Container image — set by CI to the git SHA being deployed
container_image_tag = "latest"

# ALB
alb_deletion_protection = true
