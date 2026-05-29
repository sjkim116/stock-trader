# Infrastructure as Code

Two stacks live here. They're independent — you apply one, not both.

## `personal/` — the stack you actually use

Single EC2 (`t4g.small`) running the whole docker-compose stack
(postgres+TimescaleDB, redis, user-api, frontend). EBS data volume,
EIP, daily DLM snapshots. **~25,000 KRW / month all-in.**

Right-sized for the project's actual scope: one user, one account.

```
infrastructure/terraform/personal/
├── main.tf               minimal VPC (1 AZ, public subnet, no NAT) + personal_host
├── modules/personal_host EC2 + EBS + IAM + cloud-init bootstrap
└── environments/dev      tfvars + backend.hcl
```

### Apply

```
cd infrastructure/terraform/personal
terraform init -backend-config=environments/dev/backend.hcl
terraform apply -var-file=environments/dev/terraform.tfvars
```

(Run `../bootstrap/` once first to provision the state-backend S3 bucket
+ DynamoDB lock table.)

### Deploy app updates

`ssh ubuntu@<eip>` (or `aws ssm start-session --target <instance-id>`),
then:

```
cd /data/algotrader
git pull
docker compose up -d --build
```

No CI/CD pipeline — for a 1-user tool the ssh-and-pull loop is fine.

## `scaled-saas/` — archived multi-tenant design

The original Phase 2 Week 2 architecture: VPC across 2 AZ, ALB, ECS
Fargate, RDS PostgreSQL, ElastiCache Redis, EC2 TimescaleDB, OIDC for
CI/CD. **~330,000 KRW / month** at the lightest sizing.

Designed for SaaS scale before the project pivoted to personal-use
([memory: project_direction](../../../.claude/projects/D--Work-stock-trader/memory/project_direction.md)).
Never applied. Kept as a reference in case the direction changes.

```
infrastructure/terraform/scaled-saas/
├── main.tf            VPC + ALB + ECS + RDS + ElastiCache + EC2 TS + OIDC
└── environments/      dev + prod tfvars
```

Don't apply this on purpose — read it for the architectural shape.
The modules under `modules/` are shared between both stacks.

## `bootstrap/` — Terraform state backend

S3 + DynamoDB for remote state + locking. Apply once before either
stack. Same `bootstrap/` for both — the `key` in each backend.hcl
namespaces the state files.
