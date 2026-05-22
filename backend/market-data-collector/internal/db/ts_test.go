package db

import (
	"context"
	"os"
	"strconv"
	"testing"
	"time"

	"github.com/algotrader/market-data-collector/internal/config"
)

// loadIntegrationConfig pulls DB connection details out of the env. Returns
// nil when DATABASE_HOST is unset so individual tests can skip cleanly when
// no postgres is reachable (e.g. running on a dev box without docker up).
func loadIntegrationConfig(t *testing.T) *config.DatabaseConfig {
	t.Helper()
	host := os.Getenv("DATABASE_HOST")
	if host == "" {
		t.Skip("DATABASE_HOST not set — skipping integration test")
	}
	port := 5432
	if p := os.Getenv("DATABASE_PORT"); p != "" {
		if v, err := strconv.Atoi(p); err == nil {
			port = v
		}
	}
	return &config.DatabaseConfig{
		Host:             host,
		Port:             port,
		Name:             envOr("DATABASE_NAME", "algotrader"),
		Username:         envOr("DATABASE_USERNAME", "algotrader"),
		Password:         envOr("DATABASE_PASSWORD", ""),
		MaxConns:         5,
		MinConns:         1,
		ConnectTimeoutMs: 5000,
	}
}

func envOr(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func TestNew_OpensPoolAndPings(t *testing.T) {
	cfg := loadIntegrationConfig(t)
	pool, err := New(context.Background(), *cfg)
	if err != nil {
		t.Fatalf("New: %v", err)
	}
	defer pool.Close()

	var got int
	if err := pool.QueryRow(context.Background(), "SELECT 42").Scan(&got); err != nil {
		t.Fatalf("simple query failed: %v", err)
	}
	if got != 42 {
		t.Errorf("SELECT 42 returned %d", got)
	}
}

func TestPing_ReturnsErrorForNilPool(t *testing.T) {
	if err := Ping(context.Background(), nil, time.Second); err == nil {
		t.Fatal("expected error for nil pool")
	}
}

func TestNew_FailsFastOnBadCredentials(t *testing.T) {
	// Only meaningful when a host is reachable; otherwise the underlying
	// error is "no route to host" which exercises the same fail-fast path.
	host := os.Getenv("DATABASE_HOST")
	if host == "" {
		t.Skip("DATABASE_HOST not set")
	}
	bad := config.DatabaseConfig{
		Host:             host,
		Port:             5432,
		Name:             envOr("DATABASE_NAME", "algotrader"),
		Username:         envOr("DATABASE_USERNAME", "algotrader"),
		Password:         "definitely-not-the-password",
		MaxConns:         2,
		MinConns:         1,
		ConnectTimeoutMs: 2000,
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if _, err := New(ctx, bad); err == nil {
		t.Fatal("expected New to fail with bad password")
	}
}
