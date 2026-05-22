terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Intentionally no backend block — this stack lives on local state
  # so it can be applied before the remote backend exists.
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = "shared"
      ManagedBy   = "Terraform"
      Stack       = "bootstrap"
    }
  }
}

data "aws_caller_identity" "current" {}
