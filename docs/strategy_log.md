# Strategy Performance Log

Running log of param study results. Top 4 models by net profit added each run.
"Net" = total LucidFlex payouts received minus eval fees paid (not raw trade P&L).
All runs: /MNQ, $2/point, 5 contracts, max 2 daily losses, max 5 daily trades, no first-30min.

---

## How to Read This Log

| Column | Meaning |
|--------|---------|
| Model | Strategy letter + name |
| Stop | % of entry price used as stop loss |
| RR | Risk:Reward ratio for take profit |
| BE | Breakeven buffer points after 1R hit (0 = move to exact entry) |
| Win% | % of trades with positive P&L |
| P&L | Raw cumulative trade profit (before prop firm fee math) |
| Net | Payouts received − eval fees (what you actually pocket) |

---

## Run Log

---

### [2026-05-13 23:27] 6-Month Sweep — 12 Models, Old Simulator

**Period:** 2025-11-13 → 2026-05-13 (10,010 RTH bars)
**Models:** A B C D E F G J K N O P (12 total — no Q yet)
**Grid:** stop_pct=[0.15, 0.20, 0.25, 0.30] × rr=[1.5, 2.0] × be=[0, 10]
**Simulator:** v1 — BE stops counted as daily losses (be_moved bool)
**Full report:** `docs/backtest_results/20260513_2327_2025-11-13_to_2026-05-13.md`

| # | Model | Stop | RR | BE | Win% | P&L | Net |
|---|-------|------|----|----|------|-----|-----|
| 1 | P: ORB Breakout + Retest | 0.20% | 1.5 | 0 | 47.0% | $15,586 | $7,761 |
| 2 | P: ORB Breakout + Retest | 0.20% | 1.5 | 10 | 60.9% | $15,478 | $7,638 |
| 3 | P: ORB Breakout + Retest | 0.20% | 2.0 | 10 | 60.9% | $17,569 | $5,941 |
| 4 | P: ORB Breakout + Retest | 0.20% | 2.0 | 0 | 38.3% | $16,912 | $5,624 |

**Best per model (top 4):**

| Model | Stop | RR | BE | Net |
|-------|------|----|----|-----|
| P: ORB Breakout + Retest | 0.20% | 1.5 | 0 | $7,761 |
| F: Cloud Flip Near Key Level | 0.15% | 1.5 | 10 | $4,650 |
| B: All Key Levels | 0.25% | 2.0 | 0 | $4,492 |
| G: Breakout + Retest | 0.25% | 1.5 | 10 | $4,306 |

**Key observation:** P dominates recent 6mo with low stop and RR1.5. F competitive with tight stop.

---

### [2026-05-13 23:31] 3.5-Year Sweep — 12 Models, Old Simulator

**Period:** 2023-01-03 → 2026-05-13 (69,303 RTH bars)
**Models:** A B C D E F G J K N O P (12 total — no Q yet)
**Grid:** stop_pct=[0.15, 0.20, 0.25, 0.30] × rr=[1.5, 2.0] × be=[0, 10]
**Simulator:** v1 — BE stops counted as daily losses (be_moved bool)
**Full report:** `docs/backtest_results/20260513_2331_2023-01-03_to_2026-05-13.md`

| # | Model | Stop | RR | BE | Win% | P&L | Net |
|---|-------|------|----|----|------|-----|-----|
| 1 | F: Cloud Flip Near Key Level | 0.15% | 1.5 | 10 | 51.2% | $51,689 | $23,460 |
| 2 | P: ORB Breakout + Retest | 0.20% | 2.0 | 0 | 30.1% | $31,165 | $19,399 |
| 3 | P: ORB Breakout + Retest | 0.20% | 1.5 | 0 | 37.3% | $26,590 | $18,173 |
| 4 | P: ORB Breakout + Retest | 0.25% | 1.5 | 0 | 37.7% | $31,714 | $17,267 |

