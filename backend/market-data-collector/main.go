package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"go.uber.org/zap"
)

var logger *zap.Logger

func main() {
	// Initialize logger
	var err error
	if os.Getenv("ENVIRONMENT") == "production" {
		logger, err = zap.NewProduction()
	} else {
		logger, err = zap.NewDevelopment()
	}
	if err != nil {
		log.Fatalf("Failed to initialize logger: %v", err)
	}
	defer logger.Sync()

	logger.Info("Starting Market Data Collector",
		zap.String("environment", getEnv("ENVIRONMENT", "development")),
		zap.String("version", "0.1.0"),
	)

	// TODO: Initialize database connection
	// TODO: Initialize Redis connection
	// TODO: Initialize broker API clients (KIS, Xing, IB, Alpaca)

	// Health check server
	go startHealthCheckServer()

	// TODO: Start WebSocket connections to brokers
	// TODO: Start data processing pipeline

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("Shutting down Market Data Collector...")

	// Graceful shutdown
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	// TODO: Close database connections
	// TODO: Close Redis connections
	// TODO: Close WebSocket connections

	select {
	case <-ctx.Done():
		logger.Info("Shutdown complete")
	}
}

// startHealthCheckServer starts HTTP server for health checks
func startHealthCheckServer() {
	http.HandleFunc("/health", healthCheckHandler)
	http.HandleFunc("/ready", readinessCheckHandler)
	http.HandleFunc("/live", livenessCheckHandler)

	port := getEnv("HEALTH_CHECK_PORT", "8080")
	logger.Info("Starting health check server", zap.String("port", port))

	if err := http.ListenAndServe(":"+port, nil); err != nil {
		logger.Fatal("Failed to start health check server", zap.Error(err))
	}
}

// Health check handler
func healthCheckHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, `{"status":"healthy","service":"market-data-collector","timestamp":"%s"}`, time.Now().Format(time.RFC3339))
}

// Readiness check handler
func readinessCheckHandler(w http.ResponseWriter, r *http.Request) {
	// TODO: Check database and Redis connectivity
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, `{"status":"ready"}`)
}

// Liveness check handler
func livenessCheckHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, `{"status":"alive"}`)
}

// getEnv gets environment variable with default value
func getEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}
