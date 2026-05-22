# RDS PostgreSQL module — OLTP tables only.
#
# AWS RDS does not ship the TimescaleDB extension, so the time-series
# tables (market_data, quote_data) live on a self-managed TimescaleDB host
# provisioned by modules/timescaledb_ec2. The OLTP schema in
# database/schema_oltp.sql targets this instance.

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
    "log_statement"              = "ddl"
    "log_min_duration_statement" = "1000"
    "shared_preload_libraries"   = "pg_stat_statements"
    "pg_stat_statements.track"   = "ALL"
  }
  effective_parameters = merge(local.default_parameters, var.parameter_overrides)
}

resource "aws_db_subnet_group" "this" {
  name        = "${local.identifier}-db-subnet-group"
  description = "Database subnet group for ${local.identifier}"
  subnet_ids  = var.subnet_ids

  tags = {
    Name = "${local.identifier}-db-subnet-group"
  }
}

resource "aws_db_parameter_group" "this" {
  name        = "${local.identifier}-pg"
  family      = var.family
  description = "Parameter group for ${local.identifier}"

  dynamic "parameter" {
    for_each = local.effective_parameters
    content {
      name         = parameter.key
      value        = parameter.value
      apply_method = contains(["shared_preload_libraries"], parameter.key) ? "pending-reboot" : "immediate"
    }
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${local.identifier}-pg"
  }
}

resource "random_password" "master" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${local.identifier}/rds/credentials"
  description = "RDS master credentials for ${local.identifier}"

  tags = {
    Name = "${local.identifier}-rds-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.username
    password = random_password.master.result
    host     = aws_db_instance.this.address
    port     = aws_db_instance.this.port
    dbname   = var.db_name
  })
}

resource "aws_iam_role" "rds_monitoring" {
  count = var.monitoring_interval > 0 ? 1 : 0
  name  = "${local.identifier}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "monitoring.rds.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  count      = var.monitoring_interval > 0 ? 1 : 0
  role       = aws_iam_role.rds_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

resource "aws_db_instance" "this" {
  identifier     = local.identifier
  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage > 0 ? var.max_allocated_storage : null
  storage_type          = var.storage_type
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.username
  password = random_password.master.result
  port     = var.port

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = var.security_group_ids
  parameter_group_name   = aws_db_parameter_group.this.name
  publicly_accessible    = false

  multi_az                = var.multi_az
  backup_retention_period = var.backup_retention_period
  backup_window           = var.backup_window
  maintenance_window      = var.maintenance_window
  copy_tags_to_snapshot   = true

  deletion_protection       = var.deletion_protection
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${local.identifier}-final-${formatdate("YYYYMMDDhhmmss", timestamp())}"

  performance_insights_enabled          = var.performance_insights_enabled
  performance_insights_retention_period = var.performance_insights_enabled ? var.performance_insights_retention_period : null

  monitoring_interval = var.monitoring_interval
  monitoring_role_arn = var.monitoring_interval > 0 ? aws_iam_role.rds_monitoring[0].arn : null

  enabled_cloudwatch_logs_exports = var.enabled_cloudwatch_logs_exports
  auto_minor_version_upgrade      = true
  apply_immediately               = var.apply_immediately

  lifecycle {
    ignore_changes = [
      final_snapshot_identifier,
      password,
    ]
  }

  tags = {
    Name = local.identifier
  }
}

resource "aws_cloudwatch_log_group" "postgresql" {
  for_each          = toset(var.enabled_cloudwatch_logs_exports)
  name              = "/aws/rds/instance/${aws_db_instance.this.identifier}/${each.value}"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${local.identifier}-${each.value}-logs"
  }
}
