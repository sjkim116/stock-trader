output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnet_ids
}

output "database_subnet_ids" {
  description = "Database subnet IDs"
  value       = module.vpc.database_subnet_ids
}

output "ecr_repository_urls" {
  description = "Map of ECR short name to repository URL — use with `docker push <url>:<tag>`"
  value       = module.ecr.repository_urls
}

output "alb_dns_name" {
  description = "Public ALB DNS name"
  value       = module.alb.alb_dns_name
}

output "alb_zone_id" {
  description = "ALB hosted zone ID (use for Route 53 alias records)"
  value       = module.alb.alb_zone_id
}

output "rds_address" {
  description = "RDS endpoint host"
  value       = module.rds.address
}

output "rds_credentials_secret_arn" {
  description = "Secrets Manager ARN for RDS master credentials"
  value       = module.rds.credentials_secret_arn
  sensitive   = true
}

output "redis_primary_endpoint" {
  description = "Redis primary endpoint host"
  value       = module.elasticache.primary_endpoint_address
}

output "redis_auth_secret_arn" {
  description = "Secrets Manager ARN for Redis AUTH token (null when AUTH disabled)"
  value       = module.elasticache.auth_token_secret_arn
  sensitive   = true
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs_user_api.cluster_name
}

output "ecs_user_api_service_name" {
  description = "ECS user-api service name"
  value       = module.ecs_user_api.service_name
}

output "ecs_user_api_log_group" {
  description = "CloudWatch log group for user-api task"
  value       = module.ecs_user_api.log_group_name
}

output "logs_bucket_name" {
  description = "S3 bucket for shared logs"
  value       = aws_s3_bucket.logs.bucket
}

output "github_oidc_role_arn" {
  description = "IAM role ARN for GitHub Actions OIDC (null if github_repository unset)"
  value       = length(module.github_oidc) > 0 ? module.github_oidc[0].role_arn : null
}
