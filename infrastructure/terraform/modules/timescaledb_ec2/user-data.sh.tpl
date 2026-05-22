#!/usr/bin/env bash
# TimescaleDB on EC2 bootstrap.
#
# Idempotent: re-running on an existing host with the data volume attached
# only re-applies pg_hba / postgresql.conf and ensures the service is up.
# It never re-initdbs over an existing data directory.
#
# Variables interpolated by Terraform via templatefile():
#   PG_MAJOR        — postgres major version, e.g. "15"
#   TS_PKG_VERSION  — empty for latest, or e.g. "2.14.2~ubuntu22.04"
#   DATA_DEVICE     — block device the data EBS volume is exposed as
#   DATA_MOUNT      — filesystem mount point for the data volume
#   DB_NAME         — initial database to create
#   DB_USER         — master role
#   DB_PORT         — listen port
#   SECRET_ID       — Secrets Manager secret id holding {"password": "..."}
#   AWS_REGION      — region for the AWS CLI
#   VPC_CIDR        — CIDR allowed in pg_hba.conf
#   LOG_GROUP       — CloudWatch log group for postgres logs

set -euo pipefail
exec > >(tee -a /var/log/timescaledb-bootstrap.log) 2>&1
echo "[bootstrap] starting at $(date -Is)"

PG_MAJOR='${PG_MAJOR}'
TS_PKG_VERSION='${TS_PKG_VERSION}'
DATA_DEVICE='${DATA_DEVICE}'
DATA_MOUNT='${DATA_MOUNT}'
DB_NAME='${DB_NAME}'
DB_USER='${DB_USER}'
DB_PORT='${DB_PORT}'
SECRET_ID='${SECRET_ID}'
AWS_REGION='${AWS_REGION}'
VPC_CIDR='${VPC_CIDR}'
LOG_GROUP='${LOG_GROUP}'

export DEBIAN_FRONTEND=noninteractive

# --- 1. system packages ----------------------------------------------------
apt-get update -y
apt-get install -y curl gnupg lsb-release ca-certificates unzip jq xfsprogs awscli amazon-cloudwatch-agent

# --- 2. PostgreSQL + TimescaleDB apt repos --------------------------------
install -d /usr/share/keyrings
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
  | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg
echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
  > /etc/apt/sources.list.d/pgdg.list

curl -fsSL https://packagecloud.io/timescale/timescaledb/gpgkey \
  | gpg --dearmor -o /usr/share/keyrings/timescaledb.gpg
echo "deb [signed-by=/usr/share/keyrings/timescaledb.gpg] https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -cs) main" \
  > /etc/apt/sources.list.d/timescaledb.list

apt-get update -y

TS_PACKAGE="timescaledb-2-postgresql-$${PG_MAJOR}"
if [ -n "$${TS_PKG_VERSION}" ]; then
  TS_PACKAGE="$${TS_PACKAGE}=$${TS_PKG_VERSION}"
fi
apt-get install -y "postgresql-$${PG_MAJOR}" "$${TS_PACKAGE}" "timescaledb-tools"

systemctl stop postgresql

# --- 3. prepare data volume -----------------------------------------------
# The EBS volume may surface as /dev/nvme1n1 (Nitro) or DATA_DEVICE. Resolve.
resolve_data_device() {
  if [ -b "$${DATA_DEVICE}" ]; then echo "$${DATA_DEVICE}"; return; fi
  # Nitro: look up by NVMe serial which equals the EBS volume id (minus dashes).
  for d in /dev/nvme*n1; do
    serial=$(nvme id-ctrl -o json "$${d}" 2>/dev/null | jq -r '.sn // empty' || true)
    if [ -n "$${serial}" ] && [ "/dev/$${serial}" = "$${DATA_DEVICE}" ]; then
      echo "$${d}"; return
    fi
  done
  echo "$${DATA_DEVICE}"
}
DEV=$(resolve_data_device)
echo "[bootstrap] data device resolved: $${DEV}"

if ! blkid "$${DEV}" >/dev/null 2>&1; then
  echo "[bootstrap] formatting $${DEV} as xfs"
  mkfs.xfs -L pgdata "$${DEV}"
fi
mkdir -p "$${DATA_MOUNT}"
UUID=$(blkid -s UUID -o value "$${DEV}")
if ! grep -q "$${UUID}" /etc/fstab; then
  echo "UUID=$${UUID} $${DATA_MOUNT} xfs defaults,nofail,noatime 0 2" >> /etc/fstab
fi
mount -a

# --- 4. initdb on the EBS volume (idempotent) -----------------------------
PGDATA="$${DATA_MOUNT}/$${PG_MAJOR}/main"
mkdir -p "$${PGDATA}"
chown -R postgres:postgres "$${DATA_MOUNT}"
chmod 700 "$${PGDATA}"

