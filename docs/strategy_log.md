# Strategy Performance Log

Running bookkeeping of every param study run. Each entry has a unique Run ID,
exactly what changed from the previous run, and the top results. This lets you
compare apples to apples and understand WHY results differ.

**Instrument:** /MNQ, $2/point, 5 contracts
**Prop firm sim:** LucidFlex 50k — $3k target, $2k EOD trailing drawdown, $150 eval fee, 5 qualifying days (≥$150) needed for payout
**Net** = total payouts collected − total eval fees paid (what you actually pocket from prop firm)
**P&L** = raw sum of all trade profits/losses (your actual trading edge, ignoring prop firm math)

> ⚠️ **Only trust models where BOTH P&L > 0 AND Net > 0.**
> A model with negative P&L but positive Net is profiting from the prop firm eval structure
> (occasional good streaks collect payouts; losses are capped at $150 per eval attempt).
> This is NOT a real trading edge and will not work in a live funded account long-term.

---

## Simulator Versions

| Version | Key Behavior | Used In |
|---------|-------------|---------|
| **v1** | BE stop at breakeven counts as a daily loss (uses daily-loss limit) | R1, R2 |
| **v2** | BE stop at breakeven does NOT count as a daily loss — only hard SL exits count | R3, R4 |
| **v2 + accurate LucidFlex** | Same as v2; prop firm sim rewritten with real MLL lock, 50% payout cap, max 5 payouts, balance tracking, zero-payout refunds | R5, R6 |

**Why this matters:** Cloud-heavy models (F, C, D, E, Q) fire many signals per day.
In v1, BE stops ate into the 2-loss daily limit, so these models were forced to stop early —
keeping only their best trades. In v2, BE stops are "free", so they keep taking trades all day
including lower-quality late-session entries. This caused F's 3.5yr P&L to swing from
+$51,689 (v1) to -$37,414 (v2) — same market data, different simulator rule.

**Bottom line:** v1 and v2 results are NOT directly comparable for BE-heavy models.
This is the main reason numbers look completely different between runs.

---

## Model Reference

| Letter | Model Name | Signal Type | Early Entry |
|--------|-----------|-------------|-------------|
| A | ORB Only | Close crosses ORH/ORL | No |
| B | All Key Levels | Close crosses PDH/PDL/PMH/PML/ORH/ORL/PDC | No |
| C | Key Levels + Cloud 1&2 | B + EMA 8/9 and 5/12 aligned | Yes |
| D | Key Levels + Cloud 3 | B + EMA 34/50 aligned | Yes |
| E | Key Levels + All Clouds | B + all 3 clouds aligned | Yes |
| F | Cloud Flip Near Key Level | Cloud 1+2 flips within 30pt of key level | Yes |
| G | Breakout + Retest | 3-state machine on all key levels | No |
| J | PDC Only | Close crosses previous day close | No |
| K | Pre-Market Levels Only | Close crosses PMH/PML | No |
| N | Breakout + Retest + EMA | G + EMA cloud aligned at entry | No |
| O | B+R + Trend + EMA | G + trend filter + EMA cloud | No |
| P | ORB Breakout + Retest | 3-state machine on ORH/ORL only | No |
| Q | Cloud Flip + ORB Retest | F signals OR P signals (union) | Yes |

---

## Run Log

---

### R1 — 2026-05-13 23:27 | Simulator: v1 | Period: 6 months

**Period:** 2025-11-13 → 2026-05-13
**Models active:** A B C D E F G J K N O P (12 — Q not yet created)
**What changed from previous run:** First run using % stops (0.15/0.20/0.25/0.30% of entry price). Previous runs used fixed 60pt stop which is era-biased — 60pt is 0.43% at 2023 prices vs 0.21% at 2026 prices.
**Grid:** stop_pct=[0.15, 0.20, 0.25, 0.30] × rr=[1.5, 2.0] × be=[0, 10] × max_trades=[5]
**Full report:** `docs/backtest_results/20260513_2327_2025-11-13_to_2026-05-13.md`

