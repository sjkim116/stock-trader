-- AlgoTrader Pro - Time-series schema (EC2 TimescaleDB).
-- OLTP tables live in schema_oltp.sql, which runs on the RDS PostgreSQL
-- instance. See infrastructure/terraform/modules/timescaledb_ec2 for the
-- TS host. The two databases are independent — there are no FKs across
-- them; the symbol identifier is a shared string by convention.
-- PostgreSQL 15+ with TimescaleDB extension
-- Last updated: 2026-05-22

CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Shared enums (idempotent so this file can coexist with schema_oltp.sql
-- when loaded into a single local DB for docker-compose dev).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'market_type') THEN
        CREATE TYPE market_type AS ENUM ('kr', 'us');
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'data_interval') THEN
        CREATE TYPE data_interval AS ENUM ('tick', '1s', '1m', '5m', '15m', '1h', '1d');
    END IF;
END$$;

-- ================================================================
-- Market Data (OHLCV) - TimescaleDB Hypertable
-- ================================================================

CREATE TABLE IF NOT EXISTS market_data (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    market market_type NOT NULL,
    interval data_interval NOT NULL,

    open DECIMAL(15, 4),
    high DECIMAL(15, 4),
    low DECIMAL(15, 4),
    close DECIMAL(15, 4),
    volume BIGINT,

    PRIMARY KEY (time, symbol, interval)
);

-- Convert to TimescaleDB hypertable (time-series optimization).
-- if_not_exists keeps re-applies idempotent.
SELECT create_hypertable('market_data', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_market_data_symbol_time ON market_data (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_market_data_interval ON market_data (interval);

-- Compression policy (compress data older than 7 days)
ALTER TABLE market_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol,interval'
);

SELECT add_compression_policy('market_data', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('market_data', INTERVAL '2 years', if_not_exists => TRUE);

-- ================================================================
-- Quote Data (호가 데이터) - TimescaleDB Hypertable
-- ================================================================

CREATE TABLE IF NOT EXISTS quote_data (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    market market_type NOT NULL,

    bid_price DECIMAL(15, 4),
    bid_size INTEGER,
    ask_price DECIMAL(15, 4),
    ask_size INTEGER,

    bids JSONB,  -- [{price, size}, ...]
    asks JSONB,

    PRIMARY KEY (time, symbol)
);

SELECT create_hypertable('quote_data', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_quote_data_symbol_time ON quote_data (symbol, time DESC);

ALTER TABLE quote_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol'
);
SELECT add_compression_policy('quote_data', INTERVAL '1 day', if_not_exists => TRUE);
SELECT add_retention_policy('quote_data', INTERVAL '30 days', if_not_exists => TRUE);

-- ================================================================
-- End of Time-Series Schema
-- ================================================================