if [ ! -s "$${PGDATA}/PG_VERSION" ]; then
  echo "[bootstrap] initdb at $${PGDATA}"
  sudo -u postgres /usr/lib/postgresql/$${PG_MAJOR}/bin/initdb -D "$${PGDATA}" --auth-host=scram-sha-256 --auth-local=peer
fi

# Point the service at the EBS-backed data directory.
CONF_DIR="/etc/postgresql/$${PG_MAJOR}/main"
mkdir -p "$${CONF_DIR}"
# Ship a minimal config; the package config still expects to find a data dir.
cat > "$${CONF_DIR}/postgresql.conf" <<EOF
data_directory = '$${PGDATA}'
hba_file = '$${CONF_DIR}/pg_hba.conf'
ident_file = '$${CONF_DIR}/pg_ident.conf'
external_pid_file = '/var/run/postgresql/$${PG_MAJOR}-main.pid'
listen_addresses = '*'
port = $${DB_PORT}
max_connections = 200
shared_preload_libraries = 'timescaledb,pg_stat_statements'
log_destination = 'stderr'
logging_collector = on
log_directory = '/var/log/postgresql'
log_filename = 'postgresql-%Y-%m-%d.log'
log_min_duration_statement = 1000
log_line_prefix = '%t [%p]: db=%d,user=%u '
ssl = on
ssl_cert_file = '/etc/ssl/certs/ssl-cert-snakeoil.pem'
ssl_key_file  = '/etc/ssl/private/ssl-cert-snakeoil.key'
EOF
apt-get install -y ssl-cert
usermod -aG ssl-cert postgres

cat > "$${CONF_DIR}/pg_hba.conf" <<EOF
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             postgres                                peer
local   all             all                                     scram-sha-256
hostssl all             all             $${VPC_CIDR}            scram-sha-256
host    all             all             127.0.0.1/32            scram-sha-256
EOF
chown postgres:postgres "$${CONF_DIR}/postgresql.conf" "$${CONF_DIR}/pg_hba.conf"
chmod 640 "$${CONF_DIR}/postgresql.conf" "$${CONF_DIR}/pg_hba.conf"

# Apply Timescale-recommended memory/parallelism settings.
sudo -u postgres timescaledb-tune --quiet --yes --conf-path "$${CONF_DIR}/postgresql.conf" || true

mkdir -p /var/log/postgresql
chown postgres:postgres /var/log/postgresql

# --- 5. start postgres & set up role/db -----------------------------------
systemctl enable postgresql
systemctl restart postgresql

# Wait for postgres to be ready.
for i in $(seq 1 30); do
  if sudo -u postgres psql -p "$${DB_PORT}" -tAc 'SELECT 1' >/dev/null 2>&1; then break; fi
  sleep 2
done

DB_PASSWORD=$(aws secretsmanager get-secret-value \
  --region "$${AWS_REGION}" \
  --secret-id "$${SECRET_ID}" \
  --query SecretString --output text | jq -r '.password')

if [ -z "$${DB_PASSWORD}" ] || [ "$${DB_PASSWORD}" = "null" ]; then
  echo "[bootstrap] FATAL: could not read password from $${SECRET_ID}" >&2
  exit 1
fi

sudo -u postgres psql -p "$${DB_PORT}" -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$${DB_USER}') THEN
    CREATE ROLE $${DB_USER} LOGIN PASSWORD '$${DB_PASSWORD}' CREATEDB;
  ELSE
    ALTER ROLE $${DB_USER} WITH LOGIN PASSWORD '$${DB_PASSWORD}';
  END IF;
END
\$\$;
SELECT 'CREATE DATABASE $${DB_NAME} OWNER $${DB_USER}'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '$${DB_NAME}')\gexec
SQL

sudo -u postgres psql -p "$${DB_PORT}" -d "$${DB_NAME}" -v ON_ERROR_STOP=1 <<SQL
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
SQL

# --- 6. CloudWatch agent for postgres logs --------------------------------
cat > /opt/aws/amazon-cloudwatch-agent/etc/postgres-logs.json <<EOF
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/postgresql/postgresql-*.log",
            "log_group_name": "$${LOG_GROUP}",
            "log_stream_name": "{instance_id}/postgresql",
            "timezone": "UTC",
            "retention_in_days": 30
          },
          {
            "file_path": "/var/log/timescaledb-bootstrap.log",
            "log_group_name": "$${LOG_GROUP}",
            "log_stream_name": "{instance_id}/bootstrap",
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
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/postgres-logs.json

echo "[bootstrap] done at $(date -Is)"
