# Strategy Reference Guide

All strategies trade /MNQ (Micro Nasdaq futures) on 5-minute bars during RTH (9:30–16:20 ET).
Each strategy inherits from `BaseStrategy` and implements `generate_signals(df)` which adds
`long_signal` and `short_signal` boolean columns to the dataframe.

The simulator then takes those signals and manages all trade execution, stop loss, take profit,
breakeven moves, and daily loss limits.

---

## How the Simulator Works (Common to All Strategies)

```
Signal bar close → Entry price
Entry price - stop_points → Hard Stop Loss (SL)
Entry price + stop_points → 1R trigger (BE move)
Entry price + stop_points × rr_ratio → Take Profit (TP)

After price hits 1R:
  Stop moves to → entry + be_buffer_points (e.g. entry+10)
  This locks in a small profit if price reverses

Daily limits:
  max_daily_losses=2 → bot stops after 2 full stop-outs
  max_daily_trades=5 → hard cap (rarely hit, signal fires ~1.7x/day)
  no_first_30min=True → no entries before 10:00 AM ET (opening range)

Cloud-flip exit (optional):
  If long and EMA cloud flips bearish (both_red=True) → exit at close
  if short and EMA cloud flips bullish (both_green=True) → exit at close
  Only fires if exit price is better than the hard SL (reduces loss, never adds to it)
```

**Point value:** $2/point/contract. With 5 contracts:
- Full SL (60pt): -$600 gross (-$605.90 after commission)
- Full TP (2R=120pt): +$1,200 gross (+$1,194.10 after commission)
- BE stop (10pt): +$100 gross (+$94.10 after commission)

---

## Key Levels Used by Strategies

Calculated by `add_key_levels()` for each trading day:

| Level | Meaning | When available |
|-------|---------|----------------|
| **ORH** | Opening Range High — max high 9:30–10:00 AM | After 10:00 AM |
| **ORL** | Opening Range Low — min low 9:30–10:00 AM | After 10:00 AM |
| **PDH** | Previous Day High — RTH high of prior day | All day |
| **PDL** | Previous Day Low — RTH low of prior day | All day |
| **PMH** | Pre-Market High — 4:00–9:30 AM high | All day |
| **PML** | Pre-Market Low — 4:00–9:30 AM low | All day |
| **PDC** | Previous Day Close — last RTH close of prior day | All day |

---

## EMA Clouds (Ripster-style)

Calculated by `add_ema_clouds()` on `hl2 = (high+low)/2`:

| Cloud | EMAs | State |
|-------|------|-------|
| Cloud 1 (fast) | EMA 8 vs EMA 9 | `cloud1_green = ema8 > ema9` |
| Cloud 2 (fast) | EMA 5 vs EMA 12 | `cloud2_green = ema5 > ema12` |
| Cloud 3 (slow) | EMA 34 vs EMA 50 | `cloud3_green = ema34 > ema50` |
| **both_green** | Cloud 1 AND Cloud 2 green | Strong bullish momentum |
| **both_red** | Cloud 1 AND Cloud 2 red | Strong bearish momentum |

---

## Strategy A: ORB Only

**File:** `backtest/strategies/orb_only.py`

**What it does:** Trades the classic Opening Range Breakout. After 10:00 AM, if price closes above the ORH (Opening Range High), fire a long signal. If price closes below the ORL (Opening Range Low), fire a short signal. Maximum one signal per day (whichever direction breaks first).

**Signal logic:**
```
After 10:00 AM, for each bar:
  if prev_close <= ORH < close  →  long_signal = True  (breakout above OR high)
  if prev_close >= ORL > close  →  short_signal = True (breakdown below OR low)
  Once fired, done for the day (one trade max)
```

**Why it works:** The opening range (9:30–10:00) sets the day's equilibrium. A clean close above/below it signals institutional commitment to a direction. Simple, no discretion required.

**Strengths:**
- Best long-term performer: $17,250 net / 3.5 years ($421/month)
- Only 1 signal/day — very selective, high signal quality
- 30% eval pass rate (best of all strategies)
- Clean, objective, no ambiguity

**Weaknesses:**
- On days without a clear break, generates no trade ($0 for the day)
- Only 677 trades over 3.5 years (~0.8/day)
- 33% win rate (relies on TP being large enough to overcome SL losses)

**Best config:** 60pt stop, 2R, be_buffer=0 → $17,250 net

---

## Strategy B: All Key Levels

**File:** `backtest/strategies/key_levels.py`

