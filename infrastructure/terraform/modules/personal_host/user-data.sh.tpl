#!/usr/bin/env bash
# personal_host bootstrap.
#
# Idempotent: re-running on an existing host reattaches the data volume,
# pulls the latest git ref, and `docker compose up -d`s. The CD path
# from this point is "ssh in, git pull, docker compose up -d" — no ECR
# or pipeline required for a 1-user tool.
#
# Template variables (templatefile):
#   PROJECT      service tag prefix
#   DATA_DEVICE  expected block device for the EBS data volume
#   DATA_MOUNT   where to mount it (Docker volumes live here)
#   REPO_URL     git remote to clone (empty ⇒ skip clone, leave empty checkout)
#   REPO_BRANCH  branch to check out
#   LOG_GROUP    CloudWatch log group for /var/log forwarders

set -euo pipefail
exec > >(tee -a /var/log/personal-host-bootstrap.log) 2>&1
echo "[bootstrap] starting at $(date -Is)"

PROJECT='${PROJECT}'
DATA_DEVICE='${DATA_DEVICE}'
DATA_MOUNT='${DATA_MOUNT}'
REPO_URL='${REPO_URL}'
REPO_BRANCH='${REPO_BRANCH}'
LOG_GROUP='${LOG_GROUP}'

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y curl gnupg lsb-release ca-certificates git jq xfsprogs unzip awscli amazon-cloudwatch-agent

# --- 1. Docker -------------------------------------------------------------
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

# --- 2. data volume --------------------------------------------------------
resolve_device() {
  if [ -b "$${DATA_DEVICE}" ]; then echo "$${DATA_DEVICE}"; return; fi
  for d in /dev/nvme*n1; do
    serial=$(nvme id-ctrl -o json "$${d}" 2>/dev/null | jq -r '.sn // empty' || true)
    if [ -n "$${serial}" ] && [ "/dev/$${serial}" = "$${DATA_DEVICE}" ]; then
      echo "$${d}"; return
    fi
  done
  echo "$${DATA_DEVICE}"
}
DEV=$(resolve_device)
echo "[bootstrap] data device: $${DEV}"

if ! blkid "$${DEV}" >/dev/null 2>&1; then
  mkfs.xfs -L data "$${DEV}"
fi
mkdir -p "$${DATA_MOUNT}"
UUID=$(blkid -s UUID -o value "$${DEV}")
if ! grep -q "$${UUID}" /etc/fstab; then
  echo "UUID=$${UUID} $${DATA_MOUNT} xfs defaults,nofail,noatime 0 2" >> /etc/fstab
fi
mount -a

# --- 3. clone the app ------------------------------------------------------
APP_DIR="$${DATA_MOUNT}/${PROJECT}"
mkdir -p "$${APP_DIR}"

if [ -n "$${REPO_URL}" ]; then
  if [ ! -d "$${APP_DIR}/.git" ]; then
    git clone --branch "$${REPO_BRANCH}" "$${REPO_URL}" "$${APP_DIR}"
  else
    cd "$${APP_DIR}"
    git fetch --depth 1 origin "$${REPO_BRANCH}"
    git checkout "$${REPO_BRANCH}"
    git reset --hard "origin/$${REPO_BRANCH}"
  fi
fi

# --- 4. docker compose up --------------------------------------------------
# The repo must ship a docker-compose.production.yml (or honour the
# vanilla docker-compose.yml for now — first deploys can iterate).
cd "$${APP_DIR}"
COMPOSE_FILE="docker-compose.production.yml"
if [ ! -f "$${COMPOSE_FILE}" ]; then
  # Fall back to the dev compose file. Caveat: it exposes Postgres + Redis
  # on the host network; tighten before going live by writing the prod
  # variant. Tracked in the personal-infra PR description.
  COMPOSE_FILE="docker-compose.yml"
fi
if [ -f "$${COMPOSE_FILE}" ]; then
  docker compose -f "$${COMPOSE_FILE}" pull || true
  docker compose -f "$${COMPOSE_FILE}" up -d --build
fi

# --- 5. CloudWatch agent ---------------------------------------------------
cat > /opt/aws/amazon-cloudwatch-agent/etc/personal-host.json <<EOF
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/personal-host-bootstrap.log",
            "log_group_name": "$${LOG_GROUP}",
            "log_stream_name": "{instance_id}/bootstrap",
            "timezone": "UTC",
            "retention_in_days": 30
          },
          {
            "file_path": "/var/log/syslog",
            "log_group_name": "$${LOG_GROUP}",
            "log_stream_name": "{instance_id}/syslog",
            "timezone": "UTC",
            "retention_in_days": 30
          }
        ]
      }
    }
  }
}
EOF
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/personal-host.json

echo "[bootstrap] done at $(date -Is)"
