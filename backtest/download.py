import os
import argparse
import pandas as pd
import yfinance as yf

TICKER = "MNQ=F"   # Yahoo Finance continuous MNQ futures contract
DEFAULT_OUT = os.path.join(os.path.dirname(__file__), "data", "MNQ_5min.csv")

def download_mnq(out_path: str = DEFAULT_OUT, days: int = 60) -> pd.DataFrame:
    """
    Download up to 60 days of 5-min /MNQ bars from Yahoo Finance.
    Yahoo Finance free tier limit: 60 days of intraday data.
    Saves CSV to out_path and returns the DataFrame.
    """
    print(f"Downloading {days}-day 5-min {TICKER} data from Yahoo Finance...")
    ticker = yf.Ticker(TICKER)
    df = ticker.history(period=f"{days}d", interval="5m")

    if df.empty:
        raise RuntimeError(f"No data returned for {TICKER}. Check your internet connection.")

    # Normalise columns
    df = df.rename(columns={
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Volume": "volume"
    })
    df = df[["open", "high", "low", "close", "volume"]].copy()

    # Strip timezone from index so it saves cleanly and load_csv can parse it
    df.index = df.index.tz_convert("America/New_York").tz_localize(None)
    df.index.name = "time"

    # Drop pre/post market rows outside 04:00-20:00 (keep extended + RTH)
    df = df.between_time("04:00", "20:00")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_csv(out_path)

    print(f"Saved {len(df)} bars ({df.index[0]} → {df.index[-1]})")
    print(f"Output: {out_path}")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download /MNQ 5-min data from Yahoo Finance")
    parser.add_argument("--out",  default=DEFAULT_OUT, help="Output CSV path")
    parser.add_argument("--days", type=int, default=60, help="Days of history (max 60 for free tier)")
    args = parser.parse_args()
    download_mnq(out_path=args.out, days=args.days)
