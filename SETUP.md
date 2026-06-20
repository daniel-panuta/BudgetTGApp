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

# Run the schema script
\i sql/create_schema.sql

# Add some initial categories (example)
INSERT INTO categories (name, type) VALUES 
  ('Groceries', 'expense'),
  ('Transport', 'expense'),
  ('Entertainment', 'expense'),
  ('Salary', 'income'),
  ('Other', 'expense');
```

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

### Upload PDF
Send a maib bank statement PDF file:
1. Bot extracts transactions
2. Shows preview of extracted data
3. Presents **✅ Approve & Save** or **❌ Reject** buttons
4. If approved:
   - Checks for duplicates (date + shop + amount)
   - Creates shops if they don't exist
   - Assigns default categories
   - Saves to database
5. Returns summary with inserted count and any duplicates skipped

## Database Schema

### categories
- `id`: Auto-increment ID
- `name`: Category name (UNIQUE)
- `type`: 'income' or 'expense'

### shops
- `id`: Auto-increment ID
- `name`: Shop name (UNIQUE)
- `default_category_id`: FK to categories (auto-assigned on first transaction)

### transactions
- `id`: Auto-increment ID
- `date`: Transaction date (YYYY-MM-DD)
- `shop_id`: FK to shops
- `category_id`: FK to categories
- `amount`: Transaction amount in MDL
- `raw_text`: Original line from PDF (for debugging)

## Features

✅ **PDF Parsing**: Extracts date, shop, amount from maib statements
✅ **Preview & Approval**: Shows data before saving to DB
✅ **Duplicate Detection**: Skips transactions with same date + shop + amount
✅ **Auto-shop Creation**: Creates new shops if not in database
✅ **Category Assignment**: Uses shop's default category or first expense category
✅ **Monthly Analysis**: Breakdown by categories with income/expense split
✅ **Smart Filtering**: Ignores P2P and A2A transfers

## Troubleshooting

### "Database connection failed"
- Check if PostgreSQL is running
- Verify .env credentials
- Check if database exists

### "No categories found"
- Run the INSERT statement in step 1 to add categories
- At least one 'expense' category is needed

### "PDF parsing failed"
- Ensure PDF is from maib bank
- Check if regex pattern matches your statement format

## Future Enhancements

- [ ] Manual category assignment during approval
- [ ] Shop-to-category mapping UI
- [ ] Monthly budget limits and alerts
- [ ] Export to CSV
- [ ] Custom date range analysis
- [ ] Category-specific trends
