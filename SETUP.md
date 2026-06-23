# BudgetApp Bot - Setup Guide

## Prerequisites

Make sure you have:
- PostgreSQL installed and running
- Python 3.8+
- A Telegram bot token from BotFather

## 1. Setup Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE budget_app;

# Connect to the new database
\c budget_app

# Run the unified schema script (creates all tables from scratch)
\i sql/schema.sql
```

The `sql/schema.sql` script will:
- Drop existing tables if they exist (for fresh deployment)
- Create all necessary tables with proper constraints
- Create indexes for query optimization
- Populate default categories and salary day example

## 2. Setup Python Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## 3. Configure Environment Variables

```bash
# Copy example to actual .env
cp .env.example .env

# Edit .env with your settings
nano .env
```

Set these values:
- `BOT_TOKEN`: Your Telegram bot token
- `DB_HOST`: PostgreSQL host (usually localhost)
- `DB_USER`: PostgreSQL username
- `DB_PASSWORD`: PostgreSQL password
- `DB_NAME`: budget_app (or your database name)

## 4. Run the Bot

```bash
python3 main.py
```

## Bot Commands

### `/start`
Shows welcome message and help about available commands.

### `/analyze`
Displays monthly analysis of transactions broken down by:
- **Expenses** by category (with count and total)
- **Income** by category (with count and total)
- Summary (total income, expenses, net)

### Upload PDF/HTML
Send a bank statement file (MAIB PDF or Victoriabank HTML):
1. Bot extracts transactions
2. Shows preview of extracted data
3. Presents **✅ Approve & Save** or **❌ Reject** buttons
4. If approved:
   - Creates audit_insert record to track file import
   - Checks for duplicates using 4-level detection:
     1. Exact raw_text match
     2. Same import + same date + shop + amount
     3. Any import + same date + shop + amount
     4. Any import + same shop + amount within ±5 days
   - Creates/finds shops and applies default category
   - Inserts transactions with full audit trail

## Database Schema

### Tables

**categories** - Transaction categories (income/expense)
**shops** - Merchant names with deduplication and default category
**salary_days** - Payroll cycle dates for financial analysis
**audit_inserts** - Import log (filename, type, timestamp)
**transactions** - Transaction records with full audit trail

Each transaction stores:
- Date, shop, and amount
- Currency conversion info
- Raw PDF/HTML line for debugging
- Link to import source file

## Duplicate Detection

The system uses 4-level duplicate detection to prevent importing:
1. **Exact matches**: Same raw_text line
2. **Same import duplicates**: Same file + date + shop + amount
3. **Same-day duplicates**: Different files but same date + shop + amount
4. **Window duplicates**: Same shop + amount within ±5 days

This prevents overlapping statement imports while allowing legitimate repeat purchases.

## Troubleshooting

### Database connection failed
- Verify PostgreSQL is running
- Check `.env` credentials
- Ensure `budget_app` database exists

### Schema errors
- If migrating from old schema, backup data first
- Run `\d` in psql to check existing tables
- Run `schema.sql` on fresh database

### Duplicate warnings
- Check `audit_inserts` table to see import history
- View `transactions.raw_text` to see source line
- Verify no overlapping statement date ranges
