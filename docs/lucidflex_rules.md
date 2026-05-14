# LucidFlex Rules Reference

Sourced from LucidFlex support articles, May 2026.
Links: https://support.lucidtrading.com/en/collections/16914631-lucidflex

---

## Evaluation Account

| Rule | $25k | $50k | $100k | $150k |
|------|------|------|-------|-------|
| Profit target | $1,250 | **$3,000** | $6,000 | $9,000 |
| Max drawdown (EOD trailing) | $1,000 | **$2,000** | $3,000 | $4,500 |
| Daily loss limit | None | None | None | None |
| Consistency rule | 50% | **50%** | 50% | 50% |
| Max contracts (minis) | 2 | **4** | 6 | 10 |
| Max contracts (micros) | 20 | **40** | 60 | 100 |
| Time limit | None | None | None | None |
| Eval fee | ~$75 | **~$150** | ~$250 | ~$350 |

**Consistency rule (eval only):** Largest single profitable day ÷ total account profit ≤ 50%.
Small cushion (~4%) built in. If violated: cannot upgrade — keep trading until ratio drops below 50%.
Consistency rule does NOT apply in the funded phase.

**When you pass:** Upgrade to funded account happens within 5–30 minutes. No activation fee.

**Contract limits during eval:** No scaling restrictions — full access from day 1.

---

## Funded Account

| Rule | $25k | $50k | $100k | $150k |
|------|------|------|-------|-------|
| Max drawdown (EOD trailing) | $1,000 | **$2,000** | $3,000 | $4,500 |
| Daily loss limit | None | None | None | None |
| Consistency rule | None | **None** | None | None |
| MLL trail locks at balance | $26,100 | **$52,100** | $103,100 | $154,600 |
| MLL locks to (permanent floor) | $25,100 | **$50,100** | $100,100 | $150,100 |

**No daily loss limit.** No consistency rule.

---

## Drawdown Mechanics (EOD Trailing)

- Drawdown is tracked at **end of trading session only** — not intraday
- MLL (Max Loss Limit) = your account floor; balance touching MLL = account breached
- MLL starts at: account_size − max_drawdown (e.g., $50,000 − $2,000 = $48,000)
- MLL **trails upward** as EOD balance rises (e.g., balance $51,000 → MLL $49,000)
- MLL **locks permanently** when balance exceeds the trail lock threshold:
  - $50k account: balance > $52,100 → MLL locks at $50,100 forever
  - After lock: MLL stays at $50,100 regardless of future balance moves

**Payout trigger also locks MLL:** Requesting any payout before naturally exceeding $52,100 immediately locks MLL to $50,100. This means after your first payout, your remaining risk is only (current_balance − $50,100).

---

## Scaling Plan (Funded Accounts Only)

Contract limits update at **end of each trading session**.
Payouts reduce your simulated balance → can drop you to a lower tier.

| Simulated Profit | $25k max | $50k max | $100k max | $150k max |
|-----------------|----------|----------|-----------|-----------|
| $0 – $999 | 10 micros | **20 micros** | 30 micros | 40 micros |
| $1,000 – $1,999 | 20 micros | **30 micros** | 40 micros | 50 micros |
| $2,000 – $2,999 | — | **40 micros** | 50 micros | 60 micros |
| $3,000 – $4,499 | — | — | 60 micros | 80 micros |
| $4,500+ | — | — | — | 100 micros |

**Eval phase:** No scaling restrictions — full contract access from the start.

---

## Payouts

| Rule | $25k | $50k | $100k | $150k |
|------|------|------|-------|-------|
| Qualifying days per cycle | 5 | **5** | 5 | 5 |
| Min profit per qualifying day | $100 | **$150** | $200 | $250 |
| Payout split | 90% trader | **90% trader** | 90% trader | 90% trader |
| Max payout per cycle (50% of profit) | $1,000 | **$2,000** | $2,500 | $3,000 |
| Min payout request | $500 | **$500** | $500 | $500 |
| Max payouts per funded account | 5 | **5** | 5 | 5 |

**How payout amount is calculated:**
1. You need 5 qualifying days (each ≥ $150 profit for 50k) AND positive net profit in current cycle
2. Max withdrawal = min(50% × current_cycle_profit, $2,000)
3. Trader receives = withdrawal × 90%
4. Sim balance decreases by the withdrawal amount
5. Payout cycle resets (qualifying days and cycle profit restart from 0)

**After 5 payouts:** Account enters live review. Not all accounts are approved for live.

**Zero-payout blown accounts:** If funded account blows before achieving any payout, the **eval fee is refunded**.

---

## Live Account Structure

Source: https://support.lucidtrading.com/en/articles/13425130-new-live-structure

Traders enter live review after Payout 5, significant lifetime payouts, exceptional performance, or prior live history. Live transition is at Lucid risk team's discretion — not guaranteed.

| Rule | $25k | $50k | $100k | $150k |
|------|------|------|-------|-------|
| Starting balance | $0 | **$0** | $0 | $0 |
| Starting drawdown limit | $1,000 | **$2,000** | $3,000 | $4,500 |
| Max contracts (micros) | 20 | **40** | 60 | 100 |
| Daily payouts | Yes | Yes | Yes | Yes |
| MLL Lock rule | Applies | **Applies** | Applies | Applies |

**Live Bonus (first trip only):**
| Account | Profit target for bonus | Bonus amount |
|---------|------------------------|--------------|
| $25k | $1,100 | $1,000 |
| $50k | $2,100 | **$2,000** |
| $100k | $3,100 | $3,000 |
| $150k | $4,600 | $4,500 |

**After blowing live account:** 2-week cooldown before purchasing new evaluation.

---

## Key Rules Bot Must Enforce

1. **No overnight positions** — all must close by 4:45 PM ET (bot closes at 4:40 PM ET)
2. **No hedging** across accounts — long one account, short another = violation (permanent ban risk)
3. **No microscalping** — trades must have realistic hold times
4. **Automation allowed** — bots permitted; trader responsible for errors
5. **No household hedging** — if one household member is live, others cannot trade sim

---

## Simulation Parameters for prop_firm.py

For $50k LucidFlex:

```python
account_size        = 50_000.0
eval_fee            = 150.0
profit_target       = 3_000.0   # eval only
max_drawdown        = 2_000.0   # EOD trailing
mll_lock_threshold  = 52_100.0  # balance above this → MLL locks
mll_lock_floor      = 50_100.0  # MLL locked permanently at this level
consistency_ratio   = 0.50      # eval only: biggest day ≤ 50% of total profit
min_payout_days     = 5
min_day_profit      = 150.0     # per qualifying day
payout_max_pct      = 0.50      # max 50% of cycle profit per payout
payout_cap          = 2_000.0   # hard cap
payout_split        = 0.90      # 90% to trader
max_funded_payouts  = 5         # then live review
```