#### Top 4 Overall (by Net)

| # | Model | Stop | RR | BE | P&L | Net |
|---|-------|------|----|----|-----|-----|
| 1 | P: ORB Breakout + Retest | 0.20% | 1.5 | 0 | $15,586 | $7,761 |
| 2 | P: ORB Breakout + Retest | 0.20% | 1.5 | 10 | $15,478 | $7,638 |
| 3 | P: ORB Breakout + Retest | 0.20% | 2.0 | 10 | $17,569 | $5,941 |
| 4 | P: ORB Breakout + Retest | 0.20% | 2.0 | 0 | $16,912 | $5,624 |

#### Best Config Per Model (top 4 models by Net)

| Model | Stop | RR | BE | P&L | Net |
|-------|------|----|----|-----|-----|
| P: ORB Breakout + Retest | 0.20% | 1.5 | 0 | $15,586 | **$7,761** |
| F: Cloud Flip Near Key Level | 0.15% | 1.5 | 10 | $21,196 | **$4,650** |
| B: All Key Levels | 0.25% | 2.0 | 0 | $5,375 | **$4,492** |
| G: Breakout + Retest | 0.25% | 1.5 | 10 | $14,730 | **$4,306** |

**Key finding:** P is the clear 6mo winner. F is competitive with a tight 0.15% stop. All top models have positive P&L — no red flags.

---

### R2 — 2026-05-13 23:31 | Simulator: v1 | Period: 3.5 years

**Period:** 2023-01-03 → 2026-05-13
**Models active:** A B C D E F G J K N O P (12 — Q not yet created)
**What changed from R1:** Same simulator and grid, different time period (3.5yr vs 6mo). First era-comparable 3.5yr run.
**Grid:** stop_pct=[0.15, 0.20, 0.25, 0.30] × rr=[1.5, 2.0] × be=[0, 10] × max_trades=[5]
**Full report:** `docs/backtest_results/20260513_2331_2023-01-03_to_2026-05-13.md`

#### Top 4 Overall (by Net)

| # | Model | Stop | RR | BE | P&L | Net |
|---|-------|------|----|----|-----|-----|
| 1 | F: Cloud Flip Near Key Level | 0.15% | 1.5 | 10 | $51,689 | $23,460 |
| 2 | P: ORB Breakout + Retest | 0.20% | 2.0 | 0 | $31,165 | $19,399 |
| 3 | P: ORB Breakout + Retest | 0.20% | 1.5 | 0 | $26,590 | $18,173 |
| 4 | P: ORB Breakout + Retest | 0.25% | 1.5 | 0 | $31,714 | $17,267 |

#### Best Config Per Model (top 4 models by Net)

| Model | Stop | RR | BE | P&L | Net |
|-------|------|----|----|-----|-----|
| F: Cloud Flip Near Key Level | 0.15% | 1.5 | 10 | $51,689 | **$23,460** |
| P: ORB Breakout + Retest | 0.20% | 2.0 | 0 | $31,165 | **$19,399** |
| B: All Key Levels | 0.15% | 1.5 | 10 | $25,906 | **$15,001** |
| D: Key Levels + Cloud 3 | 0.25% | 1.5 | 0 | $15,041 | **$14,794** |

**Key finding:** F leads over the full 3.5yr period with high signal volume + tight stop. P still strong. Both P&L and Net positive for all 4 — these have real trading edge.

---

### R3 — 2026-05-13 23:57 | Simulator: v2 | Period: 6 months

**Period:** 2025-11-13 → 2026-05-13
**Models active:** A B C D E F G J K N O P Q (13 — Q added: Cloud Flip + ORB Retest = F signals OR P signals)
**What changed from R2:**
  1. **Simulator upgraded to v2** — BE stops no longer count as daily losses
  2. **Model Q added** (Cloud Flip + ORB Retest, combining F and P signal logic)
