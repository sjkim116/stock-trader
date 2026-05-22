output "state_bucket_name" {
  description = "S3 bucket name for Terraform state — set as `bucket =` in backend config"
  value       = aws_s3_bucket.state.bucket
}

output "state_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.state.arn
}

output "lock_table_name" {
  description = "DynamoDB table name for state locks — set as `dynamodb_table =` in backend config"
  value       = aws_dynamodb_table.locks.name
}

output "kms_key_arn" {
  description = "KMS key ARN if customer-managed encryption is enabled, else null"
  value       = length(aws_kms_key.state) > 0 ? aws_kms_key.state[0].arn : null
}

output "region" {
  description = "Region hosting the state backend — set as `region =` in backend config"
  value       = var.aws_region
}

output "backend_config_snippet" {
  description = "Snippet to paste into environments/<env>/backend.hcl"
  value       = <<-EOT
    bucket         = "${aws_s3_bucket.state.bucket}"
    key            = "<env>/terraform.tfstate"   # replace <env>, e.g. dev/terraform.tfstate
    region         = "${var.aws_region}"
    dynamodb_table = "${aws_dynamodb_table.locks.name}"
    encrypt        = true
  EOT
}
