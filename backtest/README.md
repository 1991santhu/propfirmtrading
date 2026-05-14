# Backtest Module

Backtests prop firm trading strategies on historical /MNQ 5-minute data.  
Simulates LucidFlex eval + funded rules (profit target, consistency rule, trailing drawdown).

---

## 1. Download Historical Data

Uses yfinance (free, ~60 days of 5-min bars).

```bash
python -m backtest.download --days 60 --out backtest/data/MNQ_5min.csv
```

The CSV is saved with columns: `datetime, open, high, low, close, volume` in `America/New_York` timezone.

---

## 2. Run a Single Backtest

```bash
python -m backtest.run backtest/data/MNQ_5min.csv <contracts> <stop_points>

# Example: 5 contracts, 60-point stop, default 2R
python -m backtest.run backtest/data/MNQ_5min.csv 5 60
```

Output: trade list, daily PnL, eval simulation result.

---

## 3. Run the Parameter Optimizer

Sweeps all combinations of strategies × stop sizes × R:R ratios × contracts × daily loss limits.

```bash
python -m backtest.optimizer backtest/data/MNQ_5min.csv
python -m backtest.optimizer backtest/data/MNQ_5min.csv --top 30
```

Default grid (1,920 combinations with 12 strategies):
- Stop points: 20, 30, 40, 50, 60
- R:R ratios: 1.5, 2.0, 2.5, 3.0
- Contracts: 3, 5
- Max daily losses: 1, 2
- Re-entry: True / False

Results are ranked by `net profit = payouts - eval fees`.

**Latest best result (70-day dataset):**
```
Strategy G: Breakout + Retest | No Re-entry | Stop=60pts | R:R=2.0 | 5 contracts → Net $5,222
```

---

## 4. Strategies

| ID | Name | Logic |
|----|------|-------|
| A | ORB Only | Long on ORH break, short on ORL break |
| B | All Key Levels | ORH/ORL + PDH/PDL/PDC + PMH/PML |
| C | Key Levels + Cloud 1&2 | Level break + EMA8/9 and EMA5/12 green/red |
| D | Key Levels + Cloud 3 | Level break + EMA34/50 trend filter |
| E | Key Levels + All Clouds | Level break + all 3 EMA cloud agreement |
| F | Cloud Flip Near Level | EMA cloud transition within 30pts of key level |
| G | Breakout + Retest | 3-state: break → retest → re-break (best performer) |
| H | Morning Only | All key levels, 9:30–11:30 AM only |
| I | Afternoon Only | All key levels, 1:00–3:30 PM only |
| J | PDC Only | Only Previous Day Close level |
| K | Pre-Market Only | Only PMH/PML levels |
| L | ORB + Cloud3 Trend | ORH/ORL break with EMA34/50 trend filter |

### Key Levels Used

| Level | Source | Description |
|-------|--------|-------------|
| `orh` / `orl` | 9:30–10:00 AM | Opening Range High / Low |
| `pdh` / `pdl` | Previous RTH day | Previous Day High / Low |
| `pdc` | Previous RTH day | Previous Day Close |
| `pmh` / `pml` | 4:00–9:30 AM | Pre-Market High / Low |

---

## 5. Add a New Strategy

1. Create `backtest/strategies/my_strategy.py`:

```python
from backtest.strategies.base import BaseStrategy
import pandas as pd

class MyStrategy(BaseStrategy):
    name = "X: My Strategy"

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        return self._level_break_signals(
            df,
            long_levels=["orh", "pdh"],
            short_levels=["orl", "pdl"],
            reentry=reentry,
        )
```

2. Register in `backtest/strategies/__init__.py`:

```python
from backtest.strategies.my_strategy import MyStrategy
ALL_STRATEGIES = [..., MyStrategy()]
```

3. Re-run the optimizer — it picks up all strategies automatically.

---

## 6. LucidFlex Prop Firm Simulation

The optimizer calls `simulate_lucid_flex()` for each parameter combo.

**Eval rules simulated:**
- Profit target: $3,000
- EOD trailing drawdown: $2,000 max loss from high-water mark
- Consistency rule: no single day > 50% of running profit total

**Funded rules simulated:**
- Need 5 qualifying days (each ≥ $150 profit)
- Payout = min(90% × profit since last reset, $2,000)

---

## 7. Data Pipeline Internals

```
load_csv(path)
  └── add_key_levels(df)      ← MUST run on full data (needs pre-market bars)
        └── add_ema_clouds(df)
              └── filter_rth(df)   ← keeps only 9:30-16:20 bars
                    └── strategy.generate_signals(df)
                          └── simulate_trades(df_signals, ...)
                                └── simulate_lucid_flex(day_stats)
```

**Important:** `add_key_levels()` must be called before `filter_rth()` because it needs 4:00–9:30 AM pre-market bars to compute PMH/PML.

---

## 8. Interpreting Results

| Column | Meaning |
|--------|---------|
| `Win%` | Percentage of winning trades |
| `P&L` | Raw PnL from trades ($2/point × contracts) |
| `Evals` | `passed/attempted` over dataset period |
| `Payouts` | Total payout dollars received |
| `Net` | Payouts minus eval fees (the real number) |
| `StopDays` | Days bot was stopped early (hit daily loss limit) |

A high `StopDays` count means the strategy hits the loss limit often — bad for consistency rule compliance.

---

## 9. Getting More Data

yfinance only provides ~60 days of 5-min bars for free.  
For longer backtests (6-12 months needed for reliable eval pass rate estimates):

- **Tradovate API** — free with account, provides historical bars via REST. Build downloader once you have API credentials.
- **Polygon.io** — paid ($29/mo Starter tier), provides futures bars via REST.
- **Rithmic** — institutional data feed, requires broker account.
