output "repository_urls" {
  description = "Map of repository short name to repository URL"
  value       = { for k, repo in aws_ecr_repository.this : k => repo.repository_url }
}

output "repository_arns" {
  description = "Map of repository short name to repository ARN"
  value       = { for k, repo in aws_ecr_repository.this : k => repo.arn }
}

output "registry_id" {
  description = "Registry ID (AWS account ID) hosting the repositories"
  value       = length(aws_ecr_repository.this) > 0 ? values(aws_ecr_repository.this)[0].registry_id : null
}
