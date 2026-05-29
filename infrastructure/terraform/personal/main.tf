# Personal-use stack — single EC2 running the whole docker-compose
# stack. Targets ~25,000 KRW / month all-in. The full SaaS-grade
# architecture (ECS + RDS + ElastiCache + ALB) lives in ../scaled-saas/
# for reference; this stack consciously trades availability + scale
# for cost and operational simplicity.

# --- minimal VPC -----------------------------------------------------------
# Single AZ, one public subnet, no NAT gateway. We can't use the existing
# `modules/vpc` module because it provisions 2 AZ + private subnets + NAT
# (~$32/mo NAT eats most of the budget cut). Inlining here keeps the
# personal stack self-contained.

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-personal-vpc"
  }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = {
    Name = "${var.project_name}-personal-igw"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.this.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, 0)
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-personal-public"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = {
    Name = "${var.project_name}-personal-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# --- personal host ---------------------------------------------------------

module "personal_host" {
  source = "../modules/personal_host"

  project_name = var.project_name
  environment  = var.environment
  vpc_id       = aws_vpc.this.id
  subnet_id    = aws_subnet.public.id

  instance_type            = var.instance_type
  data_volume_size_gb      = var.data_volume_size_gb
  allowed_ssh_cidrs        = var.allowed_ssh_cidrs
  github_repo_url          = var.github_repo_url
  github_repo_branch       = var.github_repo_branch
  snapshot_retention_count = var.snapshot_retention_count

  secrets_to_grant_read = compact([
    var.kis_app_secret_arn,
    # The personal stack also produces a credentials secret (random
    # postgres + JWT keys) — pre-granted via the secret's resource
    # policy isn't necessary because we wire its ARN through here.
    aws_secretsmanager_secret.app_credentials.arn,
  ])
}

# --- app credentials --------------------------------------------------------
# One secret holds everything the docker-compose stack reads: postgres
# password, redis password, JWT key. user-data on the host pulls this
# JSON at boot and renders it into the compose `.env`.

resource "random_password" "postgres" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "random_password" "redis" {
  length  = 32
  special = false # redis ACL passwords don't love special chars
}

resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

resource "aws_secretsmanager_secret" "app_credentials" {
  name        = "${var.project_name}/${var.environment}/app-credentials"
  description = "personal-stack app credentials (postgres, redis, JWT)"

  tags = {
    Name = "${var.project_name}-${var.environment}-app-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "app_credentials" {
  secret_id = aws_secretsmanager_secret.app_credentials.id
  secret_string = jsonencode({
    postgres_password = random_password.postgres.result
    redis_password    = random_password.redis.result
    jwt_secret        = random_password.jwt_secret.result
  })
}
