import pandas as pd
import numpy as np
from datetime import time as dtime

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

def add_key_levels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate key price levels for each bar and store them as columns.
    Must be called before filter_rth() — needs pre-market data.

    Adds columns (NaN if not yet available for that bar):
    - orh: Opening Range High (max high 9:30-10:00 AM, valid after 10:00 AM)
    - orl: Opening Range Low (min low 9:30-10:00 AM, valid after 10:00 AM)
    - pdh: Previous Day High (RTH high of prior trading day)
    - pdl: Previous Day Low (RTH low of prior trading day)
    - pmh: Pre-Market High (4:00-9:30 AM high of current day)
    - pml: Pre-Market Low (4:00-9:30 AM low of current day)
    """
    df = df.copy()
    for col in ['orh', 'orl', 'pdh', 'pdl', 'pmh', 'pml', 'pdc']:
        df[col] = np.nan

    df['_date'] = df.index.date
    dates = sorted(df['_date'].unique())

    prev_rth_high = None
    prev_rth_low = None
    prev_rth_close = None

    for date in dates:
        day_mask = df['_date'] == date

        # OR window: 9:30-10:00 AM (exclusive of 10:00)
        or_mask = day_mask & (
            pd.Series(df.index.time, index=df.index) >= dtime(9, 30)
        ) & (
            pd.Series(df.index.time, index=df.index) < dtime(10, 0)
        )

        # Post-OR RTH: 10:00 AM onwards (where OR levels are valid)
        post_or_mask = day_mask & (
            pd.Series(df.index.time, index=df.index) >= dtime(10, 0)
        )

        # Full RTH: 9:30-16:00
        rth_mask = day_mask & (
            pd.Series(df.index.time, index=df.index) >= dtime(9, 30)
        ) & (
            pd.Series(df.index.time, index=df.index) < dtime(16, 0)
        )

        # Pre-market: 4:00-9:30
        pm_mask = day_mask & (
            pd.Series(df.index.time, index=df.index) >= dtime(4, 0)
        ) & (
            pd.Series(df.index.time, index=df.index) < dtime(9, 30)
        )

        # OR levels (valid after 10:00 AM)
        if or_mask.any():
            orh = df.loc[or_mask, 'high'].max()
            orl = df.loc[or_mask, 'low'].min()
            df.loc[post_or_mask, 'orh'] = orh
            df.loc[post_or_mask, 'orl'] = orl

        # Previous day levels (valid all RTH)
        if prev_rth_high is not None:
            df.loc[rth_mask, 'pdh'] = prev_rth_high
            df.loc[rth_mask, 'pdl'] = prev_rth_low
            df.loc[rth_mask, 'pdc'] = prev_rth_close

        # Pre-market levels (valid all RTH)
        if pm_mask.any():
            df.loc[rth_mask, 'pmh'] = df.loc[pm_mask, 'high'].max()
            df.loc[rth_mask, 'pml'] = df.loc[pm_mask, 'low'].min()

        # Save RTH high/low/close for next day
        if rth_mask.any():
            prev_rth_high  = df.loc[rth_mask, 'high'].max()
            prev_rth_low   = df.loc[rth_mask, 'low'].min()
            prev_rth_close = df.loc[rth_mask, 'close'].iloc[-1]

    df = df.drop(columns=['_date'])
    return df


def add_ema_clouds(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add EMA cloud columns used by strategies as filters.
    - ema8, ema9, ema5, ema12 (Cloud 1 & 2 — fast, entry signal)
    - ema34, ema50 (Cloud 3 — slow, trend filter)
    - cloud1_green, cloud2_green, cloud3_green
    - both_green (Cloud1 & Cloud2), both_red (~Cloud1 & ~Cloud2)
    """
    df = df.copy()
    src = (df['high'] + df['low']) / 2  # hl2

    df['ema8']  = src.ewm(span=8,  adjust=False).mean()
    df['ema9']  = src.ewm(span=9,  adjust=False).mean()
    df['ema5']  = src.ewm(span=5,  adjust=False).mean()
    df['ema12'] = src.ewm(span=12, adjust=False).mean()
    df['ema34'] = src.ewm(span=34, adjust=False).mean()
    df['ema50'] = src.ewm(span=50, adjust=False).mean()

    df['cloud1_green'] = df['ema8']  > df['ema9']
    df['cloud2_green'] = df['ema5']  > df['ema12']
    df['cloud3_green'] = df['ema34'] > df['ema50']
    df['both_green']   = df['cloud1_green'] & df['cloud2_green']
    df['both_red']     = ~df['cloud1_green'] & ~df['cloud2_green']

    return df


def add_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add EMA columns and signal columns to dataframe.
    Matches Ripster EMA Clouds: source=hl2, EMA pairs 8/9 and 5/12.

    Adds columns:
    - hl2: (high + low) / 2
    - ema8, ema9, ema5, ema12, ema34, ema50
    - cloud1_green: ema8 > ema9
    - cloud2_green: ema5 > ema12
    - cloud3_green: ema34 > ema50
    - both_green: cloud1_green & cloud2_green
    - both_red: ~cloud1_green & ~cloud2_green
    - long_signal: both_green & ~both_green.shift(1)   (transition bar)
    - short_signal: both_red & ~both_red.shift(1)       (transition bar)
    """
    df = add_ema_clouds(df)
    df['long_signal']  = df['both_green'] & ~df['both_green'].shift(1).fillna(False)
    df['short_signal'] = df['both_red']   & ~df['both_red'].shift(1).fillna(False)
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
