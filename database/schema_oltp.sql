-- AlgoTrader Pro - OLTP schema (RDS PostgreSQL).
-- Time-series tables (market_data, quote_data) live in schema_timeseries.sql,
-- which runs on the EC2 TimescaleDB instance. See infrastructure/terraform/
-- modules/timescaledb_ec2 for the rationale and modules/rds for this target.
-- PostgreSQL 15+
-- Last updated: 2026-05-22

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ================================================================
-- 1. Users & Authentication
-- ================================================================

CREATE TYPE user_plan AS ENUM ('basic', 'pro', 'premium');
CREATE TYPE user_status AS ENUM ('active', 'inactive', 'suspended');

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    plan user_plan NOT NULL DEFAULT 'basic',
    status user_status NOT NULL DEFAULT 'active',

    -- Preferences
    timezone VARCHAR(50) DEFAULT 'UTC',
    language VARCHAR(10) DEFAULT 'ko',

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_created_at ON users(created_at DESC);

-- ================================================================
-- 2. Broker Accounts (증권사 계좌)
-- ================================================================

CREATE TYPE broker_type AS ENUM ('kis', 'xing', 'ib', 'alpaca');
-- market_type is also used by time-series schema; idempotent create lets both
-- files load into a single DB locally without conflict.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'market_type') THEN
        CREATE TYPE market_type AS ENUM ('kr', 'us');
    END IF;
END$$;
CREATE TYPE account_status AS ENUM ('connected', 'disconnected', 'error');

CREATE TABLE accounts (
    account_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    broker broker_type NOT NULL,
    market market_type NOT NULL,
    account_number VARCHAR(100) NOT NULL,
    account_name VARCHAR(100),

    -- API Credentials (stored encrypted in AWS Secrets Manager)
    api_key_secret_arn VARCHAR(255) NOT NULL,  -- ARN of secret in Secrets Manager

    status account_status NOT NULL DEFAULT 'disconnected',
    last_sync_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_user_account UNIQUE (user_id, broker, account_number)
);

CREATE INDEX idx_accounts_user_id ON accounts(user_id);
CREATE INDEX idx_accounts_status ON accounts(status);

-- ================================================================
-- 3. Strategies (거래 전략)
-- ================================================================

CREATE TYPE strategy_category AS ENUM ('trend_following', 'mean_reversion', 'momentum', 'breakout', 'other');