**Grid:** stop_pct=[0.15, 0.20, 0.25, 0.30] × rr=[1.5, 2.0] × be=[0, 10] × max_trades=[5]
**Full report:** `docs/backtest_results/20260513_2357_2025-11-13_to_?.md`

#### Top 4 Overall (by Net)

| # | Model | Stop | RR | BE | P&L | Net |
|---|-------|------|----|----|-----|-----|
| 1 | P: ORB Breakout + Retest | 0.25% | 1.5 | 10 | $19,935 | $5,664 |
| 2 | O: B+R + Trend + EMA | 0.30% | 2.0 | 0 | $1,992 | $2,950 |
| 3 | G: Breakout + Retest | 0.25% | 1.5 | 0 | $11,128 | $2,650 |
| 4 | A: ORB Only | 0.25% | 2.0 | 10 | -$6,736 | $2,500 ⚠️ |

#### Best Config Per Model (top 4 models by Net, P&L positive only)

| Model | Stop | RR | BE | P&L | Net |
|-------|------|----|----|-----|-----|
| P: ORB Breakout + Retest | 0.25% | 1.5 | 10 | $19,935 | **$5,664** |
| O: B+R + Trend + EMA | 0.30% | 2.0 | 0 | $1,992 | **$2,950** |
| G: Breakout + Retest | 0.25% | 1.5 | 0 | $11,128 | **$2,650** |
| F: Cloud Flip Near Key Level | 0.15% | 1.5 | 10 | $5,003 | **$1,319** |

**Key finding:** P remains strongest in 6mo. F dropped sharply (v1→v2 simulator change freed up daily trade slots, causing more late-session low-quality entries). Q (F+P) landed 6th — adding F signals to P dilutes P's selectivity.

**⚠️ Do not compare R3 to R1 directly for F, C, D, E, Q — results changed due to simulator v1→v2, not market data.**

---

### R4 — 2026-05-14 00:01 | Simulator: v2 | Period: 3.5 years

**Period:** 2023-01-03 → 2026-05-13
**Models active:** A B C D E F G J K N O P Q (13 — same as R3)
**What changed from R3:** Same simulator and grid, extended to full 3.5yr period.
**Grid:** stop_pct=[0.15, 0.20, 0.25, 0.30] × rr=[1.5, 2.0] × be=[0, 10] × max_trades=[5]
**Full report:** `docs/backtest_results/20260514_0001_2023-01-03_to_2026-05-13.md`

#### Top 4 Overall (by Net)

| # | Model | Stop | RR | BE | P&L | Net |
|---|-------|------|----|----|-----|-----|
| 1 | P: ORB Breakout + Retest | 0.25% | 1.5 | 0 | $11,955 | $11,413 |
| 2 | P: ORB Breakout + Retest | 0.25% | 1.5 | 10 | $6,641 | $10,109 |
| 3 | O: B+R + Trend + EMA | 0.30% | 2.0 | 10 | $5,918 | $8,408 |
| 4 | P: ORB Breakout + Retest | 0.25% | 2.0 | 0 | -$969 | $8,299 ⚠️ |

#### Best Config Per Model (top 4 models by Net, P&L positive only)

| Model | Stop | RR | BE | P&L | Net |
|-------|------|----|----|-----|-----|
| P: ORB Breakout + Retest | 0.25% | 1.5 | 0 | $11,955 | **$11,413** |
| O: B+R + Trend + EMA | 0.30% | 2.0 | 10 | $5,918 | **$8,408** |
| F: Cloud Flip Near Key Level | 0.15% | 1.5 | 10 | -$37,414 | $3,179 ⚠️ negative P&L |
| G: Breakout + Retest | 0.25% | 1.5 | 0 | -$4,922 | $3,196 ⚠️ negative P&L |

**Key finding:** With v2 simulator, P and O are the only 2 models with both positive P&L AND positive Net over 3.5yr. F lost its 3.5yr lead — the simulator change exposed that F's 2020-era dominance depended on the BE-stops-as-losses rule acting as a quality filter.

