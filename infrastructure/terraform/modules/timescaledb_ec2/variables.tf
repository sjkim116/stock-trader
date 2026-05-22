variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the instance is launched"
  type        = string
}

variable "subnet_id" {
  description = "Private subnet ID for the EC2 instance. Single-AZ by design; HA is achieved via EBS snapshot + AMI restore until a replica module is added."
  type        = string
}

variable "client_security_group_ids" {
  description = "Security group IDs allowed to connect to PostgreSQL (typically the ECS task SG and ops bastion if any)"
  type        = list(string)
}

variable "instance_type" {
  description = "EC2 instance type. r-class recommended for memory-bound TimescaleDB workloads."
  type        = string
  default     = "r6i.large"
}

variable "data_volume_size_gb" {
  description = "Initial EBS data volume size in GB (gp3, separate from root). Grow online with aws_ebs_volume modify."
  type        = number
  default     = 200
}

variable "data_volume_iops" {
  description = "Provisioned IOPS for the gp3 data volume"
  type        = number
  default     = 3000
}

variable "data_volume_throughput_mbps" {
  description = "Provisioned throughput (MiB/s) for the gp3 data volume"
  type        = number
  default     = 125
}

variable "kms_key_id" {
  description = "KMS key ID for EBS + secret encryption. Empty uses the AWS-managed default."
  type        = string
  default     = ""
}

variable "db_name" {
  description = "Initial database name to create for time-series data"
  type        = string
  default     = "algotrader_ts"
}

variable "db_username" {
  description = "Master username for the time-series database"
  type        = string
  default     = "algotrader"
}

variable "db_port" {
  description = "PostgreSQL listen port"
  type        = number
  default     = 5432
}

variable "postgres_version" {
  description = "PostgreSQL major version (must match the TimescaleDB package available in the upstream repo)"
  type        = string
  default     = "15"
}

variable "timescaledb_version" {
  description = "TimescaleDB apt/yum package version constraint. Empty installs the latest 2.x for the given PG version."
  type        = string
  default     = ""
}

variable "snapshot_retention_count" {
  description = "Number of daily EBS snapshots to retain via Data Lifecycle Manager"
  type        = number
  default     = 14
}

variable "snapshot_schedule_cron" {
  description = "DLM schedule cron expression (UTC). Default 18:00 UTC = 03:00 KST, after KR market close."
  type        = string
  default     = "cron(0 18 * * ? *)"
}

variable "log_retention_days" {
  description = "CloudWatch log group retention for postgres logs"
  type        = number
  default     = 30
}

variable "private_zone_id" {
  description = "Route53 private hosted zone ID for the stable DNS record. Empty skips record creation."
  type        = string
  default     = ""
}

variable "dns_record_name" {
  description = "DNS record name (without zone suffix) for the TS endpoint, e.g. \"timescaledb\""
  type        = string
  default     = "timescaledb"
}

variable "additional_iam_policy_arns" {
  description = "Additional managed policy ARNs to attach to the instance role (e.g. extra ops policies)"
  type        = list(string)
  default     = []
}
