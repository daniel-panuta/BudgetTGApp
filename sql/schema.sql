-- ============================================================================
-- BudgetApp Database Schema
-- Complete production schema with all necessary tables and constraints
-- ============================================================================

-- Drop existing tables if they exist (for fresh deployment)
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS audit_inserts CASCADE;
DROP TABLE IF EXISTS salary_days CASCADE;
DROP TABLE IF EXISTS shops CASCADE;
DROP TABLE IF EXISTS categories CASCADE;

-- ============================================================================
-- 1. CATEGORIES DICTIONARY
-- ============================================================================
-- Stores transaction categories (income/expense) used for financial analysis
-- Each shop has a default category for smart classification
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    type VARCHAR(10) NOT NULL CHECK (type IN ('income', 'expense')),
    CONSTRAINT categories_name_key UNIQUE (name)
);

-- ============================================================================
-- 2. SHOPS DICTIONARY
-- ============================================================================
-- Stores merchant/shop names with deduplication support
-- Links to default category for automatic transaction classification
-- Commercial name allows tracking aliases (e.g., "MAIB P2P" vs "MAIB Online")
CREATE TABLE shops (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    commercial_name VARCHAR(255),
    default_category_id INT REFERENCES categories(id) ON DELETE SET NULL,
    CONSTRAINT shops_name_key UNIQUE (name)
);

-- ============================================================================
-- 3. SALARY DAYS TABLE
-- ============================================================================
-- Defines payroll cycle boundaries for salary-based financial analysis
-- Allows monthly analysis grouped by payroll periods
CREATE TABLE salary_days (
    id SERIAL PRIMARY KEY,
    year INT NOT NULL,
    month INT NOT NULL,
    salary_date DATE NOT NULL,
    CONSTRAINT salary_days_year_month_key UNIQUE (year, month)
);

-- ============================================================================
-- 4. AUDIT INSERTS LOG
-- ============================================================================
-- Tracks file imports for complete audit trail and duplicate detection
-- Every imported statement creates a record for provenance tracking
-- Supports duplicate detection across different file imports
CREATE TABLE audit_inserts (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_extension VARCHAR(10) NOT NULL CHECK (file_extension IN ('pdf', 'html')),
    import_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 5. TRANSACTIONS HISTORY TABLE
-- ============================================================================
-- Core transactions table with full audit trail
-- Each row includes:
--   - date: Transaction date from bank statement
--   - shop_id: Link to shops table for deduplication
--   - amount: Transaction amount in MDL
--   - currency: Original transaction currency
--   - amount_original: Amount in original currency (before conversion)
--   - amount_mdl: Amount converted to MDL
--   - raw_text: Original line from PDF/HTML for audit and debugging
--   - audit_insert_id: Link to audit_inserts for import tracking
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    processing_date DATE,
    shop_id INT NOT NULL REFERENCES shops(id) ON DELETE RESTRICT,
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'MDL',
    amount_original NUMERIC(12, 2),
    amount_mdl NUMERIC(12, 2) NOT NULL,
    raw_text TEXT NOT NULL,
    audit_insert_id INT NOT NULL REFERENCES audit_inserts(id) ON DELETE RESTRICT
);

-- ============================================================================
-- INDEXES FOR QUERY OPTIMIZATION
-- ============================================================================

-- Speed up duplicate detection queries
CREATE INDEX idx_transactions_date_shop_amount ON transactions(date, shop_id, amount);
CREATE INDEX idx_transactions_processing_shop_amount ON transactions(processing_date, shop_id, amount);
CREATE INDEX idx_transactions_audit_insert ON transactions(audit_insert_id);
CREATE INDEX idx_transactions_shop ON transactions(shop_id);
CREATE INDEX idx_transactions_date ON transactions(date);

-- Speed up audit trail queries
CREATE INDEX idx_audit_inserts_filename ON audit_inserts(filename);
CREATE INDEX idx_audit_inserts_import_date ON audit_inserts(import_date);

-- Speed up shop lookups
CREATE INDEX idx_shops_name ON shops(name);
CREATE INDEX idx_shops_commercial_name ON shops(commercial_name) WHERE commercial_name IS NOT NULL;

-- ============================================================================
-- DEFAULT DATA
-- ============================================================================

-- Insert default categories
--INSERT INTO categories (name, type) VALUES ('Other', 'expense') ON CONFLICT DO NOTHING;
--INSERT INTO categories (name, type) VALUES ('Income', 'income') ON CONFLICT DO NOTHING;
--INSERT INTO categories (name, type) VALUES ('Groceries', 'expense') ON CONFLICT DO NOTHING;
--INSERT INTO categories (name, type) VALUES ('Transport', 'expense') ON CONFLICT DO NOTHING;
--INSERT INTO categories (name, type) VALUES ('Utilities', 'expense') ON CONFLICT DO NOTHING;
--INSERT INTO categories (name, type) VALUES ('Entertainment', 'expense') ON CONFLICT DO NOTHING;
--INSERT INTO categories (name, type) VALUES ('Healthcare', 'expense') ON CONFLICT DO NOTHING;

-- ============================================================================
-- SCHEMA VERIFICATION
-- ============================================================================
\dt
