package main

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"sync/atomic"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"go.uber.org/zap"

	"github.com/algotrader/market-data-collector/internal/config"
	"github.com/algotrader/market-data-collector/internal/db"
)

const readinessPingTimeout = 2 * time.Second

func main() {
	logger := mustLogger()
	defer logger.Sync()

	cfg, err := config.FromEnv()
	if err != nil {
		logger.Fatal("Failed to load config", zap.Error(err))
	}

	logger.Info("Starting Market Data Collector",
		zap.String("environment", cfg.Environment),
		zap.String("version", "0.1.0"),
	)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	pool, err := db.New(ctx, cfg.Database)
	if err != nil {
		logger.Fatal("Failed to open TimescaleDB pool", zap.Error(err))
	}
	defer pool.Close()
	logger.Info("Connected to TimescaleDB",
		zap.String("host", cfg.Database.Host),
		zap.String("dbname", cfg.Database.Name),
	)

	// TODO: Initialize Redis connection
	// TODO: Initialize broker API clients (KIS, Xing, IB, Alpaca)
	// TODO: Start WebSocket connections to brokers
	// TODO: Start data processing pipeline

	srv := newHealthServer(logger, pool, cfg.HealthCheckPort)
	go func() {
		logger.Info("Starting health check server", zap.String("port", cfg.HealthCheckPort))
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Fatal("Health server crashed", zap.Error(err))
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("Shutting down Market Data Collector...")

	shutdownCtx, cancelShutdown := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancelShutdown()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		logger.Warn("Health server shutdown error", zap.Error(err))
	}
	// TODO: Close Redis connections
	// TODO: Close WebSocket connections

	logger.Info("Shutdown complete")
}

func mustLogger() *zap.Logger {
	var (
		logger *zap.Logger
		err    error
	)
	if os.Getenv("ENVIRONMENT") == "production" {
		logger, err = zap.NewProduction()
	} else {
		logger, err = zap.NewDevelopment()
	}
	if err != nil {
		// Bootstrapping failure — stderr is the only thing we can rely on.
		panic(err)
	}
	return logger
}

// healthServer wraps the readiness/liveness handlers with a reference to the
// pgxpool so they can ping the database without using a package-global.
type healthServer struct {
	logger *zap.Logger
	pool   *pgxpool.Pool

	// dbHealthy mirrors the last ping result so liveness can stay cheap.
	dbHealthy atomic.Bool
}

func newHealthServer(logger *zap.Logger, pool *pgxpool.Pool, port string) *http.Server {
	h := &healthServer{logger: logger, pool: pool}
	h.dbHealthy.Store(true) // db.New already pinged once successfully

	mux := http.NewServeMux()
	mux.HandleFunc("/health", h.health)
	mux.HandleFunc("/ready", h.ready)
	mux.HandleFunc("/live", h.live)

	return &http.Server{
		Addr:              ":" + port,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
	}
}

type healthResponse struct {
	Status    string            `json:"status"`
	Service   string            `json:"service"`
	Timestamp string            `json:"timestamp"`
	Checks    map[string]string `json:"checks,omitempty"`
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}

func (h *healthServer) health(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, healthResponse{
		Status:    "healthy",
		Service:   "market-data-collector",
		Timestamp: time.Now().UTC().Format(time.RFC3339),
	})
}

func (h *healthServer) ready(w http.ResponseWriter, r *http.Request) {
	err := db.Ping(r.Context(), h.pool, readinessPingTimeout)
	dbUp := err == nil
	h.dbHealthy.Store(dbUp)

	status := "ready"
	httpStatus := http.StatusOK
	if !dbUp {
		status = "not_ready"
		httpStatus = http.StatusServiceUnavailable
		h.logger.Warn("Readiness ping failed", zap.Error(err))
	}

	writeJSON(w, httpStatus, healthResponse{
		Status:    status,
		Service:   "market-data-collector",
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Checks: map[string]string{
			"database": statusString(dbUp),
		},
	})
}

func (h *healthServer) live(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, healthResponse{
		Status:    "alive",
		Service:   "market-data-collector",
		Timestamp: time.Now().UTC().Format(time.RFC3339),
	})
}

func statusString(ok bool) string {
	if ok {
		return "up"
	}
	return "down"
}