**⚠️ Do not compare R4 to R2 directly for F, C, D, E, Q — same reason as R3 vs R1.**

---

### R5 — 2026-05-14 00:48 | Simulator: v2 + Accurate LucidFlex | Period: 3.5 years

**Period:** 2023-01-03 → 2026-05-13
**Models active:** A B C D E F G J K N O P Q (13 — same as R4)
**What changed from R4:** **Prop firm simulation rewritten** — `backtest/lucid_flex.py` replaces old `prop_firm.py`.
New sim correctly models: real balance tracking (payouts reduce balance), MLL lock at $50,100 when balance > $52,100
or on first payout, 50% of cycle profit cap (not 90%), max 5 payouts per funded account → live review,
zero-payout blows get eval fee refunded. Old sim was missing all of this.
**Grid:** stop_pct=[0.20, 0.25, 0.30] × rr=[1.5, 2.0] × be=[0, 10] × max_trades=[5]
**Full report:** `docs/backtest_results/20260514_0048_2023-01-03_to_2026-05-13.md`

#### Top 4 Overall (by Net, P&L positive only)

| # | Model | Stop | RR | BE | P&L | Net |
|---|-------|------|----|----|-----|-----|
| 1 | P: ORB Breakout + Retest | 0.30% | 2.0 | 0 | $6,846 | $8,025 |
| 2 | P: ORB Breakout + Retest | 0.25% | 1.5 | 0 | $11,955 | $5,810 |
| 3 | O: B+R + Trend + EMA | 0.30% | 2.0 | 0 | $11,413 | $5,268 |
| 4 | P: ORB Breakout + Retest | 0.30% | 1.5 | 10 | $5,055 | $4,804 |

#### Best Config Per Model (top 3 models by Net, P&L positive only)

| Model | Stop | RR | BE | P&L | Net |
|-------|------|----|----|-----|-----|
| P: ORB Breakout + Retest | 0.30% | 2.0 | 0 | $6,846 | **$8,025** |
| O: B+R + Trend + EMA | 0.30% | 2.0 | 0 | $11,413 | **$5,268** |
| G: Breakout + Retest | 0.30% | 2.0 | 0 | $5,078 | **$513** |

**Key finding:** Accurate LucidFlex sim significantly reduces net profit vs old sim (P dropped from $11,413→$5,810 on same params/data). Max 5 payouts per funded account is the main driver. P and O remain the only models with both P&L > 0 and Net > 0. G barely positive. All cloud-heavy models (B, C, D, E, F, Q, N) negative Net over 3.5yr.

---

### R6 — 2026-05-14 00:45 | Simulator: v2 + Accurate LucidFlex | Period: 6 months

**Period:** 2025-11-01 → 2026-05-13
**Models active:** A B C D E F G J K N O P Q (13 — same as R5)
**What changed from R5:** Same simulator, shorter time window (6mo vs 3.5yr). Note: R6 uses 2025-11-01 start vs R3's 2025-11-13 start — slightly longer window.
**Grid:** stop_pct=[0.20, 0.25, 0.30] × rr=[1.5, 2.0] × be=[0, 10] × max_trades=[5]
**Full report:** `docs/backtest_results/20260514_0045_2025-11-01_to_2026-05-13.md`

#### Top 4 Overall (by Net, P&L positive only)

| # | Model | Stop | RR | BE | P&L | Net |
|---|-------|------|----|----|-----|-----|
| 1 | P: ORB Breakout + Retest | 0.25% | 1.5 | 0 | $20,041 | $4,397 |
| 2 | G: Breakout + Retest | 0.25% | 1.5 | 0 | $13,401 | $3,434 |
| 3 | P: ORB Breakout + Retest | 0.25% | 1.5 | 10 | $21,811 | $3,423 |
| 4 | P: ORB Breakout + Retest | 0.30% | 2.0 | 10 | $22,474 | $3,159 |

