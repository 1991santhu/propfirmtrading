# Backtest Data

## Option 1 — Auto-download via Yahoo Finance (free, no account needed)

Downloads up to 60 days of 5-min /MNQ data automatically:

    source venv/bin/activate
    python -m backtest.download
    python -m backtest.run backtest/data/MNQ_5min.csv 3 30

Optional flags:
    python -m backtest.download --days 30 --out backtest/data/MNQ_5min.csv

## Option 2 — TradingView CSV export (requires paid plan)

1. Open TradingView → search `/MNQ1!` (continuous contract)
2. Set timeframe to 5 minutes, scroll left to load max history
3. Chart menu → "Export chart data..." → save as `backtest/data/MNQ_5min.csv`
4. Run: `python -m backtest.run backtest/data/MNQ_5min.csv 3 30`

## Notes

- Yahoo Finance free tier: max 60 days of 5-min intraday data
- Data is the continuous /MNQ futures contract (MNQ=F)
- RTH filtering (09:30-16:20 ET) is applied automatically by the backtest
