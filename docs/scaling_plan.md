# Prop Firm Scaling Plan
*Last updated: 2026-05-13*

## Goal
Reach $1M+/month in funded account payouts using an automated trading bot (TradingView webhook → Tradovate → multiple prop firm accounts).

---

## Critical Finding: Automated Trading Policy by Firm

This is the most important filter. Only trade with firms that explicitly allow automation.

| Firm | Automation Allowed? | Source | Notes |
|------|--------------------|---------| ------|
| **LucidFlex** | ✅ **YES — explicitly permitted** | [Permitted Activities](https://support.lucidtrading.com/en/articles/11404728-permitted-activities) | Bots, EAs, trade copiers all OK. HFT and microscalping banned. |
| **Tradeify** | ✅ **YES** (verify current policy) | Help center | Has microscalping rule: >50% of trades AND profit must be from trades held >10 seconds |
| **MFFU** | ✅ **YES** (verify current policy) | Community reports | No explicit automation ban found |
| **Apex** | ❌ **BANNED — hard policy** | [Prohibited Activities](https://apextraderfunding.com/help-center/getting-started/prohibited-activities/) | Exact quote: *"No Automation or Algorithm Usage allowed"* — covers all webhook-triggered bots |
| **Take Profit Trader** | ⚠️ Verify | — | Not confirmed |
| **TradeDay** | ⚠️ Verify | — | Not confirmed |
| **Others** | ⚠️ Verify each | — | Check before opening eval |

**Always verify automation policy before buying an eval.** Look for their "Permitted Activities" or "Prohibited Activities" page.

---

## 50k vs 150k — Decision: **50k Accounts**

| Factor | 50k | 150k | Winner |
|--------|-----|------|--------|
| Eval cost (LucidFlex) | $130 | $315 | **50k** |
| Profit target | $3,000 | $9,000 | **50k** |
| Time to pass (est.) | 2–3 weeks | 6–8 weeks | **50k** |
| EOD drawdown buffer | $2,000 (3.3 trades) | $4,500 (7.5 trades) | 150k (more buffer) |
| Payout cycle 1 | $1,500 | ~$3,000 | 150k |
| Payouts per dollar invested | **~10× in 3 weeks** | ~8× in 7 weeks | **50k** |
| Max MNQ contracts | 40 micros | 100 micros | 150k |

**Verdict: 50k accounts scale better.** You pass faster, reinvest faster, and accumulate more funded accounts sooner. The 150k only makes sense if you want fewer, larger accounts — but at scale, many 50k accounts beat fewer 150k accounts on total monthly payout velocity.

---

## Phase-by-Phase Scaling Plan

### Phase 0: Prove the Strategy Works (Now → First Payout)
**Target: $1,500 first payout from LucidFlex 50k**

- [ ] Fill `.env` with real Tradovate credentials (live account)
- [ ] Set `TRADOVATE_ENV=live`, `SYMBOL=MNQM5`, `CONTRACTS=3`, `STOP_POINTS=60`
- [ ] Set `EXIT_STRATEGY=fixed_2r`
- [ ] Deploy bot on VPS (Dockerfile ready) with public URL for TradingView webhooks
- [ ] Add `tradingview/bot_signals.pine` to TradingView chart, create alert
- [ ] Monitor first 5 trades manually to verify fills, stops, exits
- [ ] Achieve 5 qualifying days (≥$150/day) → request first payout
- **Monthly payout: $1,350 (90% of $1,500)**
- **Eval cost: $130**

### Phase 1: First Multi-Account Run (Month 2–3)
**Target: 5 accounts across 2 firms → $5k–$8k/month**

- [ ] Open 2 more LucidFlex 50k evals (reinvest payout)
- [ ] Open 2 Tradeify 50k Select evals (verify automation policy first)
- [ ] Build **signal fan-out** in bot — one webhook → broadcasts to all 5 Tradovate accounts
- [ ] Use Tradovate Group Trade for same-login accounts (LucidFlex accounts can group)
- [ ] Track per-account P&L, consistency rule compliance, drawdown separately
- **Monthly payout: ~$5,000–$8,000**
- **Monthly eval cost: ~$650**

### Phase 2: Ten Firms, 50 Accounts (Month 4–6)
**Target: 50 accounts across 8–10 Tradovate firms → $50k–$80k/month**

- [ ] Research and verify automation policy for: MFFU, Take Profit Trader, TradeDay, Elite Trader Funding, Blue Guardian, Earn2Trade, The Trading Pit
- [ ] Open accounts at each confirmed bot-friendly firm
- [ ] Integrate **TradeSyncer** (third-party trade copier) for cross-login account copying
- [ ] Build account registry (config file listing all active accounts: firm, status, eval/funded, last payout)
- [ ] Automate account lifecycle: detect funded status, detect blown, trigger new eval
- **Monthly payout: ~$50,000–$80,000**
- **Monthly eval cost: ~$6,000–$10,000**

### Phase 3: Full Scale (Month 7–12)
**Target: 200+ accounts across all bot-friendly Tradovate firms → $200k–$400k/month**

- [ ] Max out account limits at each firm
- [ ] Add new firms as automation policy is confirmed
- [ ] Optimize strategy based on live data (which R:R, stop size, etc. passes eval fastest)
- [ ] Consider hiring to manage account admin (applications, payouts, resets)
- **Monthly payout: $200,000–$400,000**
- **Monthly eval cost: $25,000–$50,000**

### Phase 4: $1M/Month (Month 12–18)
**Target: 500–600 funded accounts across 15–19 Tradovate firms**

- Firms needed: 15 firms × ~35 accounts avg = ~525 funded accounts
- At $2,000 avg payout/account/month: **$1,050,000 gross**
- Monthly eval costs (replacing blown accounts, ~10% blow rate): ~$70k–$100k
- **Net: ~$950k–$980k/month**
- Infrastructure: TradeSyncer Pro, 2–3 VPS nodes, monitoring dashboard

---

## Confirmed Bot-Compatible Firms (Tradovate, Automation Allowed)

Start evals at these firms in priority order:

| Priority | Firm | 50k Eval | Payout Cap | Max Accounts | Split | Why |
|----------|------|----------|-----------|-------------|-------|-----|
| 1 | **LucidFlex** | $130 | $1,500 → $3,500 | TBD | 90/10 | Already set up, explicitly bot-friendly |
| 2 | **Tradeify Select** | $159/mo | $600/day | 5 | 90/10 | Same Tradovate infra, verify auto policy |
| 3 | **MFFU Rapid** | $157 one-time | Uncapped | 5 | 90/10 | Uncapped payout, verify auto policy |
| 4+ | Others | Varies | Varies | Varies | Varies | Verify automation before buying |

**Skip Apex entirely** — their "No Automation" policy is explicit and covers webhook bots.

---

## Tradeify Microscalping Rule (Important for Our Bot)

Tradeify enforces: **>50% of trades AND >50% of profits must come from trades held >10 seconds.**

Our bot's exit strategy:
- Breakeven stop trigger: immediate on 1R hit (can be <10 seconds on fast moves)
- Limit order (2R): usually fills within seconds on a strong move

**Risk:** Fast-moving days where many trades resolve in <10 seconds could flag the account.

**Mitigation:** Add a 15-second minimum hold delay before placing stop/TP orders. Implement as a `TRADEIFY_MODE=true` flag in config that adds a sleep before order placement.

---

## Bot Roadmap for Multi-Account Support

What needs to be built (in order):

### Next: Signal Fan-Out (enables Phase 1)
One incoming webhook signal → fires orders on all configured Tradovate accounts simultaneously.

```python
# Proposed config structure
ACCOUNTS = [
    {"name": "LucidFlex-1", "env": "live", "id": 123456, "spec": "user@lucidflex"},
    {"name": "LucidFlex-2", "env": "live", "id": 123457, "spec": "user@lucidflex"},
    {"name": "Tradeify-1",  "env": "live", "id": 234567, "spec": "user@tradeify"},
]
```

### After: Account Registry & Lifecycle
- `accounts.json` tracks: firm, account ID, status (eval/funded/blown), current P&L, last payout date
- Bot detects funded status via Tradovate API balance checks
- Auto-flags blown accounts (balance below drawdown threshold)

### After: Monitoring Dashboard
- Per-account daily P&L, drawdown remaining, days toward payout
- Alert when account needs attention (near drawdown, consistency violation approaching)

---

## Key Metrics to Track Per Account

| Metric | Target | Action if Breached |
|--------|--------|--------------------|
| Daily P&L | > -$600 (1 loss max) | Stop trading that account today |
| EOD trailing drawdown remaining | > $500 | Reduce to 1 contract |
| Consistency rule (single day %) | < 45% of running total | Cap position size on big green days |
| Days toward payout | 5 qualifying days | Trigger payout request automatically |
| Win rate (rolling 20 trades) | > 28% at 2R | Review strategy if drops below |

---

## The Realistic $1M/Month Timeline

The traders showing $1M/month on X have typically been doing this for 18–24 months. The compounding effect:
- Month 1: 1 account → $1,350 → fund 10 new evals
- Month 2: 5 accounts → $6,750 → fund 50 new evals
- Month 3: 20 accounts → $27,000 → fund 200 new evals
- Month 6: 100 accounts → $135,000 → pay yourself + fund 1,000 new evals
- Month 12: 400 accounts → $540,000/month
- Month 18: 600 accounts → $810,000/month

The bottleneck is **pass rate** (estimated 30–40% with our strategy vs 14% industry average) and **account limits per firm**.

With a 35% pass rate (Strategy G backtest showed 31–41%): 
- To maintain 600 funded accounts with 10% monthly blow rate: need 60 new funded accounts/month
- Need to open ~170 new evals/month at 35% pass rate
- Cost: 170 × $130 = $22,000/month in eval fees at scale
- At $810k gross: net ~$788k/month
