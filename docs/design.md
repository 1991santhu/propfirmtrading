# PropFirm Trading Bot — Design Spec
**Date:** 2026-05-13  
**Status:** Approved  
**Target:** LucidTrading LucidFlex 50k, /MNQ futures, Tradovate

---

## Problem

Trader has blown 60+ prop firm accounts and spent $5k+ in evaluation fees. Has passed evaluations multiple times but never received a payout due to:
- No stop loss, ever
- 50+ trades per day (overtrading)
- Losses held long, winners cut short
- Averaging down on losing positions
- Emotional decision-making under pressure

The strategy itself is profitable enough to pass evaluations. The problem is execution discipline. Automation removes the human from execution entirely.

---

## Goal

Build an automated trading bot that:
1. Receives entry signals from TradingView
2. Enforces all risk rules with zero human override
3. Manages partial exits and trailing stops automatically
4. Complies with all LucidTrading platform rules
5. Gets a funded account payout by end of May / early June 2026

---

## Architecture — Option C (Hybrid)

```
TradingView (Pine Script alerts)
       │ HTTPS webhook (JSON)
       ▼
Python Bot (FastAPI) — runs on laptop initially, portable to VPS/AWS
  ├── Webhook Receiver      — validates and routes incoming signals
  ├── Risk Manager          — enforces all rules before any order
  ├── Order Manager         — places and modifies orders via Tradovate API
  ├── Position Tracker      — manages partial exits and stop ladder
  └── Scheduler             — auto-close at 4:40 PM EST, daily resets
       │ REST + WebSocket
       ▼
Tradovate API (LucidTrading Flex 50k account)
  └── /MNQ orders with isAutomated: true (CME requirement)
```

**Why Option C over A (no-code) or B (pure Python):**
- Ripster EMA clouds are battle-tested in TradingView — replicating in Python adds risk of signal drift
- TradingView handles signal math, Python handles discipline enforcement
- ~1-2 second webhook latency acceptable for /MNQ swing-style entries
- Architecture naturally supports multi-account scaling later

---

## Loose Coupling Design

All components are decoupled for portability:

1. **Config via .env** — swap credentials, parameters, symbols without touching code
2. **Broker abstraction layer** — `BrokerClient` interface; Tradovate is one implementation. Swap broker by swapping one file.
3. **Generic signal receiver** — accepts JSON webhooks from any source (TradingView today, custom algo tomorrow)
4. **State in SQLite** — portable, no server needed. Migrate to Postgres/AWS RDS with zero code changes
5. **Dockerfile included** — runs identically on laptop, VPS, AWS, or anywhere

---

## Signal Layer (TradingView — Phase 2)

**Note:** TradingView Pine Script is Phase 2. Bot is built and tested with manual webhook calls first.

Three components must align to fire a signal:
1. **Key level** — price interacting with ORB High/Low or Previous Day High/Low
2. **Ripster EMA cloud direction** — green = long only, red = short only, mixed = no signal
3. **Entry trigger** — price bounces off key level with cloud confirmation

**Webhook payload:**
```json
{
  "signal": "long",
  "symbol": "MNQM5",
  "price": 19850.25,
  "level": "ORB_HIGH",
  "timestamp": "2026-05-13T14:32:00Z",
  "secret": "your-private-key"
}
```

---

## Risk Manager Rules (enforced before every order)

| Check | Rule | Action if failed |
|---|---|---|
| Already in position | No new entry while open | Reject signal |
| Daily losses ≥ 2 | Done for the day | Reject, log |
| Daily trades ≥ 5 | Done for the day | Reject, log |
| Time after 4:30 PM EST | Too close to cutoff | Reject, log |
| Invalid secret key | Security check | Reject, alert |
| Eval consistency | Today's P&L would exceed 50% of total | Warn, allow |

---

## Order Execution Flow

```
1. Signal approved by Risk Manager

2. Place bracket order on Tradovate:
   - Market entry, N contracts
   - Hard stop loss: 60 points, placed at exchange
   - isAutomated: true

3. WebSocket confirms fill → Position Tracker activates

4. Position Tracker monitors price milestones:
   Entry = X, R = 60 pts

   Price hits X + 60 (1R):
     → Close 20% of contracts (1 contract)
     → Modify stop to X (breakeven)

   Price hits X + 120 (2R):
     → Close 20% of contracts (1 contract)
     → Modify stop to X + 60 (1R locked)

   Price hits X + 180 (3R):
     → Modify stop to X + 120 (2R locked)
     → Continue trailing (stop always = current milestone - 1R)

   Trailing continues indefinitely until:
     → Stop hit (position closed, loss/win logged)
     → 4:40 PM EST (force close)

5. Result logged to SQLite + console
```

---

## Trailing Stop Logic

Stop always trails at: `highest_milestone_reached - 1R`

```
Milestone 0 (entry):    stop at -1R (60 pts below entry)
Milestone 1 (1R hit):   stop at  0R (breakeven)
Milestone 2 (2R hit):   stop at +1R (60 pts profit locked)
Milestone 3 (3R hit):   stop at +2R (120 pts profit locked)
Milestone 4 (4R hit):   stop at +3R (180 pts profit locked)
... continues until stopped out or market close
```

