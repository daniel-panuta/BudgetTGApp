-- Migration script to add commercial_name to shops and salary_days table
ALTER TABLE shops
    ADD COLUMN commercial_name VARCHAR(100);

CREATE TABLE IF NOT EXISTS salary_days (
    id SERIAL PRIMARY KEY,
    year INT NOT NULL,
    month INT NOT NULL,
    salary_date DATE NOT NULL,
    UNIQUE(year, month)
);

-- Example salary-day entries
INSERT INTO salary_days (year, month, salary_date) VALUES
  (2026, 5, '2026-05-14')
ON CONFLICT (year, month) DO NOTHING;

INSERT INTO salary_days (year, month, salary_date) VALUES
  (2026, 6, '2026-06-12')
ON CONFLICT (year, month) DO NOTHING;
