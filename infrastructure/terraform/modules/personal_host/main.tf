# personal_host — single EC2 that runs the docker-compose stack for a
# 1-user deployment. Targets ~25,000 KRW / month all-in (t4g.small +
# small EBS + EIP). The much larger scaled-saas/ architecture lives in
# the sibling stack for future reference.
#
# Topology: one ARM EC2 in a *public* subnet (no NAT gateway → biggest
# cost cut), separate gp3 data volume, EIP for stable public address,
# SG opens 80/443 (Caddy auto-HTTPS) and optionally 22 from an allow-list.

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
  name        = "${var.project_name}-${var.environment}-personal"
  log_group   = "/aws/ec2/${local.name}"
  data_mount  = "/data"
  data_device = "/dev/xvdf"
}

data "aws_region" "current" {}

data "aws_vpc" "this" {
  id = var.vpc_id
}

data "aws_subnet" "this" {
  id = var.subnet_id
}

# Ubuntu 22.04 ARM (matches t4g.* instance family).
data "aws_ami" "ubuntu_2204_arm" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-arm64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# --- security group --------------------------------------------------------

resource "aws_security_group" "this" {
  name        = "${local.name}-sg"
  description = "personal_host — HTTP/HTTPS from anywhere + optional SSH"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP (redirected to HTTPS by Caddy)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  dynamic "ingress" {
    for_each = length(var.allowed_ssh_cidrs) > 0 ? [1] : []
    content {
      description = "SSH from operator IP(s)"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = var.allowed_ssh_cidrs
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name}-sg"
  }
}

# --- IAM (SSM + CloudWatch + Secrets read) ---------------------------------

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

data "aws_iam_policy_document" "secrets_read" {
  count = length(var.secrets_to_grant_read) > 0 ? 1 : 0

  statement {
    actions   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
    resources = var.secrets_to_grant_read
  }
}

resource "aws_iam_role_policy" "secrets_read" {
  count  = length(var.secrets_to_grant_read) > 0 ? 1 : 0
  name   = "${local.name}-secrets-read"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.secrets_read[0].json
}

resource "aws_iam_instance_profile" "this" {
  name = "${local.name}-profile"
  role = aws_iam_role.this.name
}

# --- data EBS volume + EIP ------------------------------------------------

resource "aws_ebs_volume" "data" {
  availability_zone = data.aws_subnet.this.availability_zone
  size              = var.data_volume_size_gb
  type              = "gp3"
  encrypted         = true
  kms_key_id        = var.kms_key_id != "" ? var.kms_key_id : null

  tags = {
    Name      = "${local.name}-data"
    Snapshot  = "daily"
    Component = "personal_host"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_eip" "this" {
  domain = "vpc"

  tags = {
    Name = "${local.name}-eip"
  }
}

# --- CloudWatch log group --------------------------------------------------

resource "aws_cloudwatch_log_group" "this" {
  name              = local.log_group
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${local.name}-logs"
  }
}

# --- EC2 instance ----------------------------------------------------------

locals {
  user_data = templatefile("${path.module}/user-data.sh.tpl", {
    PROJECT     = var.project_name
    DATA_DEVICE = local.data_device
    DATA_MOUNT  = local.data_mount
    REPO_URL    = var.github_repo_url
    REPO_BRANCH = var.github_repo_branch
    LOG_GROUP   = local.log_group
  })
}

resource "aws_instance" "this" {
  ami                    = data.aws_ami.ubuntu_2204_arm.id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.this.id]
  iam_instance_profile   = aws_iam_instance_profile.this.name

  user_data                            = local.user_data
  user_data_replace_on_change          = false
  associate_public_ip_address          = true
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
    Component = "personal_host"
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

resource "aws_eip_association" "this" {
  instance_id   = aws_instance.this.id
  allocation_id = aws_eip.this.id
}

# --- DLM snapshot lifecycle -----------------------------------------------

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
