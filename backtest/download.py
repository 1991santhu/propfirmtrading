"""
Data downloaders for /MNQ 5-minute bars.

Sources:
    yfinance   — free, max 60 days, no credentials needed (default)
    polygon    — $29/mo subscription, up to 10+ years, needs POLYGON_API_KEY env var
    tradovate  — free with account, up to several years, needs TRADOVATE_* env vars
    barchart   — requires manual CSV download from barchart.com (instructions below)

Usage:
    # yfinance (last 60 days, no auth)
    python -m backtest.download --source yfinance

    # Polygon.io (2+ years, needs POLYGON_API_KEY in .env)
    python -m backtest.download --source polygon --from 2024-01-01 --to 2025-12-31

    # Merge a Barchart CSV into the existing dataset
    python -m backtest.download --source barchart --barchart-file ~/Downloads/MNQ_5min.csv
"""
import asyncio
import os
import argparse
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

TICKER = "MNQ=F"
DEFAULT_OUT = os.path.join(os.path.dirname(__file__), "data", "MNQ_5min.csv")


# ─────────────────────────── yfinance ──────────────────────────────────────

def download_yfinance(out_path: str = DEFAULT_OUT, days: int = 60) -> pd.DataFrame:
    """Download up to 60 days of 5-min MNQ bars from Yahoo Finance (free, no auth)."""
    print(f"[yfinance] Downloading {days}-day 5-min {TICKER}...")
    ticker = yf.Ticker(TICKER)
    df = ticker.history(period=f"{days}d", interval="5m")

    if df.empty:
        raise RuntimeError(f"No data returned for {TICKER}. Check internet connection.")

    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low",
                             "Close": "close", "Volume": "volume"})
    df = df[["open", "high", "low", "close", "volume"]].copy()
    df.index = df.index.tz_convert("America/New_York").tz_localize(None)
    df.index.name = "time"
    df = df.between_time("04:00", "20:00")

    _save(df, out_path)
    return df


# ─────────────────────────── Databento ─────────────────────────────────────

def download_databento(
    out_path: str = DEFAULT_OUT,
    date_from: str = "2023-01-01",
    date_to: str | None = None,
    api_key: str | None = None,
) -> pd.DataFrame:
    """
    Download 5-min /MNQ bars from Databento (CME Globex official data).

    Free $10 credit on signup at databento.com — covers ~2 years of MNQ 5-min data.

    Steps to get your key:
      1. Sign up free at databento.com
      2. Go to databento.com/portal/settings/api-keys
      3. Copy your key and set DATABENTO_API_KEY in your .env file

    Symbol: MNQ.c.0  (continuous front-month MNQ)
    Dataset: GLBX.MDP3  (CME Globex)
    """
    try:
        import databento as db
    except ImportError:
        raise RuntimeError("Run: pip install databento")

    api_key = api_key or os.environ.get("DATABENTO_API_KEY")
    if not api_key:
        raise RuntimeError(
            "DATABENTO_API_KEY not set. Sign up free at databento.com, "
            "get your key from databento.com/portal/settings/api-keys, "
            "then add DATABENTO_API_KEY=your_key to your .env file."
        )

    date_to = date_to or datetime.now().strftime("%Y-%m-%d")
    print(f"[databento] Downloading MNQ.c.0 1-min bars {date_from} → {date_to} (will resample to 5-min)...")
    print("[databento] Checking cost estimate first...")

    client = db.Historical(key=api_key)

    # Cost estimate before downloading
    try:
        cost = client.metadata.get_cost(
            dataset="GLBX.MDP3",
            symbols=["MNQ.c.0"],
            schema="ohlcv-1m",
            start=date_from,
            end=date_to,
            stype_in="continuous",
        )
        print(f"[databento] Estimated cost: ${cost:.4f} (deducted from your free credit)")
    except Exception:
        pass  # cost estimate is optional

    data = client.timeseries.get_range(
        dataset="GLBX.MDP3",
        symbols=["MNQ.c.0"],
        schema="ohlcv-1m",
        start=date_from,
        end=date_to,
        stype_in="continuous",
    )

    df_1m = data.to_df()
    print(f"[databento] Got {len(df_1m):,} 1-min bars. Resampling to 5-min...")

    # Databento returns UTC timestamps — convert to ET
    df_1m.index = pd.to_datetime(df_1m.index, utc=True).tz_convert("America/New_York").tz_localize(None)
    df_1m = df_1m.rename(columns={"open": "open", "high": "high", "low": "low",
                                   "close": "close", "volume": "volume"})

    # Resample 1m → 5m
    df_5m = df_1m[["open", "high", "low", "close", "volume"]].resample("5min").agg({
        "open":   "first",
        "high":   "max",
        "low":    "min",
        "close":  "last",
        "volume": "sum",
    }).dropna()
    df_5m.index.name = "time"
    df_5m = df_5m.between_time("04:00", "20:00")

    print(f"[databento] {len(df_5m):,} 5-min bars after resampling.")
    _merge_and_save(df_5m, out_path)
    return df_5m


