-- =============================================================================
-- Fraud Detection System - PostgreSQL Schema Initialization
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Transactions Table
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_ref VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    product_cd VARCHAR(10) NOT NULL,
    card1 VARCHAR(32),
    card2 VARCHAR(32),
    card3 VARCHAR(32),
    card4 VARCHAR(32),
    card5 VARCHAR(32),
    card6 VARCHAR(32),
    p_emaildomain VARCHAR(100),
    r_emaildomain VARCHAR(100),
    device_type VARCHAR(50),
    device_info VARCHAR(150),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Fraud Assessments (Scoring details from ML service)
CREATE TABLE IF NOT EXISTS fraud_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    fraud_probability NUMERIC(5, 4) NOT NULL,
    decision VARCHAR(20) NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    risk_factors JSONB,
    evaluated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. Human Review Cases (for FLAGGED transactions)
CREATE TABLE IF NOT EXISTS review_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    analyst_id VARCHAR(64),
    review_status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    analyst_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_ref ON transactions(transaction_ref);
CREATE INDEX IF NOT EXISTS idx_fraud_assessments_tx_id ON fraud_assessments(transaction_id);
CREATE INDEX IF NOT EXISTS idx_fraud_assessments_prob ON fraud_assessments(fraud_probability DESC);
CREATE INDEX IF NOT EXISTS idx_review_cases_status ON review_cases(review_status);
CREATE INDEX IF NOT EXISTS idx_review_cases_tx_id ON review_cases(transaction_id);
