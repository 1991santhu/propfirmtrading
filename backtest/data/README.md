# How to Download /MNQ 5-Minute Data from TradingView

## Steps

1. Open TradingView (tradingview.com) and log in
2. Search for `/MNQ` or `MNQ1!` (Micro E-mini Nasdaq-100 futures, continuous contract)
3. Set the chart timeframe to **5 minutes** (click the timeframe selector at the top)
4. Scroll back as far as possible to maximize history:
   - Free plan: ~1 month
   - Essential plan: ~2 years (recommended)
   - Premium plan: up to 10+ years
5. Click the **"..."** (three dots) menu at the top right of the chart
6. Select **"Export chart data"**
7. In the dialog, choose **CSV** format and click **Download**
8. Rename the file to `MNQ_5min.csv` and save it in this directory (`backtest/data/`)

## Expected CSV Format

TradingView exports data in this format:

```
time,open,high,low,close,Volume
2024-01-02 09:30:00,16750.25,16780.50,16740.00,16765.75,12345
2024-01-02 09:35:00,16765.75,16790.25,16758.00,16782.00,9876
...
```

- **time**: Timestamp in exchange timezone (US Eastern for /MNQ)
- **open/high/low/close**: Price in index points
- **Volume**: Contract volume

## Running the Backtest

Once your CSV is in place, run from the project root:

```bash
cd /Users/ssomarapu/propfirm_trading
source venv/bin/activate

# Default: 3 contracts, 30-point stop
python -m backtest.run backtest/data/MNQ_5min.csv

# Custom: 5 contracts, 60-point stop
python -m backtest.run backtest/data/MNQ_5min.csv 5 60
```

## Notes

- The backtest filters to RTH only (09:30-16:20 ET) automatically
- Timestamps are localized to America/New_York if not already timezone-aware
- The EMA signals replicate the Ripster EMA Clouds (hl2 source, pairs 8/9 and 5/12)
