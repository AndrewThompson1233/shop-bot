# shop-bot

Telegram digital goods store bot with CryptoPay payment processing.

## Stack

- aiogram 3.x
- SQLAlchemy 2 (async) + aiosqlite (SQLite)
- CryptoPay API integration
- Pydantic Settings

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Configure `.env`:
- `BOT_TOKEN`: Telegram bot token from @BotFather
- `CRYPTOPAY_TOKEN`: API token from @CryptoBot
- `ADMIN_IDS`: JSON array of admin Telegram IDs (e.g. `[123456789]`)
- `DB_URL`: Database connection string (defaults to local SQLite `shop.db`)

## Run

```bash
python -m src.main
```
