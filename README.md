# PropFirm Trading Bot

Automated trading bot for LucidFlex 50k futures prop firm accounts.  
Trades /MNQ (Micro Nasdaq) via Tradovate using TradingView webhook signals.

**Private repo** — never commit `.env` (gitignored). Copy `.env.template` and fill in credentials locally.

## Architecture

```
TradingView Alert
  → POST /signal (webhook)
  → Risk Manager (loss limit, trade count, time gate)
  → Order Manager (market order → stop order → DB state)
  → Position Tracker (breakeven at 1R, close at 2R)
  → Scheduler (EOD close 4:40PM, daily reset 9:30AM)
```

## Quick Start

### 1. Clone and install

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.template .env
# Fill in Tradovate credentials, SYMBOL, STOP_POINTS, etc.
```

### 3. Run (demo mode)

```bash
python main.py
```

Server starts on `http://localhost:8000`.

### 4. Health check

```bash
curl http://localhost:8000/health
```

### 5. Send a test signal

```bash
curl -X POST http://localhost:8000/signal \
  -H "Content-Type: application/json" \
  -d '{"signal":"long","symbol":"MNQM5","price":21000,"secret":"your_webhook_secret"}'
```

### 6. Switch to live trading

Set `TRADOVATE_ENV=live` in `.env`. The bot will route to the live Tradovate API.

---

## Key Configuration (`.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `TRADOVATE_ENV` | `demo` or `live` | `demo` |
| `SYMBOL` | Contract symbol (update quarterly) | `MNQM5` |
| `CONTRACTS` | Number of contracts per trade | `3` |
| `STOP_POINTS` | Stop loss in /MNQ points | `60` |
| `EXIT_STRATEGY` | `fixed_2r` or `trailing` | `fixed_2r` |
| `MAX_DAILY_LOSSES` | Max losing trades before bot stops | `2` |
| `MAX_DAILY_TRADES` | Max total trades per day | `5` |
| `CLOSE_HOUR_EST` | EOD auto-close hour (EST) | `16` |
| `CLOSE_MINUTE_EST` | EOD auto-close minute | `40` |

## Exit Strategies

- **`fixed_2r`** — Stop moves to breakeven at +30pts. Take profit at +60pts (2R). Entire position closed.
- **`trailing`** — 20% at 1R, 20% at 2R, trail remainder with 30pt stop.

---

## Module Overview

| Module | Purpose |
|--------|---------|
| `bot/webhook.py` | FastAPI endpoints, signal intake |
| `bot/risk_manager.py` | Time gate, daily loss/trade limits |
| `bot/order_manager.py` | Entry order → stop order → DB |
| `bot/position_tracker.py` | Manages open position lifecycle |
| `bot/scheduler.py` | EOD close + daily reset cron |
| `broker/tradovate.py` | Tradovate REST + WebSocket client |
| `db/state.py` | SQLite state (position, daily counters) |
| `config.py` | All settings from `.env` |

---

## Tests

```bash
pytest                  # all tests
pytest tests/ -v        # verbose
pytest tests/test_risk_manager.py   # single file
```

---

## Docker

```bash
docker build -t propfirm-bot .
docker run --env-file .env -p 8000:8000 propfirm-bot
```

---

## TradingView Alert Setup

1. Add `tradingview/bot_signals.pine` as a strategy to your /MNQ 5-min chart
2. Set alert → `Webhook URL` → your public URL + `/signal`
3. Alert message body (JSON):
   ```json
   {"signal":"{{strategy.order.action}}","symbol":"MNQM5","price":{{close}},"secret":"YOUR_WEBHOOK_SECRET"}
   ```
4. For local testing, use [ngrok](https://ngrok.com): `ngrok http 8000`

---

## Symbol Rollover

Tradovate futures contracts expire quarterly (Mar/Jun/Sep/Dec).  
Update `SYMBOL=` in `.env` before expiry:
- MNQ**H**5 = March 2025
- MNQ**M**5 = June 2025
- MNQ**U**5 = September 2025
- MNQ**Z**5 = December 2025

---

## Security

| File | Committed to Git? |
|------|-------------------|
| `.env` | No (gitignored) — Tradovate, Databento, Polygon keys |
| `.git/credentials-trading` | No — optional local GitHub HTTPS auth (repo-only) |

Do not paste API keys or tokens into AI chat or screenshots.

---

## Git push

Uses a repo-local credentials file (`.git/credentials-trading`) so work Keychain entries for `github.com` are not used.

```bash
cd /path/to/propfirm_trading
git add .
git commit -m "your message"
git -c credential.helper= -c credential.helper='store --file=.git/credentials-trading' push origin master
```

One-time setup on a new machine: create `.git/credentials-trading` with one line  
`https://1991santhu:YOUR_GITHUB_TOKEN@github.com` and `chmod 600` it. Do not commit this file.

---

## Scaling to Multiple Accounts

See `docs/scaling.md` for the horizontal scaling strategy (trade copiers across multiple funded accounts).
See `research/reports/` for ongoing prop firm research.

---

## Backtest Strategies

See **[docs/strategies.md](docs/strategies.md)** for the full strategy reference:
- How the simulator works (stops, TP, breakeven, daily limits)
- All 12 active strategies (A, B, C, D, E, F, G, J, K, N, O, P) with signal logic and performance
- Key levels, EMA cloud definitions, data pipeline
- Backtest results saved in `docs/backtest_results/`
