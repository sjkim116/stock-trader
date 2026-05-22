output "replication_group_id" {
  description = "Replication group identifier"
  value       = aws_elasticache_replication_group.this.id
}

output "primary_endpoint_address" {
  description = "Primary endpoint DNS for writes"
  value       = aws_elasticache_replication_group.this.primary_endpoint_address
}

output "reader_endpoint_address" {
  description = "Reader endpoint DNS (only meaningful when HA)"
  value       = aws_elasticache_replication_group.this.reader_endpoint_address
}

output "port" {
  description = "Redis port"
  value       = aws_elasticache_replication_group.this.port
}

output "auth_token_secret_arn" {
  description = "Secrets Manager ARN holding the Redis AUTH token (null when auth disabled)"
  value       = length(aws_secretsmanager_secret.auth_token) > 0 ? aws_secretsmanager_secret.auth_token[0].arn : null
}

output "tls_enabled" {
  description = "Whether TLS is enabled"
  value       = var.transit_encryption_enabled
}
