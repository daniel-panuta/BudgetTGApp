# BudgetApp - Telegram Bot for Bank Statement Management

BudgetApp is a Telegram bot that parses bank statements, lets the user review extracted expense transactions, detects duplicates, and saves approved entries into a PostgreSQL database.

## 🎯 What this project does

- Parses `.pdf` and `.html` bank statements
- Supports MAIB statement layouts and HTML exports
- Filters out P2P / A2A / IPS transfer lines
- Detects duplicate transactions before saving
- Stores transaction metadata in PostgreSQL
- Provides monthly expense analysis by category

## 📋 Main features

- **Upload bank statement** via Telegram
- **Preview parsed transactions** before saving
- **Approve or reject** parsed rows
- **Duplicate detection** using raw text or date/shop/amount
- **Shop normalization** and smart matching
- **Category assignment** using shop defaults or fallback expense category
- **Currency-aware parsing** with original currency and MDL conversion
- **Monthly analytics** through `/analyze`

## 🧩 Supported files

- `.pdf` bank statements (MAIB-style)
- `.html` statement exports
- File type is detected by content and extension

## 🚀 Quick setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup PostgreSQL

```bash
psql -U postgres -c "CREATE DATABASE budget_app;"
psql -U postgres -d budget_app -f "sql /create_schema.sql"
```

### 3. Add initial categories

```bash
psql -U postgres -d budget_app << 'EOF'
INSERT INTO categories (name, type) VALUES 
  ('Groceries', 'expense'),
  ('Transport', 'expense'),
  ('Entertainment', 'expense'),
  ('Restaurants', 'expense'),
  ('Utilities', 'expense'),
  ('Other', 'expense'),
  ('Salary', 'income');
EOF
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and provide your Telegram bot token and database settings.

### 5. Run the bot

```bash
python3 main.py
```

## � Docker support

### Build the Docker image

```bash
docker build -t budgetapp .
```

### Run the bot in Docker

```bash
docker run --env-file .env --rm budgetapp
```

### Notes

- `Dockerfile` installs dependencies with `pip install -r requirements.txt`

## �📦 Project structure

```
BudgetApp/
├── main.py             # Telegram bot application
├── parser.py           # PDF/HTML statement parser
├── db.py               # PostgreSQL CRUD and shop/category logic
├── config.py           # Configuration loader
├── requirements.txt    # Python dependencies
├── .env.example        # Template environment variables
├── SETUP.md            # Setup instructions
├── README.md           # Project documentation
├── sql /create_schema.sql # Database schema
└── extracts/           # Example bank statement samples
```

## 🔧 Configuration

The bot uses `.env` variables. Example values in `.env.example`:

```env
BOT_TOKEN=your_telegram_bot_token_here
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
# or local config:
# DB_HOST=localhost
# DB_PORT=5432
# DB_USER=postgres
# DB_PASSWORD=your_password
# DB_NAME=budget_app
# DB_SSLMODE=prefer
LOG_LEVEL=INFO
TEMP_PDF_FILENAME=temp_uploaded_statement.pdf
DEBUG_MODE=false
```

## 📱 Bot commands

### `/start`
Shows the welcome message and usage instructions.

### `/analyze`
Shows monthly analytics grouped by category and transaction type.

### Upload a statement file
Send a `.pdf` or `.html` bank statement to the bot.

The bot will:
- download the file
- detect whether it is PDF or HTML
- parse transactions
- show a preview with totals
- ask for approval before saving

## 💾 Database schema

### categories
- `id` SERIAL PRIMARY KEY
- `name` VARCHAR(50) UNIQUE NOT NULL
- `type` VARCHAR(10) NOT NULL CHECK (type IN ('income', 'expense'))

### shops
- `id` SERIAL PRIMARY KEY
- `name` VARCHAR(100) UNIQUE NOT NULL
- `default_category_id` INT REFERENCES categories(id) ON DELETE SET NULL

### transactions
- `id` SERIAL PRIMARY KEY
- `date` DATE NOT NULL
- `shop_id` INT REFERENCES shops(id) ON DELETE RESTRICT
- `category_id` INT REFERENCES categories(id) ON DELETE RESTRICT
- `amount` NUMERIC(10, 2) NOT NULL
- `currency` VARCHAR(10) NOT NULL DEFAULT 'MDL'
- `amount_original` NUMERIC(12, 2)
- `amount_mdl` NUMERIC(12, 2) NOT NULL
- `raw_text` TEXT

## 🧠 How parsing works

- `main.py` handles Telegram interactions
- `parser.py` reads PDF or HTML content
- HTML support uses `BeautifulSoup` and detects MAIB pages
- Parsed transaction fields include:
  - `date`
  - `shop`
  - `currency`
  - `amount_original`
  - `amount_mdl`
  - `amount`
  - `raw_text`
- `db.py` stores transactions and matches shops/categories

## ✅ Transaction workflow

1. User uploads a statement file.
2. Bot extracts rows and filters non-expense transfers.
3. User approves or rejects the parsed list.
4. Bot checks for duplicates.
5. Bot inserts approved transactions into PostgreSQL.
6. Bot returns a summary of inserted and skipped rows.

## 📊 Analysis output

The `/analyze` command summarizes current-month spending by category and separates income from expenses.

Example output:

```
📊 Monthly Analysis - June 2026