#### Best Config Per Model (top 3 models by Net, P&L positive only)

| Model | Stop | RR | BE | P&L | Net |
|-------|------|----|----|-----|-----|
| P: ORB Breakout + Retest | 0.25% | 1.5 | 0 | $20,041 | **$4,397** |
| G: Breakout + Retest | 0.25% | 1.5 | 0 | $13,401 | **$3,434** |
| O: B+R + Trend + EMA | 0.30% | 2.0 | 0 | $6,634 | **$1,888** |

**Key finding:** 6mo period is very hot (MNQ bull run Nov 2025–May 2026). G performs surprisingly well short-term. P remains #1 across all configs. Q (Cloud Flip + ORB Retest) appears at #15 overall (net=$1,500) but with negative P&L — not a real edge.

---

## Summary Across All Runs — Consistent Winners

Models that appear in the top 4 (by Net, P&L positive) in ALL comparable runs:

| Model | R1 6mo v1 | R2 3.5yr v1 | R3 6mo v2 | R4 3.5yr v2 | R5 3.5yr accurate | R6 6mo accurate | Verdict |
|-------|-----------|-------------|-----------|-------------|-------------------|-----------------|---------|
| P: ORB Breakout + Retest | ✅ #1 | ✅ #2 | ✅ #1 | ✅ #1 | ✅ #1 | ✅ #1 | **Most consistent — all 6 runs** |
| O: B+R + Trend + EMA | — | — | ✅ #2 | ✅ #2 | ✅ #2 | ✅ #3 | Strong in v2 |
| G: Breakout + Retest | ✅ #4 | — | ✅ #3 | ⚠️ neg P&L | ✅ #3 (barely) | ✅ #2 | Good short-term, marginal 3.5yr |
| F: Cloud Flip | ✅ #2 | ✅ #1 | ✅ #4 | ⚠️ neg P&L | ⚠️ neg Net | ⚠️ neg Net | v1 only reliable |
| B: All Key Levels | ✅ #3 | ✅ #3 | — | — | ⚠️ neg Net | ⚠️ neg Net | Weak in v2 accurate sim |

**R4 vs R5 (same params, same data — only prop firm simulation changed):**
Model P 0.25%/rr=1.5/be=0: Net dropped from **$11,413** (old sim) → **$5,810** (accurate sim).
This is the real number. Old sim allowed unlimited payouts; accurate sim caps at 5 payouts per funded account.

**Current recommendation (v2 simulator + accurate LucidFlex, forward-looking):**
- **Primary:** Model P at 0.25% stop, RR=1.5, BE=0 (3.5yr: $11,955 P&L / $5,810 Net)
- **Secondary:** Model O at 0.30% stop, RR=2.0, BE=0 (3.5yr: $11,413 P&L / $5,268 Net)
- **Pending:** be_ladder test on P and O — not yet run in any backtest

---

## Parameter Glossary

| Term | Meaning |
|------|---------|
| stop_pct | Stop loss as % of entry price. Use % not fixed points — MNQ moved from 14k (2023) to 29k (2026) so fixed points are era-biased. 0.20% ≈ 28pt at 14k, ≈ 58pt at 29k. |
| RR | Risk:Reward ratio. TP = entry ± stop × RR. RR=1.5 means you target 1.5× your risk distance. |
| BE | Breakeven buffer. After price hits 1R profit, stop moves to entry + BE points. BE=0 = exact entry. BE=10 = 10pt profit locked in. |
| be_ladder | Tiered stop ladder (v2 simulator). e.g. [(1.0, 0.5), (1.5, 1.0)] = at 1R lock 0.5R; at 1.5R lock 1.0R. Not yet in param sweep — pending manual test. |
| Net | Payouts received − eval fees paid. What you actually pocket from the prop firm. |
| P&L | Raw trading profit/loss summed across all trades. Your actual trading edge. Must be positive. |