**Best per model (top 4):**

| Model | Stop | RR | BE | Net |
|-------|------|----|----|-----|
| F: Cloud Flip Near Key Level | 0.15% | 1.5 | 10 | $23,460 |
| P: ORB Breakout + Retest | 0.20% | 2.0 | 0 | $19,399 |
| B: All Key Levels | 0.15% | 1.5 | 10 | $15,001 |
| D: Key Levels + Cloud 3 | 0.25% | 1.5 | 0 | $14,794 |

**Key observation:** F wins over full 3.5yr. P is strong but F's high signal frequency and tight stop compounds well over time. B surprisingly strong at 3.5yr, weak in recent 6mo.

---

### [2026-05-13 23:57] 6-Month Sweep — 13 Models, New Simulator

**Period:** 2025-11-13 → 2026-05-13 (10,010 RTH bars)
**Models:** A B C D E F G J K N O P Q (13 total — Q added: Cloud Flip + ORB Retest)
**Grid:** stop_pct=[0.15, 0.20, 0.25, 0.30] × rr=[1.5, 2.0] × be=[0, 10]
**Simulator:** v2 — BE stops do NOT count as daily losses (be_stage int, be_ladder support added)
**Full report:** `docs/backtest_results/20260513_2357_2025-11-13_to_?.md`

| # | Model | Stop | RR | BE | Win% | P&L | Net |
|---|-------|------|----|----|------|-----|-----|
| 1 | P: ORB Breakout + Retest | 0.25% | 1.5 | 10 | 62.6% | $19,935 | $5,664 |
| 2 | O: B+R + Trend + EMA | 0.30% | 2.0 | 0 | 34.0% | $1,992 | $2,950 |
| 3 | G: Breakout + Retest | 0.25% | 1.5 | 0 | 38.9% | $11,128 | $2,650 |
| 4 | A: ORB Only | 0.25% | 2.0 | 10 | 47.6% | -$6,736 | $2,500 |

**Best per model (top 4):**

| Model | Stop | RR | BE | Net |
|-------|------|----|----|-----|
| P: ORB Breakout + Retest | 0.25% | 1.5 | 10 | $5,664 |
| O: B+R + Trend + EMA | 0.30% | 2.0 | 0 | $2,950 |
| G: Breakout + Retest | 0.25% | 1.5 | 0 | $2,650 |
| Q: Cloud Flip + ORB Retest | 0.20% | 2.0 | 10 | $1,750 |

**Key observation:** Simulator v2 change significantly affected cloud-based models (F dropped from $4,650 → $1,319 net). P remains strongest. Q (F+P combined) landed 6th overall — F component may dilute P's selectivity. 0.25% stop outperforms 0.20% for P in recent 6mo.

**⚠️ Simulator change note:** v1 → v2 changed how BE stops affect daily loss count. In v1, a BE stop (even at breakeven) consumed one of the 2 allowed daily losses. In v2, only hard SL exits count as losses. This freed up more daily trades for cloud-heavy models like F, leading to more lower-quality late-day entries and lower net. Results between v1 and v2 are NOT directly comparable for BE-heavy models.

---

### [2026-05-14 00:01] 3.5-Year Sweep — 13 Models, New Simulator

**Period:** 2023-01-03 → 2026-05-13 (69,303 RTH bars)
**Models:** A B C D E F G J K N O P Q (13 total — first run with Q)
**Grid:** stop_pct=[0.15, 0.20, 0.25, 0.30] × rr=[1.5, 2.0] × be=[0, 10]
**Simulator:** v2 — BE stops do NOT count as daily losses
**Full report:** `docs/backtest_results/20260514_0001_2023-01-03_to_2026-05-13.md`

