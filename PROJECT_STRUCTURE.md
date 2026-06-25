# BudgetApp Project Structure

## Goal

One shared PostgreSQL database, one Telegram bot, one Telegram Mini App, one backend API.
The bot and the Mini App both use the same data model and business rules, but they stay in separate delivery units.

## Root Layout

```text
BudgetApp/
├── budgetapp/                # Existing bot and shared parsing logic
├── backend/                  # New Python API for the Mini App
├── frontend/miniapp/         # React app for Telegram Web Apps
├── sql/                      # Database schema and seed data
├── tests/                    # Existing Python tests
├── Dockerfile                # Telegram bot container
├── backend/Dockerfile        # API container
├── docker-compose.yml        # Local orchestration for db + bot + api + frontend
└── requirements.txt          # Python dependencies shared by bot and API
```

## Backend API

```text
backend/app/
├── main.py                   # FastAPI app entrypoint
├── core/                     # Config, logging, DB connection helpers
├── api/routers/              # HTTP routes
├── repositories/             # SQL access and DB-facing helpers
├── services/                 # Business use-cases built on repositories
└── domain/                   # Future domain models and rules
```

### Responsibilities

- `core`: environment, logging, and connection primitives
- `repositories`: SQL queries and persistence logic
- `services`: application workflows and orchestration
- `api`: request/response layer only

## Frontend Mini App

```text
frontend/miniapp/
├── src/
│   ├── App.tsx               # Telegram Mini App shell
│   ├── main.tsx              # React bootstrap
│   └── styles.css            # Visual system for the Mini App
├── package.json              # React/Vite dependencies and scripts
├── vite.config.ts            # Vite dev/build config
└── Dockerfile                # Frontend container
```

### Responsibilities

- Render the Telegram Web App UI
- Read Telegram init data from `window.Telegram.WebApp`
- Call the backend API for transaction and analytics screens

## Shared Data Model

The same PostgreSQL database is used by:

- Telegram bot for uploads and approvals
- Backend API for the Mini App
- Analytics and duplicate detection logic

## Flow

1. User uploads bank data in Telegram bot or Mini App.
2. Backend logic parses and validates transactions.
3. Repositories persist to PostgreSQL.
4. Services expose the same data to the Mini App and the bot.
5. UI layers stay separate and stateless.

## Architecture Rule

The API should depend only on `backend/app/*`, not on `budgetapp/*`.
Legacy bot code can stay in `budgetapp/` until it is gradually migrated.