💸 Expenses:
  • Groceries: 7 transactions | 560.00 MDL
  • Transport: 3 transactions | 120.00 MDL

💰 Income:
  • Salary: 1 transaction | 15000.00 MDL

📈 Summary:
  Total Income: 15000.00 MDL
  Total Expenses: 680.00 MDL
  Net: 14320.00 MDL
```

## � Currency API support

To support multi-currency statements and store official rates:

1. Add a `currency_rates` table:

```sql
CREATE TABLE currency_rates (
  id SERIAL PRIMARY KEY,
  rate_date DATE NOT NULL,
  currency VARCHAR(10) NOT NULL,
  rate_to_mdl NUMERIC(12, 6) NOT NULL,
  UNIQUE(rate_date, currency)
);
```

2. Use a currency API to fetch daily rates and persist them.
   - Example endpoints: exchangerate.host, openexchangerates.org, fixer.io
   - Store `rate_date`, `currency`, and `rate_to_mdl`.
   - When parsing a transaction, use `currency` and `amount_original` to calculate `amount_mdl`.

3. Example flow:
   - Parse transaction currency from statement
   - Lookup rate for transaction date and currency
   - Convert original amount to MDL
   - Save both `amount_original` and `amount_mdl`

4. This enables analysis of:
   - currency exposure by month
   - foreign spending trends
   - impact of exchange rates on expenses

## 📅 Salary and recurring income analysis

To model salary payment dates and recurring income:

1. Add a salary schedule table:

```sql
CREATE TABLE salary_schedule (
  id SERIAL PRIMARY KEY,
  salary_date DATE NOT NULL,
  amount NUMERIC(12, 2),
  description TEXT,
  recurring BOOLEAN DEFAULT TRUE
);
```

2. Detect monthly salary transactions by category and description.
   - Mark transactions with category `income` and shop names like `Salary`, `Employer`, or known payroll sources.
   - Save the actual salary date and amount.

3. Use salary data to analyze:
   - monthly income consistency
   - salary date changes over time
   - salary-to-expense ratio per month
   - if expenses spike before or after salary date

## 📈 Extended analytics ideas

Add richer reporting beyond simple monthly sums:

- Monthly income vs. expense ratio
- Average spending per category and merchant
- Trend lines for each category over 3 / 6 / 12 months
- Salary date vs. cash flow timing analysis
- Recurring payment detection and projection
- Currency breakdown: local vs foreign spending
- Category share of total expenses
- Top merchants by value and frequency

## 🚀 Implementation notes

These enhancements are useful for turning raw transaction data into budgeting insights:

- Keep `currency` in each transaction record
- Store `amount_original`, `amount_mdl`, and `rate_date`
- Use a separate rate table for historical accuracy
- Add explicit salary/recurring income metadata if needed

## �🛠 Troubleshooting

### "Database connection failed"
- Ensure PostgreSQL is running
- Verify `.env` database credentials
- Confirm the target database exists

### "No transactions found"
- Confirm the statement is in a supported MAIB format
- Try a different HTML export or PDF layout

### "No categories found"
- Insert at least one expense category into `categories`
- The bot requires an expense category for fallback mapping

## 🚀 Future improvements

- manual category assignment during approval
- shop/category mapping UI
- export transactions to CSV
- support more banks and formats
- advanced budget/time range analysis
