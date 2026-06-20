-- 1. Categories Dictionary
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    type VARCHAR(10) CHECK (type IN ('income', 'expense')) NOT NULL
);

-- 2. Shops Dictionary (Linked to a default category for smart parsing)
CREATE TABLE shops (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    default_category_id INT REFERENCES categories(id) ON DELETE SET NULL
);

-- 3. Transactions History Table
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    shop_id INT REFERENCES shops(id) ON DELETE RESTRICT,
    category_id INT REFERENCES categories(id) ON DELETE RESTRICT,
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'MDL',
    amount_original NUMERIC(12, 2),
    amount_mdl NUMERIC(12, 2) NOT NULL,
    raw_text TEXT -- Stores original PDF/HTML line for debugging
);
