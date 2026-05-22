package config

import (
	"strings"
	"testing"
)

func TestFromEnv_DefaultsApply(t *testing.T) {
	t.Setenv("ENVIRONMENT", "")
	t.Setenv("DATABASE_HOST", "")
	t.Setenv("DATABASE_PORT", "")
	t.Setenv("DATABASE_NAME", "")
	t.Setenv("DATABASE_USERNAME", "")
	t.Setenv("DATABASE_PASSWORD", "anything")
	t.Setenv("HEALTH_CHECK_PORT", "")

	cfg, err := FromEnv()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if cfg.Environment != "development" {
		t.Errorf("Environment default=development, got %q", cfg.Environment)
	}
	if cfg.HealthCheckPort != "8080" {
		t.Errorf("HealthCheckPort default=8080, got %q", cfg.HealthCheckPort)
	}
	if cfg.Database.Host != "localhost" {
		t.Errorf("DB Host default=localhost, got %q", cfg.Database.Host)
	}
	if cfg.Database.Port != 5432 {
		t.Errorf("DB Port default=5432, got %d", cfg.Database.Port)
	}
	if cfg.Database.MaxConns != 10 {
		t.Errorf("DB MaxConns default=10, got %d", cfg.Database.MaxConns)
	}
}

func TestFromEnv_ProductionRequiresPassword(t *testing.T) {
	t.Setenv("ENVIRONMENT", "production")
	t.Setenv("DATABASE_PASSWORD", "")

	_, err := FromEnv()
	if err == nil {
		t.Fatal("expected error when DATABASE_PASSWORD is empty in production")
	}
	if !strings.Contains(err.Error(), "DATABASE_PASSWORD") {
		t.Errorf("error should mention DATABASE_PASSWORD, got: %v", err)
	}
}

func TestDSN_FormatIsKeyValue(t *testing.T) {
	cfg := DatabaseConfig{
		Host:             "example",
		Port:             5432,
		Name:             "tsdb",
		Username:         "user",
		Password:         "pw with spaces",
		ConnectTimeoutMs: 3000,
	}
	dsn := cfg.DSN()
	for _, want := range []string{
		"host=example",
		"port=5432",
		"dbname=tsdb",
		"user=user",
		"application_name=market-data-collector",
		"connect_timeout=3",
	} {
		if !strings.Contains(dsn, want) {
			t.Errorf("DSN missing %q: %s", want, dsn)
		}
	}
}