CREATE TABLE strategies (
    strategy_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category strategy_category NOT NULL,

    -- Markets supported
    supported_markets market_type[] NOT NULL,

    -- Strategy code
    code_module VARCHAR(255) NOT NULL,  -- Python module path (e.g., strategies.ma_cross)

    -- Parameters schema (JSON Schema)
    parameters_schema JSONB NOT NULL,

    -- Default parameters
    default_parameters JSONB NOT NULL,

    -- Backtesting results (aggregated)
    backtesting_results JSONB,

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_strategies_category ON strategies(category);
CREATE INDEX idx_strategies_is_active ON strategies(is_active);

-- ================================================================
-- 4. User Strategies (사용자가 활성화한 전략)
-- ================================================================

CREATE TYPE user_strategy_status AS ENUM ('active', 'paused', 'stopped');

CREATE TABLE user_strategies (
    user_strategy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    strategy_id VARCHAR(50) NOT NULL REFERENCES strategies(strategy_id),
    account_id UUID NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,

    -- Custom parameters for this user
    parameters JSONB NOT NULL,

    -- Risk management
    max_position_size DECIMAL(15, 2),  -- Maximum per position
    max_positions INTEGER DEFAULT 5,
    stop_loss_percent DECIMAL(5, 2) DEFAULT 2.0,
    take_profit_percent DECIMAL(5, 2) DEFAULT 3.0,

    -- Status
    status user_strategy_status NOT NULL DEFAULT 'paused',

    -- Statistics (updated periodically)
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_pnl DECIMAL(15, 2) DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    activated_at TIMESTAMP WITH TIME ZONE,
    deactivated_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT unique_user_account_strategy UNIQUE (user_id, account_id, strategy_id)
);

CREATE INDEX idx_user_strategies_user_id ON user_strategies(user_id);
CREATE INDEX idx_user_strategies_account_id ON user_strategies(account_id);
CREATE INDEX idx_user_strategies_status ON user_strategies(status);

-- ================================================================
-- 5. Orders (주문)
-- ================================================================

CREATE TYPE order_side AS ENUM ('buy', 'sell');
CREATE TYPE order_type AS ENUM ('market', 'limit', 'stop', 'stop_limit');
CREATE TYPE order_status AS ENUM ('pending', 'submitted', 'filled', 'partially_filled', 'cancelled', 'rejected', 'expired');

CREATE TABLE orders (
    order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID NOT NULL REFERENCES accounts(account_id),
    user_strategy_id UUID REFERENCES user_strategies(user_strategy_id),  -- NULL for manual orders

    -- Order details
    symbol VARCHAR(20) NOT NULL,
    side order_side NOT NULL,
    order_type order_type NOT NULL,
    quantity DECIMAL(15, 4) NOT NULL,
    price DECIMAL(15, 4),  -- NULL for market orders
    stop_price DECIMAL(15, 4),  -- For stop orders

    -- Execution
    status order_status NOT NULL DEFAULT 'pending',
    filled_quantity DECIMAL(15, 4) DEFAULT 0,
    filled_price DECIMAL(15, 4),  -- Average fill price
    commission DECIMAL(10, 4) DEFAULT 0,

    -- Broker order ID
    broker_order_id VARCHAR(100),

    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    submitted_at TIMESTAMP WITH TIME ZONE,
    filled_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_orders_account_id ON orders(account_id);
CREATE INDEX idx_orders_user_strategy_id ON orders(user_strategy_id);
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);

-- ================================================================
-- 6. Positions (포지션)
-- ================================================================

CREATE TYPE position_status AS ENUM ('open', 'closed');

CREATE TABLE positions (
    position_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID NOT NULL REFERENCES accounts(account_id),
    user_strategy_id UUID REFERENCES user_strategies(user_strategy_id),

    -- Position details
    symbol VARCHAR(20) NOT NULL,
    quantity DECIMAL(15, 4) NOT NULL,
    avg_entry_price DECIMAL(15, 4) NOT NULL,

    -- Risk management
    stop_loss_price DECIMAL(15, 4),
    take_profit_price DECIMAL(15, 4),

    -- PnL (updated periodically)
    current_price DECIMAL(15, 4),
    unrealized_pnl DECIMAL(15, 2),
    unrealized_pnl_percent DECIMAL(8, 4),

    realized_pnl DECIMAL(15, 2) DEFAULT 0,  -- When closed

    -- Status
    status position_status NOT NULL DEFAULT 'open',

    -- Entry/Exit orders
    entry_order_id UUID REFERENCES orders(order_id),
    exit_order_id UUID REFERENCES orders(order_id),

    -- Timestamps
    opened_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_positions_account_id ON positions(account_id);
CREATE INDEX idx_positions_user_strategy_id ON positions(user_strategy_id);
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_positions_opened_at ON positions(opened_at DESC);

-- ================================================================
-- 7. Trades (거래 이력 - 체결된 거래)
-- ================================================================

CREATE TABLE trades (
    trade_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    position_id UUID REFERENCES positions(position_id),
    order_id UUID REFERENCES orders(order_id),
    account_id UUID NOT NULL REFERENCES accounts(account_id),

    symbol VARCHAR(20) NOT NULL,
    side order_side NOT NULL,
    quantity DECIMAL(15, 4) NOT NULL,
    price DECIMAL(15, 4) NOT NULL,
    commission DECIMAL(10, 4) DEFAULT 0,

    -- PnL (for closing trades)
    pnl DECIMAL(15, 2),
    pnl_percent DECIMAL(8, 4),

    executed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_trades_account_id ON trades(account_id);
CREATE INDEX idx_trades_position_id ON trades(position_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_executed_at ON trades(executed_at DESC);

-- ================================================================
-- 8. Backtesting Results
-- ================================================================

CREATE TYPE backtest_status AS ENUM ('pending', 'running', 'completed', 'failed');

CREATE TABLE backtest_results (
    backtest_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    strategy_id VARCHAR(50) NOT NULL REFERENCES strategies(strategy_id),

    -- Backtest parameters
    parameters JSONB NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital DECIMAL(15, 2) NOT NULL,
    symbols VARCHAR(20)[] NOT NULL,

    -- Results
    status backtest_status NOT NULL DEFAULT 'pending',

    -- Performance metrics
    total_return DECIMAL(10, 4),
    cagr DECIMAL(10, 4),
    sharpe_ratio DECIMAL(8, 4),
    sortino_ratio DECIMAL(8, 4),
    max_drawdown DECIMAL(10, 4),
    win_rate DECIMAL(8, 4),
    profit_factor DECIMAL(8, 4),
    total_trades INTEGER,

    -- Detailed results (stored in S3)
    results_s3_key VARCHAR(255),

    -- Error
    error_message TEXT,

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_backtest_results_user_id ON backtest_results(user_id);
CREATE INDEX idx_backtest_results_strategy_id ON backtest_results(strategy_id);
CREATE INDEX idx_backtest_results_status ON backtest_results(status);
CREATE INDEX idx_backtest_results_created_at ON backtest_results(created_at DESC);

-- ================================================================
-- 9. Notifications (알림)
-- ================================================================

CREATE TYPE notification_type AS ENUM ('order_filled', 'stop_loss_triggered', 'take_profit_triggered',
                                        'daily_loss_limit', 'system_error', 'strategy_activated', 'other');
CREATE TYPE notification_status AS ENUM ('unread', 'read');

CREATE TABLE notifications (
    notification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    type notification_type NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,

    -- Related entities
    related_order_id UUID REFERENCES orders(order_id),
    related_position_id UUID REFERENCES positions(position_id),

    status notification_status NOT NULL DEFAULT 'unread',

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    read_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);

-- ================================================================
-- 10. Audit Logs (감사 로그)
-- ================================================================

CREATE TYPE audit_action AS ENUM ('create', 'update', 'delete', 'login', 'logout', 'order_placed', 'order_cancelled');

CREATE TABLE audit_logs (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id),

    action audit_action NOT NULL,
    entity_type VARCHAR(50),  -- e.g., 'order', 'position', 'user_strategy'
    entity_id UUID,

    details JSONB,
    ip_address INET,
    user_agent TEXT,

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- ================================================================
-- 11. Kill Switch (긴급 정지 플래그)
-- ================================================================
-- Per-user emergency stop. When enabled=TRUE, SafetyGuard refuses every
-- order regardless of strategy or limits. Set by the user manually or
-- triggered automatically (e.g. daily loss limit reached).

CREATE TABLE kill_switch (
    user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    reason TEXT,
    triggered_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_kill_switch_enabled ON kill_switch(enabled) WHERE enabled = TRUE;

-- ================================================================
-- 12. Paper Trading State (모의투자 상태 영속화)
-- ================================================================
-- Persists the in-memory PaperBroker state so an app restart doesn't
-- wipe positions/cash/PnL. Kept separate from the orders/positions
-- tables — those describe real-broker account state and follow a
-- different lifecycle. Paper state is per-user, single account per
-- user.

CREATE TABLE paper_account (
    user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    cash DECIMAL(20, 4) NOT NULL,
    realized_pnl_today DECIMAL(20, 4) NOT NULL DEFAULT 0,
    -- Today is reset by the strategy runner at session start (00:00 KST
    -- typically). Tracking the timestamp lets a restart figure out
    -- whether to zero PnL or carry it.
    pnl_reset_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE paper_position (
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    avg_entry_price DECIMAL(20, 4) NOT NULL,
    realized_pnl DECIMAL(20, 4) NOT NULL DEFAULT 0,
    opened_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, symbol)
);

CREATE INDEX idx_paper_position_user ON paper_position(user_id);

CREATE TABLE paper_fill (
    fill_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    -- order_id is the in-process Order UUID, NOT a FK. The orders table
    -- belongs to real-broker accounts; paper orders aren't persisted there.
    order_id UUID NOT NULL,
    broker_order_id VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side order_side NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 4) NOT NULL,
    commission DECIMAL(20, 4) NOT NULL DEFAULT 0,
    executed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_paper_fill_user_executed ON paper_fill(user_id, executed_at DESC);
CREATE INDEX idx_paper_fill_symbol ON paper_fill(symbol);

-- ================================================================
-- Triggers for updated_at
-- ================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_accounts_updated_at BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_strategies_updated_at BEFORE UPDATE ON strategies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_strategies_updated_at BEFORE UPDATE ON user_strategies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_positions_updated_at BEFORE UPDATE ON positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_kill_switch_updated_at BEFORE UPDATE ON kill_switch
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_paper_account_updated_at BEFORE UPDATE ON paper_account
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_paper_position_updated_at BEFORE UPDATE ON paper_position
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ================================================================
-- Sample Data (for development)
-- ================================================================

-- Insert sample strategies
INSERT INTO strategies (strategy_id, name, description, category, supported_markets, code_module, parameters_schema, default_parameters, is_active) VALUES
('strat_ma_cross', 'Moving Average Crossover', '단기/장기 이동평균선 교차 전략', 'trend_following', ARRAY['kr', 'us']::market_type[], 'strategies.ma_cross',
 '{"type": "object", "properties": {"short_period": {"type": "integer", "minimum": 3, "maximum": 50}, "long_period": {"type": "integer", "minimum": 10, "maximum": 200}}}',
 '{"short_period": 5, "long_period": 20, "investment_amount": 1000000, "stop_loss_percent": 2.0, "take_profit_percent": 3.0}', TRUE),

('strat_rsi_reversal', 'RSI Mean Reversion', 'RSI 과매도/과매수 구간 역추세 전략', 'mean_reversion', ARRAY['kr', 'us']::market_type[], 'strategies.rsi_reversal',
 '{"type": "object", "properties": {"rsi_period": {"type": "integer", "minimum": 5, "maximum": 30}, "oversold": {"type": "integer", "minimum": 10, "maximum": 40}, "overbought": {"type": "integer", "minimum": 60, "maximum": 90}}}',
 '{"rsi_period": 14, "oversold": 30, "overbought": 70, "investment_amount": 1000000, "stop_loss_percent": 2.0, "take_profit_percent": 3.0}', TRUE),

('strat_bb_breakout', 'Bollinger Bands Breakout', '볼린저 밴드 돌파 전략', 'breakout', ARRAY['kr', 'us']::market_type[], 'strategies.bb_breakout',
 '{"type": "object", "properties": {"bb_period": {"type": "integer", "minimum": 10, "maximum": 50}, "bb_std": {"type": "number", "minimum": 1.0, "maximum": 3.0}}}',
 '{"bb_period": 20, "bb_std": 2.0, "investment_amount": 1000000, "stop_loss_percent": 2.0, "take_profit_percent": 3.0}', TRUE);

-- ================================================================
-- Views for common queries
-- ================================================================

-- Active positions with current PnL
CREATE VIEW v_active_positions AS
SELECT
    p.position_id,
    p.account_id,
    a.user_id,
    p.symbol,
    p.quantity,
    p.avg_entry_price,
    p.current_price,
    p.unrealized_pnl,
    p.unrealized_pnl_percent,
    p.stop_loss_price,
    p.take_profit_price,
    us.strategy_id,
    s.name AS strategy_name,
    p.opened_at
FROM positions p
JOIN accounts a ON p.account_id = a.account_id
LEFT JOIN user_strategies us ON p.user_strategy_id = us.user_strategy_id
LEFT JOIN strategies s ON us.strategy_id = s.strategy_id
WHERE p.status = 'open';

-- Daily PnL summary
CREATE VIEW v_daily_pnl AS
SELECT
    a.user_id,
    DATE(t.executed_at) AS trade_date,
    COUNT(*) AS total_trades,
    SUM(CASE WHEN t.pnl > 0 THEN 1 ELSE 0 END) AS winning_trades,
    SUM(CASE WHEN t.pnl < 0 THEN 1 ELSE 0 END) AS losing_trades,
    SUM(t.pnl) AS total_pnl,
    AVG(t.pnl) AS avg_pnl
FROM trades t
JOIN accounts a ON t.account_id = a.account_id
WHERE t.pnl IS NOT NULL
GROUP BY a.user_id, DATE(t.executed_at);

-- ================================================================
-- End of OLTP Schema
-- ================================================================