No hard profit target — let winners run as far as possible.

---

## Position Sizing

| Phase | Contracts | Risk/trade | Max daily loss (2 stops) |
|---|---|---|---|
| Eval | 3 MNQ | $360 | $720 |
| Funded tier 1 ($0-$999 profit) | 3 MNQ | $360 | $720 |
| Funded tier 2 ($1k+ profit) | 5 MNQ | $600 | $1,200 |
| Funded tier 3 ($2k+ profit) | 7 MNQ | $840 | $1,680 |

Start conservative, scale up as account grows. Parameters adjustable via .env.

---

## Platform Rules Enforced by Bot

| Rule | Implementation |
|---|---|
| No overnight positions (cutoff 4:45 PM EST) | Force close all at 4:40 PM EST (5-min buffer) |
| No hedging across accounts | Single direction only; multi-account mode always same direction |
| No averaging down | New entries blocked while any position is open |
| No microscalping | Minimum hold time enforced (configurable) |
| Max 2 losses/day | Hard counter, bot shuts off after 2nd loss |
| Max 5 trades/day | Hard counter, bot shuts off after 5th trade |

---

## LucidFlex 50k Account Rules (Reference)

### Eval
| Rule | Value |
|---|---|
| Profit target | $3,000 |
| Max drawdown (EOD trailing) | $2,000 |
| Daily loss limit | None |
| Consistency rule | Biggest day ≤ 50% of total profit |
| Max contracts /MNQ | 40 micros |

### Funded
| Rule | Value |
|---|---|
| Max drawdown (EOD trailing) | $2,000 |
| Daily loss limit | None |
| Consistency rule | None |
| Payout requirement | 5 days with ≥$150 profit each |
| Min payout | $500 |
| Max payout per cycle | 50% of profit, capped at $2,000 |
| Payout split | 90% trader / 10% Lucid |

---

## State Management

Bot tracks in SQLite (resets counters daily at 9:30 AM EST):

```python
state = {
    "daily_losses": 0,       # stops trading at 2
    "daily_trades": 0,       # stops trading at 5
    "in_position": False,    # blocks new entries
    "daily_pnl": 0.0,        # for eval consistency check
    "total_pnl": 0.0,        # cumulative, never resets
    "position": {
        "contracts": 0,
        "entry_price": 0.0,
        "stop_price": 0.0,
        "milestone": 0       # highest R milestone reached
    }
}
```

---

## Project Structure

```
propfirm_trading/
├── .env                    # all config and secrets
├── Dockerfile              # for portability
├── requirements.txt
├── main.py                 # entry point
├── config.py               # loads .env
├── broker/
│   ├── base.py             # BrokerClient interface
│   └── tradovate.py        # Tradovate implementation
├── bot/
│   ├── webhook.py          # FastAPI receiver
│   ├── risk_manager.py     # all rule checks
│   ├── order_manager.py    # entry/exit logic
│   ├── position_tracker.py # partial exits, stop ladder
│   └── scheduler.py        # 4:40 PM close, daily resets
├── db/
│   └── state.py            # SQLite state management
└── logs/
    └── trades.log          # full audit trail
```

---

## Tech Stack

| Component | Choice | Reason |
|---|---|---|
| Language | Python 3.11+ | Tradovate API well-supported, fast to build |
| Web framework | FastAPI | Async, lightweight, perfect for webhook receiver |
| Broker API | Tradovate REST + WebSocket | LucidTrading's platform |
| Signal source | TradingView webhooks | Ripster already built-in |
| Database | SQLite → Postgres | Start simple, scale later |
| Deployment | Laptop → VPS/AWS | Start free, scale when needed |
| Scheduler | APScheduler | Lightweight Python scheduler |

---

## Deployment (Phase 1 — Laptop)

Requirements:
- Laptop on and plugged in during market hours
- Stable internet connection
- Python 3.11+ installed
- Run: `python main.py`

Move to VPS/AWS when:
- Scaling to multiple accounts
- Want fully hands-off operation
- Travelling

---

## Timeline

| Milestone | Target Date |
|---|---|
| Design approved | 2026-05-13 |
| Implementation plan written | 2026-05-13 |
| Bot built and tested locally | 2026-05-16 to 2026-05-18 |
| Live on eval account | 2026-05-18 to 2026-05-20 |
| Eval passed | 2026-05-25 to 2026-05-28 |
| First funded payout | Early June 2026 |

---

## Phase 2 — TradingView Pine Script

After bot is live and tested, add:
- ORB High/Low detection (first 30 min)
- Previous Day High/Low levels
- Ripster EMA cloud direction filter
- Webhook alert firing on signal confluence

---

## Phase 3 — Multi-Account Scaling

After first payout proven:
- Add Tradeify, Apex, MyFundedFutures accounts
- Bot fans out one signal to multiple Tradovate accounts
- All accounts always same direction (cross-firm hedging is prohibited)
- Each account has independent daily loss counters and state
