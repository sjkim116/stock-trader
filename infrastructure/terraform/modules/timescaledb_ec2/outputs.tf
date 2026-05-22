output "instance_id" {
  description = "TimescaleDB EC2 instance ID"
  value       = aws_instance.this.id
}

output "private_ip" {
  description = "Private IP of the TimescaleDB instance"
  value       = aws_instance.this.private_ip
}

output "private_dns" {
  description = "AWS-assigned private DNS name of the instance"
  value       = aws_instance.this.private_dns
}

output "endpoint" {
  description = "Hostname clients should connect to. Stable DNS record when private_zone_id is set, otherwise the instance's private DNS."
  value       = local.dns_host
}

output "port" {
  description = "PostgreSQL port"
  value       = var.db_port
}

output "db_name" {
  description = "Initial database name created for time-series data"
  value       = var.db_name
}

output "db_username" {
  description = "Master username"
  value       = var.db_username
}

output "credentials_secret_arn" {
  description = "Secrets Manager ARN holding {username, password}"
  value       = aws_secretsmanager_secret.credentials.arn
}

output "credentials_secret_name" {
  description = "Secrets Manager secret name"
  value       = aws_secretsmanager_secret.credentials.name
}

output "security_group_id" {
  description = "Security group attached to the TimescaleDB instance — clients add an egress rule for this SG."
  value       = aws_security_group.this.id
}

output "data_volume_id" {
  description = "EBS data volume ID (also tagged Snapshot=daily for DLM)"
  value       = aws_ebs_volume.data.id
}

output "log_group_name" {
  description = "CloudWatch log group for postgres logs"
  value       = aws_cloudwatch_log_group.this.name
}
