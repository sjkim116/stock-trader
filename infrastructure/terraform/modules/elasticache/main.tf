terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

locals {
  identifier = "${var.project_name}-${var.environment}"
  default_parameters = {
    "maxmemory-policy" = "allkeys-lru"
  }
  effective_parameters = merge(local.default_parameters, var.parameter_overrides)
  ha_enabled           = var.num_cache_clusters > 1
  auth_enabled         = var.auth_token_enabled && var.transit_encryption_enabled
}

resource "aws_elasticache_subnet_group" "this" {
  name        = "${local.identifier}-cache-subnet-group"
  description = "Subnet group for ${local.identifier} Redis"
  subnet_ids  = var.subnet_ids
}

resource "aws_elasticache_parameter_group" "this" {
  name        = "${local.identifier}-redis"
  family      = var.parameter_group_family
  description = "Parameter group for ${local.identifier} Redis"

  dynamic "parameter" {
    for_each = local.effective_parameters
    content {
      name  = parameter.key
      value = parameter.value
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "random_password" "auth_token" {
  count            = local.auth_enabled ? 1 : 0
  length           = 64
  special          = true
  override_special = "!&#$^<>-"
}

resource "aws_secretsmanager_secret" "auth_token" {
  count       = local.auth_enabled ? 1 : 0
  name        = "${local.identifier}/redis/auth-token"
  description = "Redis AUTH token for ${local.identifier}"
}

resource "aws_secretsmanager_secret_version" "auth_token" {
  count     = local.auth_enabled ? 1 : 0
  secret_id = aws_secretsmanager_secret.auth_token[0].id
  secret_string = jsonencode({
    auth_token = random_password.auth_token[0].result
    host       = aws_elasticache_replication_group.this.primary_endpoint_address
    port       = aws_elasticache_replication_group.this.port
    tls        = var.transit_encryption_enabled
  })
}

resource "aws_cloudwatch_log_group" "slow" {
  name              = "/aws/elasticache/${local.identifier}/slow-log"
  retention_in_days = var.log_retention_days
}

resource "aws_elasticache_replication_group" "this" {
  replication_group_id = "${local.identifier}-redis"
  description          = "Redis replication group for ${local.identifier}"
  engine               = "redis"
  engine_version       = var.engine_version
  node_type            = var.node_type
  num_cache_clusters   = var.num_cache_clusters
  port                 = var.port
  parameter_group_name = aws_elasticache_parameter_group.this.name
  subnet_group_name    = aws_elasticache_subnet_group.this.name
  security_group_ids   = var.security_group_ids

  automatic_failover_enabled = local.ha_enabled
  multi_az_enabled           = local.ha_enabled

  at_rest_encryption_enabled = var.at_rest_encryption_enabled
  transit_encryption_enabled = var.transit_encryption_enabled
  auth_token                 = local.auth_enabled ? random_password.auth_token[0].result : null

  snapshot_retention_limit   = var.snapshot_retention_limit
  snapshot_window            = var.snapshot_window
  maintenance_window         = var.maintenance_window
  apply_immediately          = var.apply_immediately
  auto_minor_version_upgrade = true

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.slow.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }

  lifecycle {
    ignore_changes = [auth_token]
  }

  tags = {
    Name = "${local.identifier}-redis"
  }
}
