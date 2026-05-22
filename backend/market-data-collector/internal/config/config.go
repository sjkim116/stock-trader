// Package config loads market-data-collector configuration from the environment.
//
// The service writes time-series data to a TimescaleDB instance — in the cloud
// that's the EC2 host provisioned by infrastructure/terraform/modules/timescaledb_ec2,
// and locally it's the docker-compose postgres container. The env var names match
// the user-api convention so the same Terraform ECS plumbing applies when this
// service is wired in.
package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
)

// Config is the runtime configuration loaded from environment variables.
type Config struct {
	Environment string

	HealthCheckPort string

	Database DatabaseConfig
}

// DatabaseConfig describes the single PostgreSQL/TimescaleDB endpoint this
// service writes to. The field names mirror the env var components, not a DSN.
type DatabaseConfig struct {
	Host             string
	Port             int
	Name             string
	Username         string
	Password         string
	MaxConns         int32
	MinConns         int32
	ConnectTimeoutMs int
}

// FromEnv loads config from environment variables, applying sane defaults.
// Returns an error only when a required value is missing AND no default makes
// sense (e.g. an empty Database.Password in production).
func FromEnv() (*Config, error) {
	cfg := &Config{
		Environment:     getEnv("ENVIRONMENT", "development"),
		HealthCheckPort: getEnv("HEALTH_CHECK_PORT", "8080"),
		Database: DatabaseConfig{
			Host:             getEnv("DATABASE_HOST", "localhost"),
			Port:             getEnvInt("DATABASE_PORT", 5432),
			Name:             getEnv("DATABASE_NAME", "algotrader"),
			Username:         getEnv("DATABASE_USERNAME", "algotrader"),
			Password:         getEnv("DATABASE_PASSWORD", ""),
			MaxConns:         int32(getEnvInt("DATABASE_MAX_CONNS", 10)),
			MinConns:         int32(getEnvInt("DATABASE_MIN_CONNS", 2)),
			ConnectTimeoutMs: getEnvInt("DATABASE_CONNECT_TIMEOUT_MS", 5000),
		},
	}

	if cfg.Database.Password == "" && strings.EqualFold(cfg.Environment, "production") {
		return nil, fmt.Errorf("DATABASE_PASSWORD must be set in production")
	}

	return cfg, nil
}

// DSN renders a libpq connection string. pgx/v5 understands the key=value form
// and ignores it as a URL — using key=value keeps special chars in the password
// from breaking URL parsing.
func (d DatabaseConfig) DSN() string {
	return fmt.Sprintf(
		"host=%s port=%d dbname=%s user=%s password=%s sslmode=prefer connect_timeout=%d application_name=market-data-collector",
		d.Host, d.Port, d.Name, d.Username, d.Password, d.ConnectTimeoutMs/1000,
	)
}

func getEnv(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func getEnvInt(key string, def int) int {
	v := os.Getenv(key)
	if v == "" {
		return def
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		return def
	}
	return n
}
