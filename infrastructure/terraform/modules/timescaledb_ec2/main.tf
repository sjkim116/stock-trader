# TimescaleDB on EC2 — single-instance, EBS-backed time-series database.
#
# Why this module exists: AWS RDS PostgreSQL does not ship the TimescaleDB
# extension, and the schema in `database/schema_timeseries.sql` relies on
# hypertables + native compression + retention policies. Running Timescale
# on EC2 keeps the full feature surface without onboarding a separate vendor.
#
# Topology: one EC2 instance in a private subnet, separate gp3 data EBS,
# daily DLM snapshots, master credential in Secrets Manager. OLTP workload
# stays on RDS (`modules/rds`).

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
  name        = "${var.project_name}-${var.environment}-timescaledb"
  log_group   = "/aws/ec2/${local.name}"
  data_mount  = "/var/lib/postgresql"
  data_device = "/dev/xvdf"
}

data "aws_region" "current" {}

data "aws_subnet" "this" {
  id = var.subnet_id
}

data "aws_vpc" "this" {
  id = var.vpc_id
}

data "aws_ami" "ubuntu_2204" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# --- security group ---------------------------------------------------------

resource "aws_security_group" "this" {
  name        = "${local.name}-sg"
  description = "TimescaleDB EC2 — PostgreSQL from app SGs only"
  vpc_id      = var.vpc_id

  egress {
    description = "All outbound (package repos, SSM, CloudWatch, Secrets Manager)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name}-sg"
  }
}

resource "aws_security_group_rule" "ingress_postgres" {
  for_each                 = toset(var.client_security_group_ids)
  type                     = "ingress"
  from_port                = var.db_port
  to_port                  = var.db_port
  protocol                 = "tcp"
  security_group_id        = aws_security_group.this.id
  source_security_group_id = each.value
  description              = "PostgreSQL from client SG ${each.value}"
}

# --- master credential ------------------------------------------------------

resource "random_password" "master" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_secretsmanager_secret" "credentials" {
  name        = "${local.name}/credentials"
  description = "TimescaleDB master credentials for ${local.name}"
  kms_key_id  = var.kms_key_id != "" ? var.kms_key_id : null

  tags = {
    Name = "${local.name}-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "credentials" {
  secret_id = aws_secretsmanager_secret.credentials.id
  # Only username + password live in the secret so the bootstrap script can
  # read it without a circular dependency on the instance. Host / port / dbname
  # are surfaced as module outputs (plaintext, non-sensitive).
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.master.result
  })
}

# --- IAM (SSM + CloudWatch + read its own secret) ---------------------------

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "this" {
  name               = "${local.name}-role"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "cw_agent" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_role_policy_attachment" "extra" {
  for_each   = toset(var.additional_iam_policy_arns)
  role       = aws_iam_role.this.name
  policy_arn = each.value
}

data "aws_iam_policy_document" "read_secret" {
  statement {
    actions   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
    resources = [aws_secretsmanager_secret.credentials.arn]
  }
}

resource "aws_iam_role_policy" "read_secret" {
  name   = "${local.name}-read-secret"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.read_secret.json
}

resource "aws_iam_instance_profile" "this" {
  name = "${local.name}-profile"
  role = aws_iam_role.this.name
}

# --- data EBS volume --------------------------------------------------------

resource "aws_ebs_volume" "data" {
  availability_zone = data.aws_subnet.this.availability_zone
  size              = var.data_volume_size_gb
  type              = "gp3"
  iops              = var.data_volume_iops
  throughput        = var.data_volume_throughput_mbps
  encrypted         = true
  kms_key_id        = var.kms_key_id != "" ? var.kms_key_id : null

  tags = {
    Name      = "${local.name}-data"
    Snapshot  = "daily"
    Component = "timescaledb"
  }

  lifecycle {
    prevent_destroy = true
  }
}

# --- log group --------------------------------------------------------------

resource "aws_cloudwatch_log_group" "this" {
  name              = local.log_group
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${local.name}-logs"
  }
}

# --- EC2 instance -----------------------------------------------------------

locals {
  user_data = templatefile("${path.module}/user-data.sh.tpl", {
    PG_MAJOR       = var.postgres_version
    TS_PKG_VERSION = var.timescaledb_version
    DATA_DEVICE    = local.data_device
    DATA_MOUNT     = local.data_mount
    DB_NAME        = var.db_name
    DB_USER        = var.db_username
    DB_PORT        = var.db_port
    SECRET_ID      = aws_secretsmanager_secret.credentials.id
    AWS_REGION     = data.aws_region.current.name
    VPC_CIDR       = data.aws_vpc.this.cidr_block
    LOG_GROUP      = local.log_group
  })
}

resource "aws_instance" "this" {
  ami                    = data.aws_ami.ubuntu_2204.id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.this.id]
  iam_instance_profile   = aws_iam_instance_profile.this.name

  user_data                            = local.user_data
  user_data_replace_on_change          = false
  instance_initiated_shutdown_behavior = "stop"

  metadata_options {
    http_tokens                 = "required"
    http_endpoint               = "enabled"
    http_put_response_hop_limit = 2
  }

  root_block_device {
    volume_size           = 20
    volume_type           = "gp3"
    encrypted             = true
    kms_key_id            = var.kms_key_id != "" ? var.kms_key_id : null
    delete_on_termination = true
  }

  tags = {
    Name      = local.name
    Component = "timescaledb"
  }

  lifecycle {
    ignore_changes = [
      ami,
      user_data,
    ]
  }
}

resource "aws_volume_attachment" "data" {
  device_name                    = local.data_device
  volume_id                      = aws_ebs_volume.data.id
  instance_id                    = aws_instance.this.id
  force_detach                   = false
  stop_instance_before_detaching = true
}

# --- DLM snapshot lifecycle -------------------------------------------------

data "aws_iam_policy_document" "dlm_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["dlm.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "dlm" {
  name               = "${local.name}-dlm"
  assume_role_policy = data.aws_iam_policy_document.dlm_assume.json
}

resource "aws_iam_role_policy_attachment" "dlm" {
  role       = aws_iam_role.dlm.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSDataLifecycleManagerServiceRole"
}

resource "aws_dlm_lifecycle_policy" "snapshots" {
  description        = "${local.name} daily EBS snapshots"
  execution_role_arn = aws_iam_role.dlm.arn
  state              = "ENABLED"

  policy_details {
    resource_types = ["VOLUME"]

    target_tags = {
      Snapshot = "daily"
    }

    schedule {
      name = "daily-${var.snapshot_retention_count}"

      create_rule {
        cron_expression = var.snapshot_schedule_cron
      }

      retain_rule {
        count = var.snapshot_retention_count
      }

      copy_tags = true

      tags_to_add = {
        SnapshotCreator = "DLM"
        Source          = local.name
      }
    }
  }
}

# --- private DNS record (optional) -----------------------------------------

locals {
  dns_host = var.private_zone_id != "" ? "${var.dns_record_name}.${data.aws_route53_zone.private[0].name}" : aws_instance.this.private_dns
}

data "aws_route53_zone" "private" {
  count   = var.private_zone_id != "" ? 1 : 0
  zone_id = var.private_zone_id
}

resource "aws_route53_record" "this" {
  count   = var.private_zone_id != "" ? 1 : 0
  zone_id = var.private_zone_id
  name    = var.dns_record_name
  type    = "A"
  ttl     = 60
  records = [aws_instance.this.private_ip]
}
