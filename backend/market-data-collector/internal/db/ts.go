// Package db owns the TimescaleDB connection pool for market-data-collector.
//
// Only one pool because this service writes exclusively to the time-series
// database (hypertables: market_data, quote_data). The OLTP RDS instance is
// owned by user-api and is not used here.
package db

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/algotrader/market-data-collector/internal/config"
)

// New opens a pgxpool against the configured TimescaleDB endpoint and waits
// for the first connection to succeed before returning. The caller owns the
// pool lifecycle — call pool.Close() on shutdown.
func New(ctx context.Context, cfg config.DatabaseConfig) (*pgxpool.Pool, error) {
	poolCfg, err := pgxpool.ParseConfig(cfg.DSN())
	if err != nil {
		return nil, fmt.Errorf("parse pgxpool config: %w", err)
	}

	poolCfg.MaxConns = cfg.MaxConns
	poolCfg.MinConns = cfg.MinConns
	poolCfg.HealthCheckPeriod = 30 * time.Second
	poolCfg.MaxConnLifetime = 30 * time.Minute
	poolCfg.MaxConnIdleTime = 5 * time.Minute

	pool, err := pgxpool.NewWithConfig(ctx, poolCfg)
	if err != nil {
		return nil, fmt.Errorf("create pgxpool: %w", err)
	}

	// Eager-acquire one connection so we fail fast on misconfiguration rather
	// than discovering it on the first query at request time.
	pingCtx, cancel := context.WithTimeout(ctx, time.Duration(cfg.ConnectTimeoutMs)*time.Millisecond)
	defer cancel()
	if err := pool.Ping(pingCtx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("ping timescaledb: %w", err)
	}

	return pool, nil
}

// Ping returns nil if the pool can reach the database within the timeout.
// Used by readiness probes; safe to call concurrently.
func Ping(ctx context.Context, pool *pgxpool.Pool, timeout time.Duration) error {
	if pool == nil {
		return fmt.Errorf("pool is nil")
	}
	pingCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	return pool.Ping(pingCtx)
}
