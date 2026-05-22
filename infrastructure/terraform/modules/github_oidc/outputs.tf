output "role_arn" {
  description = "IAM role ARN to put in the GitHub Actions workflow as `role-to-assume`"
  value       = aws_iam_role.this.arn
}

output "role_name" {
  description = "IAM role name"
  value       = aws_iam_role.this.name
}

output "oidc_provider_arn" {
  description = "OIDC provider ARN (newly created or existing, depending on create_oidc_provider)"
  value       = local.oidc_provider_arn
}
