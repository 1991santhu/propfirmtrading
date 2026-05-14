# Strategy Findings — May 2026

Full 3.5-year backtest summary. Data: Jan 2023 – May 2026, 153,567 bars, Databento CME Globex.

---

## Top Strategies — 3.5 Year Net (Best Config Each)

| Rank | Strategy | Stop | RR | BE buf | Trades | Win% | Net/3.5yr | Net/mo |
|------|----------|------|----|----|--------|------|-----------|--------|
| 1 | A: ORB Only | 60pt | 2.0 | 0 | 677 | 33% | $17,250 | $421 |
| 2 | K: Pre-Market Levels | 60pt | 1.5 | 10 | 793 | 51% | $15,339 | $374 |
| 3 | N: Breakout+Retest+EMA | 60pt | 1.5 | 10 | 618 | 50% | $15,079 | $368 |
| 4 | D: KL + Cloud3 | 60pt | 1.5 | 0 | 459 | 37% | $13,810 | $337 |
| 5 | G: Breakout+Retest | 60pt | 2.0 | 10 | 1,290 | 51% | $12,359 | $302 |
| 6 | J: PDC Only | 60pt | 2.0 | 0 | 440 | 30% | $11,979 | $292 |

## By Recent Time Period (Last 6 Months: Nov 2025–May 2026)

| Rank | Strategy | Net |
|------|----------|-----|
| 1 | G: Breakout+Retest | $6,119 |
| 2 | M: Breakout+Retest+Trend | $5,491 |
| 3 | A: ORB Only | $3,867 |

G wins recently. ORB wins long-term. Market regime drives this — high-vol trending markets favor G.

---

## Confirmed Parameters

| Parameter | Optimal | Reason |
|-----------|---------|--------|
| Stop loss | **60pt** | Tested 60/80/100. 60 wins for top strategies |
| RR ratio | **2.0** (or 1.5 with be=10) | 2R best net; 1.5R needed with be_buffer for win rate |
| BE buffer | **10pt** | Lifts win rate 31%→51%, lifts net on G by $3k |
| Max daily losses | **2** | 1-loss: net halves. 3-loss: worst day -$1,818 vs $2k limit |
| Max daily trades | 5 | Never hit — signal fires avg 1.7x/day |
| Contracts | **5** | $600 risk/trade, 2 losses = $1,200 < $2k drawdown |
| Commission | $0.59/side | Tradovate all-in, always included |

---

## Funded Account Reality

**The $150/day × 5 days requirement is genuinely hard:**

- 38% of days produce ≥$150 profit (qualifying)
- 41% of days produce a damaging loss (>$300)
- Need 5 qualifying days → takes ~13 trading days on average
- In those 13 days: ~5.4 damaging days × ~$600 = **$3,221 expected drawdown**
- **$3,221 > $2,000 drawdown limit** — structurally challenging

**Per funded account outcome:**
- 40% blow before any payout (sequence of bad days before 5 qual days accumulate)
- 60% get at least 1 payout (average $1,584)
- 93% eventually blow (average 1.7 payouts before blowing)
- Still profitable: only $150 at risk per eval attempt, LucidFlex absorbs drawdown

**Eval pass rates:**
- ORB: 30% pass rate, avg 3.3 evals to pass, expected $500 per passed eval
- G: 19.7% pass rate, avg 5.1 evals to pass, expected $760 per passed eval

---

## Scalability

| Accounts | Monthly net | Notes |
|----------|------------|-------|
| 1 | $302–$421 | Starting point |
| 10 | $3,000–$4,200 | Realistic year-1 target |
| 50 | $15,000–$21,000 | Solo ceiling (operations intensive) |

$100k/month requires ~250+ accounts or institutional capital. Not realistic solo.

Realistic 3-year goal: 10-15 accounts across 2-3 prop firms = $4,500–$8,000/month fully automated.

---

## Infrastructure Costs (Not in Backtest Numbers)

- Cloud VM: ~$20/month
- TradingView Pro+: ~$40/month
- Total: ~$60/month (subtract from net above)

---

## Saved Backtest Reports

| File | Period | Coverage |
|------|--------|---------|
| `20260513_2031_2023-01-03_to_2026-05-13.md` | Full 3.5yr | All 14 strategies × 12 param combos |
| `20260513_2039_2023-01-01_to_2026-02-28.md` | No March 2026 | All strategies |
| `20260513_2045_2026-02-13_to_2026-05-13.md` | Last 3 months | All strategies |
| `20260513_2049_2025-11-13_to_2026-05-13.md` | Last 6 months | All strategies |

All in `docs/backtest_results/`.

---

## Key Data Fix (Important)

Previous results showing "only $1,049 net over 3 years" were wrong — all of 2025 and Jan-Feb 2026 were missing from the dataset. After downloading the missing year ($1.47 from Databento), real results:
- G: **$12,359 net** (not $1,049)
- ORB: **$17,250 net**

Always verify monthly bar counts before trusting a backtest:
```python
df_rth.groupby(df_rth.index.to_period('M')).size()
```
