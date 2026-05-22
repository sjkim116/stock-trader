# Terraform State Backend Bootstrap

This stack creates the S3 bucket and DynamoDB table that host remote state for
the rest of the project. It is intentionally separate from the root module:
**it has its own local state**, because it can't depend on the very backend
it is creating.

## What it creates

- `s3://<project>-tfstate-<account-id>` — versioned, encrypted, public-access blocked, TLS-only, with a 90-day lifecycle on noncurrent versions.
- `dynamodb:<project>-terraform-locks` — pay-per-request, PITR enabled, SSE.
- Optional customer-managed KMS key (`use_kms_encryption = true`) for both.

Both resources carry `lifecycle { prevent_destroy = true }` — Terraform will
refuse to delete them via `terraform destroy` even if removed from config.

## One-time apply

Run from this directory **once per AWS account/region**. Credentials are
expected in the usual AWS provider chain (env vars, `~/.aws/credentials`,
SSO profile, etc.).

```powershell
# From repo root, using the dockerized Terraform CLI:
docker run --rm -v "D:\Work\stock-trader\infrastructure\terraform\bootstrap:/tf" -w /tf `
    -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN -e AWS_REGION `
    hashicorp/terraform:1.7 init

docker run --rm -v "D:\Work\stock-trader\infrastructure\terraform\bootstrap:/tf" -w /tf `
    -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN -e AWS_REGION `
    hashicorp/terraform:1.7 apply
```

Capture the `state_bucket_name` output — you'll paste it into the env backend
config in the next step.

## Wire up the root module

The root `providers.tf` already declares a **partial** backend:

```hcl
backend "s3" {}
```

Provide the values per environment via `-backend-config`. Edit
`environments/dev/backend.hcl` (and `environments/prod/backend.hcl`) and
replace `REPLACE_WITH_ACCOUNT_ID` with the actual bucket name from the
bootstrap output:

```hcl
bucket         = "algotrader-tfstate-123456789012"
key            = "dev/terraform.tfstate"
region         = "ap-northeast-2"
dynamodb_table = "algotrader-terraform-locks"
encrypt        = true
```

Then init the root module against that backend:

```powershell
docker run --rm -v "D:\Work\stock-trader\infrastructure\terraform:/tf" -w /tf `
    -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN -e AWS_REGION `
    hashicorp/terraform:1.7 init -backend-config=environments/dev/backend.hcl
```

If state already exists locally (e.g. from earlier `-backend=false` runs),
Terraform will prompt to migrate it to S3. Answer `yes`.

## Locking down the bootstrap state file

After apply, the bootstrap directory will contain a `terraform.tfstate` file
holding credentials-adjacent metadata (S3 ARN, KMS key ID, etc.). Options:

- Keep it local and add `infrastructure/terraform/bootstrap/terraform.tfstate*` to `.gitignore` (default — recommended for small teams).
- Upload it to the state bucket itself under a `bootstrap/terraform.tfstate` key after the fact (manual `terraform state push`), then change this stack to use a partial backend too.

Do not commit the local state.
