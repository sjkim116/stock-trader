output "instance_id" {
  description = "EC2 instance ID — `aws ssm start-session --target {id}` to shell in"
  value       = module.personal_host.instance_id
}

output "public_ip" {
  description = "Elastic IP — Route53 A record target"
  value       = module.personal_host.public_ip
}

output "public_dns" {
  description = "Instance public DNS (changes on stop without EIP — use public_ip for stability)"
  value       = module.personal_host.public_dns
}

output "data_volume_id" {
  description = "EBS data volume backing the docker-compose state"
  value       = module.personal_host.data_volume_id
}

output "app_credentials_secret_arn" {
  description = "Secrets Manager ARN for postgres/redis/jwt secrets. Cloud-init reads this on boot to render the compose .env"
  value       = aws_secretsmanager_secret.app_credentials.arn
  sensitive   = true
}

output "log_group_name" {
  description = "CloudWatch log group for system + bootstrap logs"
  value       = module.personal_host.log_group_name
}