**What it does:** Fires a signal whenever the EMA cloud direction aligns with price touching any of the 7 key levels (PDH, PDL, ORH, ORL, PMH, PML, PDC). Long when `both_green` near a long level, short when `both_red` near a short level.

**Signal logic:**
```
For each bar:
  if both_green AND (close near PDH or ORH or PMH or PDC)  →  long_signal
  if both_red  AND (close near PDL or ORL or PML or PDC)   →  short_signal
  "near" = within a configurable tolerance (default 5pts)
```

**Why it works:** Key levels are where institutional orders cluster (prior day high/low, opening range, pre-market extremes). When the EMA cloud also agrees with the direction, the probability of a reaction increases.

**Strengths:**
- More signals than ORB (~3–4/day possible)
- Uses multiple confluences (level + cloud)

**Weaknesses:**
- Very noisy — fires on ALL levels, so gets many signals on busy days
- Long-term net only $10,442 vs ORB's $17,250
- Higher blown account rate (more trades = more drawdown risk)

**Best config:** 60pt stop, 2R, be_buffer=0 → $10,442 net

---

## Strategy C: Key Levels + Cloud 1&2

**File:** `backtest/strategies/kl_cloud12.py`

**What it does:** Same as Strategy B. Uses `cloud1_green & cloud2_green` explicitly instead of `both_green`. Since `both_green = cloud1_green & cloud2_green`, the result is identical to B.

**Note:** This strategy is effectively a duplicate of B. It was created to separate the filter explicitly, but produces the same signals. Best config: 60pt, 1.5R, be_buffer=0 → $2,210 net (lower due to different optimal RR).

---

## Strategy D: Key Levels + Cloud 3

**File:** `backtest/strategies/kl_cloud3.py`

**What it does:** Key level touch + Cloud 3 (slow trend: EMA 34 vs EMA 50) filter. Only takes a signal if the slow trend cloud agrees. This is a slower, more selective version of B.

**Signal logic:**
```
Long:  price near long level  AND  cloud3_green (ema34 > ema50)
Short: price near short level AND  NOT cloud3_green (ema34 < ema50)
```

**Why it works:** Cloud 3 (34/50 EMA) represents the medium-term trend. Only taking signals aligned with the medium trend filters out counter-trend traps.

