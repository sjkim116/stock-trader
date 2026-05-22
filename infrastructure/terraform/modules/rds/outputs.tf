output "instance_id" {
  description = "RDS instance identifier"
  value       = aws_db_instance.this.id
}

output "endpoint" {
  description = "Connection endpoint (host:port)"
  value       = aws_db_instance.this.endpoint
}

output "address" {
  description = "DNS address of the RDS instance"
  value       = aws_db_instance.this.address
}

output "port" {
  description = "Database port"
  value       = aws_db_instance.this.port
}

output "db_name" {
  description = "Initial database name"
  value       = aws_db_instance.this.db_name
}

output "credentials_secret_arn" {
  description = "ARN of the Secrets Manager secret holding master credentials"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

output "credentials_secret_name" {
  description = "Name of the Secrets Manager secret holding master credentials"
  value       = aws_secretsmanager_secret.db_credentials.name
}
