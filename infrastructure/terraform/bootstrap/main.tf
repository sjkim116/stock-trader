# Bootstrap stack: creates the S3 bucket and DynamoDB table that host Terraform
# remote state for the rest of the project. This stack itself stays on local
# state by design — it can't depend on the very backend it's creating.
#
# Apply this ONCE per AWS account/region, then activate the partial S3 backend
# in the root module (see bootstrap/README.md).

locals {
  account_id    = data.aws_caller_identity.current.account_id
  bucket_name   = var.state_bucket_name != "" ? var.state_bucket_name : "${var.project_name}-tfstate-${local.account_id}"
  kms_key_alias = "alias/${var.project_name}-tfstate"
}

# Optional customer-managed KMS key for state encryption
resource "aws_kms_key" "state" {
  count                   = var.use_kms_encryption ? 1 : 0
  description             = "KMS key for Terraform state bucket"
  deletion_window_in_days = var.kms_deletion_window_days
  enable_key_rotation     = true

  tags = {
    Name = "${var.project_name}-tfstate-key"
  }
}

resource "aws_kms_alias" "state" {
  count         = var.use_kms_encryption ? 1 : 0
  name          = local.kms_key_alias
  target_key_id = aws_kms_key.state[0].key_id
}

resource "aws_s3_bucket" "state" {
  bucket = local.bucket_name

  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name = local.bucket_name
  }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    bucket_key_enabled = var.use_kms_encryption

    apply_server_side_encryption_by_default {
      sse_algorithm     = var.use_kms_encryption ? "aws:kms" : "AES256"
      kms_master_key_id = var.use_kms_encryption ? aws_kms_key.state[0].arn : null
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket = aws_s3_bucket.state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    id     = "expire-noncurrent-state-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = var.noncurrent_version_expiration_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Deny any plaintext (non-TLS) request to the state bucket
resource "aws_s3_bucket_policy" "state_tls_only" {
  bucket = aws_s3_bucket.state.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource = [
        aws_s3_bucket.state.arn,
        "${aws_s3_bucket.state.arn}/*"
      ]
      Condition = {
        Bool = { "aws:SecureTransport" = "false" }
      }
    }]
  })
}

resource "aws_dynamodb_table" "locks" {
  name         = var.lock_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = var.use_kms_encryption ? aws_kms_key.state[0].arn : null
  }

  point_in_time_recovery {
    enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name = var.lock_table_name
  }
}