**Strengths:**
- #4 overall: $13,810 net / 3.5yr
- Fewer trades than B, higher quality
- 37% win rate (vs B's 31%)

**Best config:** 60pt stop, 1.5R, be_buffer=0 → $13,810 net

---

## Strategy E: Key Levels + All Clouds

**File:** `backtest/strategies/kl_all_clouds.py`

**What it does:** Key level touch + ALL THREE clouds must agree (Cloud 1, 2, and 3). The strictest of the key level family.

**Signal logic:**
```
Long:  near long level  AND  cloud1_green AND cloud2_green AND cloud3_green
Short: near short level AND NOT cloud1_green AND NOT cloud2_green AND NOT cloud3_green
```

**Strengths:** Very few false signals when all three clouds agree.

**Weaknesses:** Misses many valid moves because Cloud 3 is slow to turn. Only $7,754 net (worse than D which only requires Cloud 3).

---

## Strategy F: Cloud Flip Near Key Level

**File:** `backtest/strategies/cloud_at_level.py`

**What it does:** Fires on the TRANSITION bar when both fast EMA clouds FLIP direction (both_green becomes True, or both_red becomes True) AND price is within tolerance of any key level.

**Signal logic:**
```
Long:  both_green is True NOW  AND  was False PREVIOUS BAR  AND  near any long level
Short: both_red  is True NOW  AND  was False PREVIOUS BAR  AND  near any short level
```

**Why it was built:** The cloud flip is the earliest momentum signal. Catching the EXACT bar when momentum turns, at a key level, should be a high-probability entry.

**Why it doesn't work well:** In practice, clouds flip dozens of times per day (27 long + 8 short signals today alone). Most flips near levels are noise. **This strategy generates too many signals and should not be used without additional filters.** Net: only $2,173 over 3.5 years.

---

## Strategy G: Breakout + Retest

**File:** `backtest/strategies/breakout_retest.py`

**What it does:** The most selective and sophisticated signal. Uses a 3-state machine per key level per day. A signal only fires after THREE events happen in sequence: (1) breakout through level, (2) retest back to level, (3) re-breakout away from level.

**Signal logic (per level, per day):**
```
State 1 — Watching:
  If close crosses above level (prev_close ≤ level < close) → State 2 (Armed)

State 2 — Armed (level broken, waiting for retest):
  If low touches level within tolerance (low ≤ level + 5pts) → State 3 (Retested)

State 3 — Retested (price pulled back to level, waiting for continuation):
  If close moves back above level → long_signal=True
  (Goes back to State 1 or done for this level)
```

**Why it works:** The breakout-retest-continuation pattern is one of the most reliable in technical analysis. The level acts as support/resistance. Price breaks it, retests it (clearing weak hands), then continues. The 3-state machine ensures all three conditions are met before entering.

**Strengths:**
- Best performer in recent 6 months: $6,119 net
- Current market regime (high volatility, trending) favors it
- Works on all 4 long levels (ORH, PDH, PMH, PDC) and 4 short levels

**Weaknesses:**
- 19.7% eval pass rate (harder to pass evaluations than ORB)
- More trades = more commissions = more blown accounts
- Long-term: only #5 at $12,359 net

**Best config:** 60pt stop, 2R, be_buffer=10 → $12,359 net

---

## Strategy H: Morning Only (9:30–11:30)

**File:** `backtest/strategies/morning_only.py`

**What it does:** Takes the same signals as Strategy B (All Key Levels) but filters to ONLY the first 2 hours of the session (9:30–11:30 ET). After 11:30, no new entries.

**Why it was built:** The morning session has the most volume, volatility, and follow-through. Many traders prefer morning-only trading.

**Result:** $5,634 net — worse than afternoon-only and much worse than full-day ORB. The morning signals are noisy (opening volatility).

---

## Strategy I: Afternoon Only (13:00–15:30)

**File:** `backtest/strategies/afternoon_only.py`

**What it does:** Same signals as B but only from 13:00–15:30 ET (New York afternoon session, post-lunch).

**Why it was built:** Afternoon often has cleaner, lower-noise trends as the day's direction is established.

**Result:** $6,031 net — slightly better than morning-only.

---

## Strategy J: PDC Only

**File:** `backtest/strategies/pdc_only.py`

**What it does:** Same 3-state machine as Strategy G (Breakout+Retest) but ONLY watches the Previous Day Close (PDC) level. Ignores all other levels.

**Why it was built:** PDC is often the most watched level of the day — where institutions set their directional bias. A PDC breakout+retest is a high-conviction signal.

**Result:** $11,979 net — surprisingly strong for such a simple single-level strategy. Confirms PDC is a high-quality level.

---

## Strategy K: Pre-Market Levels Only

**File:** `backtest/strategies/premarket_only.py`

**What it does:** Uses the All Key Levels approach (Strategy B) but only watches PMH (Pre-Market High) and PML (Pre-Market Low). EMA cloud confirmation required.

**Why it was built:** Pre-market highs/lows often become the day's key support/resistance — they represent where price traded before the main session and where trapped positions exist.

**Strengths:** #2 overall at $15,339 net / 3.5 years ($374/month). Very strong result for a 2-level strategy.

**Best config:** 60pt stop, 1.5R, be_buffer=10 → $15,339 net

---

## Strategy L: ORB + Cloud3 Trend

**File:** `backtest/strategies/orb_cloud3.py`

**What it does:** ORB signal (same as A) + Cloud 3 filter (slow EMA 34/50 must agree with direction). Only takes the ORB long if Cloud 3 is also bullish, and only takes ORB short if Cloud 3 is bearish.

**Why it was built:** Add a trend filter to ORB to avoid counter-trend trades.

**Result:** $11,142 net — worse than raw ORB ($17,250). The Cloud 3 filter removes some bad trades but also many good ones.

---

## Strategy M: Breakout + Retest + Trend

**File:** `backtest/strategies/breakout_retest_trend.py`

**What it does:** Strategy G + daily trend filter. Uses the 20-day SMA of daily closes to determine the macro trend. Long signals only when price is above the daily SMA20; short signals only when below.

**Signal logic:**
```
G signals generated first, then:
  long_signal  = G_long_signal  AND  (close > daily_sma20)
  short_signal = G_short_signal AND  (close < daily_sma20)
```

**Why it works:** Filters out counter-trend trades on a daily timeframe. On today's bullish day (above SMA20), all shorts were blocked — and that's exactly what saved M from the losing 9:45 short that hurt G.

**Best in recent 6 months:** #2 at $5,491 net. Long-term: $9,719 net.

---

## Strategy N: Breakout + Retest + EMA

**File:** `backtest/strategies/breakout_retest_ema.py`

**What it does:** Strategy G + EMA cloud filter at the signal bar. Long only when `both_green` is True on the signal bar; short only when `both_red` is True.

**Signal logic:**
```
G signals generated first, then:
  long_signal  = G_long_signal  AND  both_green
  short_signal = G_short_signal AND  both_red
```

**Why it was built:** The EMA cloud confirms momentum is aligned with the signal direction at entry. A breakout+retest long that also has green EMA clouds is a stronger signal.

**Strengths:** #3 overall at $15,079 net — excellent. Combines the structural precision of G with cloud momentum confirmation.

**Best config:** 60pt stop, 1.5R, be_buffer=10 → $15,079 net

---

## Strategy O: Breakout + Retest + Trend + EMA

**File:** `backtest/strategies/breakout_retest_trend_ema.py`

**What it does:** Strategy G + daily trend filter (from M) + EMA cloud filter (from N). All three conditions required simultaneously.

**Signal logic:**
```
G signals generated first, then:
  long_signal  = G_long AND both_green AND (close > daily_sma20)
  short_signal = G_short AND both_red  AND (close < daily_sma20)
```

**Why it was built:** The strictest breakout+retest variant. Triple confirmation: structural level break, EMA momentum, and macro trend alignment.

**Today's performance:** +$1,288 — best performer on May 13. Both trades won.

**Tradeoff:** Very few signals (~0.8/day) and $6,123 net long-term (less than G or N alone) because filtering out too many signals also removes profitable ones.

---

## Summary Table

| ID | Strategy | Signal Type | Filters | Avg Signals/Day | Net/3.5yr | Net/mo |
|----|----------|-------------|---------|-----------------|-----------|--------|
| A | ORB Only | Level break | None | 0.8 | $17,250 | $421 |
| B | All Key Levels | Level touch + cloud | EMA fast clouds | ~3 | $10,442 | $255 |
| C | KL + Cloud 1&2 | Level touch | EMA fast clouds | ~3 | $2,210 | $54 |
| D | KL + Cloud 3 | Level touch | EMA slow cloud | ~2 | $13,810 | $337 |
| E | KL + All Clouds | Level touch | All 3 clouds | ~1.5 | $7,754 | $189 |
| F | Cloud Flip @ Level | Cloud transition | Level proximity | ~5 ⚠️ | $2,173 | $53 |
| G | Breakout + Retest | 3-state machine | None | 1.7 | $12,359 | $302 |
| H | Morning Only | Level touch | Time: 9:30–11:30 | ~2 | $5,634 | $137 |
| I | Afternoon Only | Level touch | Time: 13:00–15:30 | ~1 | $6,031 | $147 |
| J | PDC Only | 3-state machine | PDC level only | 0.6 | $11,979 | $292 |
| K | Pre-Market Levels | Level touch + cloud | PMH/PML only | ~1.2 | $15,339 | $374 |
| L | ORB + Cloud3 | Level break | EMA slow cloud | 0.6 | $11,142 | $272 |
| M | B+R + Trend | 3-state machine | Daily SMA20 | 1.2 | $9,719 | $237 |
| N | B+R + EMA | 3-state machine | EMA fast clouds | 1.1 | $15,079 | $368 |
| O | B+R + Trend + EMA | 3-state machine | Daily SMA + EMA | 0.8 | $6,123 | $149 |

---

## New Simulator Features (as of May 2026)

### No First 30 Minutes (`no_first_30min=True`)
Blocks all new entries before 10:00 AM ET. The opening 30 minutes form the Opening Range
and are extremely volatile — signals frequently get whipsawed within 1–2 bars. This rule
skips entry on signals that fire between 9:30–9:59 AM. Exits of existing positions are
NOT affected.

### Cloud Flip Exit (`cloud_flip_exit=True`)
When in a long position and the EMA cloud flips to `both_red`, exit at the bar close
ONLY if that close is above the hard stop loss. This reduces the loss size compared to
waiting for the full SL. Similarly, when short and cloud flips `both_green`, exit early
if the close is below the hard SL. Does not trigger after the 1R BE move (the BE stop
is already protecting profit at that point).

---

## Data Pipeline

```
backtest/data/MNQ_5min.csv          153,567 bars, Jan 2023–May 2026
         ↓
load_csv()                          Parse timestamps, lowercase columns
         ↓
add_key_levels()                    Compute ORH/ORL/PDH/PDL/PMH/PML/PDC/ATR14/SMA20
         ↓
add_ema_clouds()                    Compute EMA 5/8/9/12/34/50, cloud states
         ↓
filter_rth()                        Keep 9:30–16:20 ET only
         ↓
strategy.generate_signals()         Add long_signal / short_signal columns
         ↓
simulate_trades()                   Execute trades, enforce all rules
         ↓
simulate_lucid_flex()               Model eval → funded → payout cycle
```
