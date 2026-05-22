output "cluster_id" {
  description = "ECS cluster ID"
  value       = aws_ecs_cluster.this.id
}

output "cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.this.name
}

output "service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.this.name
}

output "service_arn" {
  description = "ECS service ARN"
  value       = aws_ecs_service.this.id
}

output "task_definition_arn" {
  description = "Task definition ARN"
  value       = aws_ecs_task_definition.this.arn
}

output "task_role_arn" {
  description = "Task role ARN (assume in app for AWS SDK calls)"
  value       = aws_iam_role.task.arn
}

output "execution_role_arn" {
  description = "Execution role ARN"
  value       = aws_iam_role.execution.arn
}

output "log_group_name" {
  description = "CloudWatch log group for task logs"
  value       = aws_cloudwatch_log_group.task.name
}
