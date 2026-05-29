terraform {
  required_version = ">= 1.5.0"

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

  # Partial S3 backend — values injected per environment via
  # `terraform init -backend-config=environments/<env>/backend.hcl`.
  # The bucket + DynamoDB lock table are provisioned by the
  # `../bootstrap/` stack (same as scaled-saas/).
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Stack       = "personal"
    }
  }
}

data "aws_caller_identity" "current" {}