| # | Model | Stop | RR | BE | Win% | P&L | Net |
|---|-------|------|----|----|------|-----|-----|
| 1 | P: ORB Breakout + Retest | 0.25% | 1.5 | 0 | 34.4% | $11,955 | $11,413 |
| 2 | P: ORB Breakout + Retest | 0.25% | 1.5 | 10 | 52.4% | $6,641 | $10,109 |
| 3 | O: B+R + Trend + EMA | 0.30% | 2.0 | 10 | 52.6% | $5,918 | $8,408 |
| 4 | P: ORB Breakout + Retest | 0.25% | 2.0 | 0 | 26.9% | -$969 | $8,299 |

**Best per model (top 4):**

| Model | Stop | RR | BE | P&L | Net |
|-------|------|----|----|-----|-----|
| P: ORB Breakout + Retest | 0.25% | 1.5 | 0 | $11,955 | $11,413 |
| O: B+R + Trend + EMA | 0.30% | 2.0 | 10 | $5,918 | $8,408 |
| A: ORB Only | 0.30% | 1.5 | 0 | -$5,200 | $4,491 |
| G: Breakout + Retest | 0.25% | 1.5 | 0 | -$4,922 | $3,196 |

**Key observation:** P is now the clear 3.5yr leader ($11,413 net) — F dropped from $23,460 (v1) to $3,179 (v2) due to simulator change. O (B+R+Trend+EMA) emerged strongly at #2.

**⚠️ Warning — negative P&L with positive Net:** Several models show negative raw P&L but positive net (e.g., F: P&L=-$37k, Net=+$3k). This is technically possible because the LucidFlex eval simulation resets after each attempt — individual evals can pay out even when the long-run trading P&L is negative. **Do not trade any model with a large negative P&L regardless of Net — it means the model is losing money on actual trades and only collecting occasional eval payouts by luck.** Filter candidates by P&L > 0 first, then sort by Net.

---

## Model Reference

| Letter | Model Name | Signal Logic | Early Entry |
|--------|-----------|--------------|-------------|
| A | ORB Only | Close crosses ORH (long) or ORL (short) | No |
| B | All Key Levels | Close crosses PDH/PDL/PMH/PML/ORH/ORL/PDC | No |
| C | Key Levels + Cloud 1&2 | B + requires EMA 8/9 and 5/12 aligned | Yes |
| D | Key Levels + Cloud 3 | B + requires EMA 34/50 aligned | Yes |
| E | Key Levels + All Clouds | B + requires all 3 clouds aligned | Yes |
| F | Cloud Flip Near Key Level | Cloud 1+2 flips within 30pt of key level | Yes |
| G | Breakout + Retest | 3-state machine on all key levels | No |
| J | PDC Only | Close crosses previous day close only | No |
| K | Pre-Market Levels Only | Close crosses PMH/PML only | No |
| N | Breakout + Retest + EMA | G + requires EMA cloud aligned at entry | No |
| O | B+R + Trend + EMA | G + trend filter + EMA cloud aligned | No |
| P | ORB Breakout + Retest | 3-state machine on ORH/ORL only | No |
| Q | Cloud Flip + ORB Retest | F signals OR P signals (union) | Yes |

---

## Parameter Glossary

- **stop_pct**: Stop loss as % of entry price. 0.20% ≈ 58pt at MNQ 29k, ≈ 28pt at 14k. Use % not fixed points for era-comparable results across 2023–2026.
- **RR**: Take profit = entry ± stop × RR. RR=1.5 means 1.5× the risk distance.
- **BE (breakeven buffer)**: After price hits 1R, stop moves to entry + BE points. BE=0 means exact entry. BE=10 means 10pt profit locked.
- **be_ladder**: Tiered stop ladder (v2+). E.g. [(1.0, 0.5), (1.5, 1.0)] means: at 1R lock 0.5R; at 1.5R lock 1.0R. Not yet in param sweep — manual testing only.
- **Net**: LucidFlex 50k sim — $3k target, $2k trailing drawdown, $150 eval fee, 5 qualifying days (≥$150) for payout.
