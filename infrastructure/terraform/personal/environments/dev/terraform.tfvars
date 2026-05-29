environment = "dev"
aws_region  = "ap-northeast-2"

# Cheap default — bump if memory pressure shows up.
instance_type       = "t4g.small"
data_volume_size_gb = 50

github_repo_url    = "https://github.com/sjkim116/stock-trader.git"
github_repo_branch = "main"

# SSH ingress disabled by default — use SSM Session Manager.
allowed_ssh_cidrs = []

snapshot_retention_count = 14
