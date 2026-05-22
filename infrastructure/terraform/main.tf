# Main Terraform Configuration

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  enable_flow_logs   = var.environment == "production"
}

# Security Groups
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg-${var.environment}"
  description = "Security group for Application Load Balancer"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "HTTPS from Internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP from Internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-alb-sg-${var.environment}"
  }
}

resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-tasks-sg-${var.environment}"
  description = "Security group for ECS tasks"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "Allow traffic from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ecs-tasks-sg-${var.environment}"
  }
}

resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg-${var.environment}"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "PostgreSQL from ECS tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  tags = {
    Name = "${var.project_name}-rds-sg-${var.environment}"
  }
}

resource "aws_security_group" "redis" {
  name        = "${var.project_name}-redis-sg-${var.environment}"
  description = "Security group for ElastiCache Redis"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "Redis from ECS tasks"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  tags = {
    Name = "${var.project_name}-redis-sg-${var.environment}"
  }
}

# TimescaleDB EC2 ingress is owned by the timescaledb_ec2 module (it manages
# its own SG and per-client ingress rules), so no aws_security_group resource
# is declared here.

# S3 Bucket for Logs
resource "aws_s3_bucket" "logs" {
  bucket = "${var.project_name}-logs-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "${var.project_name}-logs-${var.environment}"
  }
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -----------------------------------------------------------------------------
# Phase 2 Week 2 — application platform modules
# -----------------------------------------------------------------------------

module "ecr" {
  source = "./modules/ecr"

  project_name = var.project_name
  environment  = var.environment
  repositories = var.ecr_repositories

  # Dev: allow repo deletion with images so tear-down is cheap. Override in prod tfvars.
  force_delete = var.environment != "production"
}

module "rds" {
  source = "./modules/rds"

  project_name       = var.project_name
  environment        = var.environment
  subnet_ids         = module.vpc.database_subnet_ids
  security_group_ids = [aws_security_group.rds.id]

  engine_version          = var.rds_engine_version
  instance_class          = var.rds_instance_class
  allocated_storage       = var.rds_allocated_storage
  max_allocated_storage   = var.rds_max_allocated_storage
  multi_az                = var.rds_multi_az
  deletion_protection     = var.rds_deletion_protection
  skip_final_snapshot     = var.rds_skip_final_snapshot
  backup_retention_period = var.environment == "production" ? 30 : 7
}

module "elasticache" {
  source = "./modules/elasticache"

  project_name       = var.project_name
  environment        = var.environment
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [aws_security_group.redis.id]

  node_type          = var.redis_node_type
  num_cache_clusters = var.redis_num_cache_clusters
}

module "timescaledb" {
  source = "./modules/timescaledb_ec2"

  project_name              = var.project_name
  environment               = var.environment
  vpc_id                    = module.vpc.vpc_id
  subnet_id                 = module.vpc.private_subnet_ids[0]
  client_security_group_ids = [aws_security_group.ecs_tasks.id]

  instance_type            = var.timescaledb_instance_type
  data_volume_size_gb      = var.timescaledb_data_volume_size_gb
  snapshot_retention_count = var.timescaledb_snapshot_retention_count
}

module "alb" {
  source = "./modules/alb"

  project_name       = var.project_name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.public_subnet_ids
  security_group_ids = [aws_security_group.alb.id]

  target_port         = 8000
  health_check_path   = "/health"
  certificate_arn     = var.certificate_arn
  deletion_protection = var.alb_deletion_protection
}

module "ecs_user_api" {
  source = "./modules/ecs"

  project_name       = var.project_name
  environment        = var.environment
  aws_region         = var.aws_region
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [aws_security_group.ecs_tasks.id]
  target_group_arn   = module.alb.user_api_target_group_arn

  service_name    = "user-api"
  container_image = "${module.ecr.repository_urls["user-api"]}:${var.container_image_tag}"
  container_port  = 8000
  task_cpu        = var.ecs_task_cpu
  task_memory     = var.ecs_task_memory
  desired_count   = var.user_api_desired_count

  database_endpoint   = module.rds.address
  database_port       = module.rds.port
  database_name       = module.rds.db_name
  database_username   = "algotrader"
  database_secret_arn = module.rds.credentials_secret_arn

  redis_host            = module.elasticache.primary_endpoint_address
  redis_port            = module.elasticache.port
  redis_tls_enabled     = module.elasticache.tls_enabled
  redis_auth_secret_arn = module.elasticache.auth_token_secret_arn != null ? module.elasticache.auth_token_secret_arn : ""

  additional_environment_variables = {
    TIMESCALEDB_HOST     = module.timescaledb.endpoint
    TIMESCALEDB_PORT     = tostring(module.timescaledb.port)
    TIMESCALEDB_NAME     = module.timescaledb.db_name
    TIMESCALEDB_USERNAME = module.timescaledb.db_username
  }

  additional_secret_environment_variables = {
    TIMESCALEDB_PASSWORD = "${module.timescaledb.credentials_secret_arn}:password::"
  }

  additional_secret_arns = [module.timescaledb.credentials_secret_arn]
}

# GitHub Actions OIDC role — only when github_repository is set
module "github_oidc" {
  count  = var.github_repository != "" ? 1 : 0
  source = "./modules/github_oidc"

  project_name         = var.project_name
  environment          = var.environment
  github_repository    = var.github_repository
  allowed_refs         = var.github_oidc_allowed_refs
  create_oidc_provider = var.github_oidc_create_provider
  ecr_repository_arns  = values(module.ecr.repository_arns)
}
