output "instance_id" {
  description = "personal-host EC2 instance ID"
  value       = aws_instance.this.id
}

output "public_ip" {
  description = "Elastic IP — point a Route53 A record here for a stable URL"
  value       = aws_eip.this.public_ip
}

output "public_dns" {
  description = "AWS-assigned public DNS of the instance (changes on stop/start without EIP)"
  value       = aws_instance.this.public_dns
}

output "security_group_id" {
  description = "Security group attached to the instance"
  value       = aws_security_group.this.id
}

output "data_volume_id" {
  description = "EBS data volume ID (Snapshot=daily tag drives DLM)"
  value       = aws_ebs_volume.data.id
}

output "log_group_name" {
  description = "CloudWatch log group for forwarded system + bootstrap logs"
  value       = aws_cloudwatch_log_group.this.name
}

output "instance_role_arn" {
  description = "IAM role ARN attached to the instance — grant additional secrets here via var.secrets_to_grant_read"
  value       = aws_iam_role.this.arn
}