# ─────────────────────────── Polygon.io ────────────────────────────────────

POLYGON_BASE = "https://api.polygon.io"
POLYGON_TICKER = "X:MNQUSD"   # Polygon continuous MNQ futures ticker


def download_polygon(
    out_path: str = DEFAULT_OUT,
    date_from: str = "2024-01-01",
    date_to: str | None = None,
    api_key: str | None = None,
) -> pd.DataFrame:
    """
    Download 5-min /MNQ bars from Polygon.io.

    Requires POLYGON_API_KEY env var (or pass api_key directly).
    Polygon free tier doesn't include futures — needs Starter plan ($29/mo).

    Ticker: X:MNQUSD  (Polygon's continuous Micro Nasdaq futures)
    Docs:   https://polygon.io/docs/futures/get_v2_aggs_ticker__stocksticker__range__multiplier___timespan___from___to_

    Args:
        date_from: start date YYYY-MM-DD (can go back to 2018+)
        date_to:   end date YYYY-MM-DD (defaults to today)
    """
    import requests

    api_key = api_key or os.environ.get("POLYGON_API_KEY")
    if not api_key:
        raise RuntimeError(
            "POLYGON_API_KEY not set. Add it to your .env file.\n"
            "Get a key at https://polygon.io (Starter plan required for futures, $29/mo)"
        )

    date_to = date_to or datetime.now().strftime("%Y-%m-%d")
    print(f"[polygon] Downloading /MNQ 5-min bars {date_from} → {date_to}...")

    all_results: list[dict] = []
    url = (
        f"{POLYGON_BASE}/v2/aggs/ticker/{POLYGON_TICKER}/range/5/minute"
        f"/{date_from}/{date_to}"
    )
    params = {
        "adjusted":  "true",
        "sort":      "asc",
        "limit":     50000,
        "apiKey":    api_key,
    }

    while url:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 403:
            raise RuntimeError(
                "Polygon returned 403 Forbidden. "
                "Futures data requires Starter plan ($29/mo). "
                "Check your subscription at polygon.io/dashboard/subscriptions"
            )
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        all_results.extend(results)
        print(f"  fetched {len(all_results):,} bars so far...")

        # Polygon paginates via next_url
        url    = data.get("next_url")
        params = {"apiKey": api_key} if url else {}

    if not all_results:
        raise RuntimeError(f"No data returned from Polygon for {POLYGON_TICKER} {date_from}→{date_to}")

    # Polygon returns millisecond timestamps in UTC
    df = pd.DataFrame(all_results)
    df["time"] = pd.to_datetime(df["t"], unit="ms", utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    df = df[["time", "open", "high", "low", "close", "volume"]].set_index("time").sort_index()
    df.index.name = "time"
    df = df.between_time("04:00", "20:00")

    print(f"[polygon] Got {len(df):,} bars after market-hours filter.")
    _merge_and_save(df, out_path)
    return df


# ─────────────────────────── Tradovate ─────────────────────────────────────

TRADOVATE_DEMO_URL = "https://demo.tradovateapi.com/v1"
TRADOVATE_LIVE_URL = "https://live.tradovateapi.com/v1"

async def _tradovate_auth(base_url: str) -> str:
    import httpx
    payload = {
        "name":       os.environ["TRADOVATE_USERNAME"],
        "password":   os.environ["TRADOVATE_PASSWORD"],
        "appId":      os.environ.get("TRADOVATE_APP_ID",      "Sample App"),
        "appVersion": os.environ.get("TRADOVATE_APP_VERSION", "1.0"),
        "cid":        int(os.environ["TRADOVATE_CLIENT_ID"]),
        "sec":        os.environ["TRADOVATE_SECRET"],
        "deviceId":   os.environ.get("TRADOVATE_DEVICE_ID",  "backtest-downloader"),
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{base_url}/auth/accesstokenrequest", json=payload)
        resp.raise_for_status()
        token = resp.json().get("accessToken")
        if not token:
            raise RuntimeError(f"Tradovate auth failed: {resp.text}")
        return token


async def _tradovate_bars(
    token: str,
    base_url: str,
    symbol: str,
    start_dt: datetime,
    end_dt: datetime,
) -> list[dict]:
    """
    Fetch 5-min OHLCV bars from Tradovate's /md/getChart endpoint.
    Tradovate returns up to ~5000 bars per call; we page with startTime.
    """
    import httpx
    headers = {"Authorization": f"Bearer {token}"}
    all_bars: list[dict] = []
    cursor = start_dt

    async with httpx.AsyncClient(timeout=30) as client:
        while cursor < end_dt:
            payload = {
                "symbol":        symbol,
                "chartDescription": {
                    "underlyingType": "MinuteBar",
                    "elementSize":    5,
                    "elementSizeUnit": "UnderlyingUnits",
                    "withHistogram": False,
                },
                "timeRange": {
                    "asMuchAsElements": 5000,
                    "closestTimestamp": cursor.strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
            }
            resp = await client.post(
                f"{base_url}/md/getChart", json=payload, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()

            charts = data.get("charts", [])
            if not charts:
                break

            bars = charts[0].get("bars", [])
            if not bars:
                break

            all_bars.extend(bars)
            # Advance cursor past the last bar timestamp
            last_ts = bars[-1]["timestamp"]
            cursor = datetime.strptime(last_ts, "%Y-%m-%dT%H:%M:%SZ") + timedelta(minutes=5)

            if len(bars) < 100:
                break  # reached the end

    return all_bars


def _tradovate_bars_to_df(bars: list[dict]) -> pd.DataFrame:
    records = []
    for b in bars:
        ts = pd.to_datetime(b["timestamp"]).tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
        records.append({
            "time":   ts,
            "open":   b["open"],
            "high":   b["high"],
            "low":    b["low"],
            "close":  b["close"],
            "volume": b.get("upVolume", 0) + b.get("downVolume", 0),
        })
    df = pd.DataFrame(records).set_index("time").sort_index()
    df = df.between_time("04:00", "20:00")
    return df


async def _download_tradovate_async(
    out_path: str,
    days: int,
    symbol: str,
    use_live: bool,
) -> pd.DataFrame:
    base_url = TRADOVATE_LIVE_URL if use_live else TRADOVATE_DEMO_URL
    print(f"[tradovate] Authenticating with {'live' if use_live else 'demo'} API...")
    token = await _tradovate_auth(base_url)

    end_dt   = datetime.utcnow()
    start_dt = end_dt - timedelta(days=days)
    print(f"[tradovate] Fetching {days} days of 5-min bars for {symbol}...")
    bars = await _tradovate_bars(token, base_url, symbol, start_dt, end_dt)
    print(f"[tradovate] Retrieved {len(bars)} raw bars.")

    if not bars:
        raise RuntimeError("No bars returned from Tradovate.")

    df = _tradovate_bars_to_df(bars)
    _merge_and_save(df, out_path)
    return df


def download_tradovate(
    out_path: str = DEFAULT_OUT,
    days: int = 730,
    symbol: str = "MNQM5",   # front-month contract; update as contracts roll
    use_live: bool = True,
) -> pd.DataFrame:
    """
    Download historical 5-min MNQ bars from Tradovate API.

    Requires env vars: TRADOVATE_USERNAME, TRADOVATE_PASSWORD,
                       TRADOVATE_CLIENT_ID, TRADOVATE_SECRET

    symbol: use the front-month contract (e.g. MNQM5 for June 2025).
            Tradovate doesn't support continuous contracts like Yahoo does —
            you'll need to stitch multiple contract CSVs for multi-year history.
            Roll schedule: March(H), June(M), Sept(U), Dec(Z).
    """
    return asyncio.run(_download_tradovate_async(out_path, days, symbol, use_live))


# ─────────────────────────── Barchart manual ───────────────────────────────

def import_barchart(barchart_file: str, out_path: str = DEFAULT_OUT) -> pd.DataFrame:
    """
    Merge a manually-downloaded Barchart CSV into the master dataset.

    How to get the file:
      1. Go to https://www.barchart.com/futures/quotes/MNQ*1/historical-download
      2. Log in (free account OK for 1 year)
      3. Select: Interval = 5-minute, Date range = up to 1 year
      4. Click Export CSV
      5. Pass the downloaded file path to this function.
    """
    print(f"[barchart] Importing {barchart_file}...")
    raw = pd.read_csv(barchart_file)

    # Barchart columns: Symbol,Time,Open,High,Low,Last,Change,%Chg,Volume,Open Int
    raw.columns = [c.strip() for c in raw.columns]
    time_col = "Time" if "Time" in raw.columns else raw.columns[1]
    df = raw.rename(columns={
        time_col: "time",
        "Open": "open", "High": "high", "Low": "low",
        "Last": "close", "Volume": "volume",
    })
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df[["open", "high", "low", "close", "volume"]].copy()
    df.index.name = "time"

    # Barchart times are already ET for US futures
    df = df.between_time("04:00", "20:00")

    _merge_and_save(df, out_path)
    return df


# ─────────────────────────── helpers ───────────────────────────────────────

def _save(df: pd.DataFrame, out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_csv(out_path)
    print(f"Saved {len(df)} bars ({df.index[0]} → {df.index[-1]}) → {out_path}")


def _merge_and_save(new_df: pd.DataFrame, out_path: str) -> None:
    """Merge new bars with existing CSV (dedup by timestamp, keep new values)."""
    if os.path.exists(out_path):
        existing = pd.read_csv(out_path, index_col=0, parse_dates=True)
        combined = pd.concat([existing, new_df])
        combined = combined[~combined.index.duplicated(keep="last")].sort_index()
        print(f"Merged: {len(existing)} existing + {len(new_df)} new = {len(combined)} total bars.")
        _save(combined, out_path)
    else:
        _save(new_df, out_path)


# ─────────────────────────── CLI ───────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download /MNQ 5-min historical data")
    parser.add_argument("--source",        default="yfinance",
                        choices=["yfinance", "databento", "polygon", "tradovate", "barchart"])
    parser.add_argument("--out",           default=DEFAULT_OUT)
    parser.add_argument("--days",          type=int, default=60,
                        help="Days of history (yfinance max 60, tradovate up to ~730)")
    parser.add_argument("--symbol",        default="MNQM5",
                        help="Tradovate contract symbol (default: MNQM5 = June 2025)")
    parser.add_argument("--live",          action="store_true",
                        help="Use Tradovate live API (default: demo)")
    parser.add_argument("--barchart-file", default=None,
                        help="Path to Barchart CSV export file")
    parser.add_argument("--date-from",   dest="date_from", default=None,
                        help="Start date for Polygon download, e.g. 2024-01-01")
    parser.add_argument("--date-to",     dest="date_to",   default=None,
                        help="End date for Polygon download, e.g. 2025-12-31")
    parser.add_argument("--polygon-key",   default=None,
                        help="Polygon API key (or set POLYGON_API_KEY in .env)")
    parser.add_argument("--databento-key", default=None,
                        help="Databento API key (or set DATABENTO_API_KEY in .env)")
    args = parser.parse_args()

    if args.source == "yfinance":
        download_yfinance(out_path=args.out, days=min(args.days, 60))

    elif args.source == "databento":
        key = os.environ.get("DATABENTO_API_KEY") or args.databento_key
        download_databento(
            out_path=args.out,
            date_from=args.date_from or "2023-01-01",
            date_to=args.date_to,
            api_key=key,
        )

    elif args.source == "polygon":
        key = os.environ.get("POLYGON_API_KEY") or args.polygon_key
        download_polygon(
            out_path=args.out,
            date_from=args.date_from or "2024-01-01",
            date_to=args.date_to,
            api_key=key,
        )

    elif args.source == "tradovate":
        for var in ["TRADOVATE_USERNAME", "TRADOVATE_PASSWORD",
                    "TRADOVATE_CLIENT_ID", "TRADOVATE_SECRET"]:
            if not os.environ.get(var):
                raise SystemExit(f"Missing env var: {var}. Fill in your .env file first.")
        download_tradovate(
            out_path=args.out, days=args.days,
            symbol=args.symbol, use_live=args.live,
        )

    elif args.source == "barchart":
        if not args.barchart_file:
            raise SystemExit("--barchart-file required for barchart source")
        import_barchart(args.barchart_file, out_path=args.out)
