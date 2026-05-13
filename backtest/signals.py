import pandas as pd
import numpy as np

def load_csv(filepath: str) -> pd.DataFrame:
    """
    Load TradingView CSV export.
    Expected columns: time, open, high, low, close, Volume
    TradingView exports time as "YYYY-MM-DD HH:MM:SS" in exchange timezone.
    Returns DataFrame with DatetimeIndex in UTC, columns: open, high, low, close, volume
    """
    df = pd.read_csv(filepath)
    df.columns = [c.lower() for c in df.columns]
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    if "volume" not in df.columns and "vol" in df.columns:
        df = df.rename(columns={"vol": "volume"})
    return df[["open", "high", "low", "close", "volume"]].copy()

def add_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add EMA columns and signal columns to dataframe.
    Matches Ripster EMA Clouds: source=hl2, EMA pairs 8/9 and 5/12.

    Adds columns:
    - hl2: (high + low) / 2
    - ema8, ema9, ema5, ema12
    - cloud1_green: ema8 > ema9
    - cloud2_green: ema5 > ema12
    - both_green: cloud1_green & cloud2_green
    - both_red: ~cloud1_green & ~cloud2_green
    - long_signal: both_green & ~both_green.shift(1)   (transition bar)
    - short_signal: both_red & ~both_red.shift(1)       (transition bar)
    """
    df = df.copy()
    df["hl2"] = (df["high"] + df["low"]) / 2

    # EMA using pandas ewm — span=N gives same result as TradingView EMA(N)
    df["ema8"]  = df["hl2"].ewm(span=8,  adjust=False).mean()
    df["ema9"]  = df["hl2"].ewm(span=9,  adjust=False).mean()
    df["ema5"]  = df["hl2"].ewm(span=5,  adjust=False).mean()
    df["ema12"] = df["hl2"].ewm(span=12, adjust=False).mean()

    df["cloud1_green"] = df["ema8"] > df["ema9"]
    df["cloud2_green"] = df["ema5"] > df["ema12"]
    df["both_green"]   = df["cloud1_green"] & df["cloud2_green"]
    df["both_red"]     = ~df["cloud1_green"] & ~df["cloud2_green"]

    # Transition bars only (first bar where condition becomes true)
    df["long_signal"]  = df["both_green"] & ~df["both_green"].shift(1).fillna(False)
    df["short_signal"] = df["both_red"]   & ~df["both_red"].shift(1).fillna(False)

    return df

def filter_rth(df: pd.DataFrame, tz: str = "America/New_York") -> pd.DataFrame:
    """
    Keep only bars within Regular Trading Hours: 09:30 - 16:20 ET.
    The index must be timezone-aware or convertible.
    """
    if df.index.tz is None:
        # Assume index is in ET (TradingView exports in exchange tz for futures)
        df = df.copy()
        df.index = df.index.tz_localize(tz, ambiguous="infer", nonexistent="shift_forward")
    else:
        df = df.copy()
        df.index = df.index.tz_convert(tz)

    rth_start = pd.Timestamp("09:30").time()
    rth_cutoff = pd.Timestamp("16:20").time()  # 10 min before bot close
    mask = (df.index.time >= rth_start) & (df.index.time <= rth_cutoff)
    return df[mask]
