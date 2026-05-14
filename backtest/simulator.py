from dataclasses import dataclass, field
from datetime import time as dtime
from typing import List, Optional
import pandas as pd

@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    side: str          # "long" or "short"
    entry_price: float
    exit_price: float
    contracts: int
    stop_points: float  # actual points used (may be derived from % of price)
    exit_reason: str   # "tp", "sl", "be_stop", "eod", "daily_limit"
    pnl: float         # total P&L in dollars

    @property
    def points(self) -> float:
        if self.side == "long":
            return self.exit_price - self.entry_price
        return self.entry_price - self.exit_price

@dataclass
class DayStats:
    date: str
    trades: int = 0
    losses: int = 0
    pnl: float = 0.0
    stopped_early: bool = False  # hit daily loss limit

def simulate_trades(
    df: pd.DataFrame,
    contracts: int = 3,
    stop_points: int = 30,
    stop_pct: float | None = None,    # if set, overrides stop_points: stop = entry * stop_pct/100
    point_value: float = 2.0,         # $2 per point per MNQ contract
    max_daily_losses: int = 2,
    max_daily_trades: int = 5,
    rr_ratio: float = 2.0,            # R:R multiplier for take profit
    be_buffer_points: int = 0,        # after hitting 1R, stop moves to entry + this many points
    commission_per_side: float = 0.59, # $ per contract per side (Tradovate all-in ~$0.59)
    min_range_pts: float = 0,          # skip day if prev_day_range < this (range filter)
    no_first_30min: bool = False,      # if True, skip all entries before 10:00 AM ET
    cloud_flip_exit: bool = False,     # if True, exit long when both_red flips True (and vice versa)
                                       # only triggers when exit price is better than the SL
) -> tuple[List[Trade], List[DayStats]]:
    """
    Simulate all trades from signal dataframe.

    Stop sizing (pick one):
      stop_points  — fixed absolute points, e.g. 60. Simple but not comparable across
                     price eras (14k MNQ vs 29k MNQ). Use only for current-era testing.
      stop_pct     — percentage of entry price, e.g. 0.20 → 40pts at 20k, 58pts at 29k.
                     Use this for multi-year backtests so results are era-comparable.

    Commissions: commission_per_side × contracts × 2 (entry + exit) deducted from each trade.
      Tradovate all-in for MNQ: ~$0.59/contract/side (exchange + clearing + NFA + platform).
      Set to 0 to disable.

    Range filter: min_range_pts skips an entire trading day if the previous day's RTH
      high-low range was below this threshold. On low-range days, a 60pt stop + 120pt TP
      physically cannot both fit within the day's expected range.
      Recommended: 150 pts (= 2.5× stop at 60pt). Set 0 to disable.

    be_buffer_points=0  → stop moves to exact entry ($0 if stopped at BE)
    be_buffer_points=10 → stop moves to entry+10pts (lock in small profit at 1R)

    no_first_30min=True → blocks all new entries before 10:00 AM ET. The opening
      30 minutes (9:30-10:00) form the Opening Range and are highly volatile —
      signals fired here are frequently whipsawed within 1-2 bars.

    cloud_flip_exit=True → if in a long and the EMA cloud flips to both_red, exit
      at the bar close ONLY if that close is better than the hard SL (i.e. we're
      cutting the loss smaller, not adding to it). Same logic inverted for shorts.
      Requires both_green/both_red columns in df (from add_ema_clouds).

    Returns (trades, day_stats).
    """
    trades: List[Trade] = []
    day_stats: List[DayStats] = []

    # Group by date
    df = df.copy()
    df["date"] = df.index.date

    commission_rt = commission_per_side * 2  # round-trip cost per contract

    for date, day_df in df.groupby("date"):
        # Daily range filter: skip day if previous day range was too small
        if min_range_pts > 0 and "prev_day_range" in day_df.columns:
            prev_range = day_df["prev_day_range"].iloc[0]
            if not pd.isna(prev_range) and prev_range < min_range_pts:
                day_stats.append(DayStats(date=str(date)))  # record as empty day
                continue

        day = DayStats(date=str(date))
        in_position = False
        entry_price = 0.0
        entry_time = None
        side = ""
        be_moved = False
        trade_stop_pts: float = stop_points  # actual stop used for this trade

        for ts, row in day_df.iterrows():
            if in_position:
                comm = commission_rt * contracts  # total round-trip commission this trade

                if side == "long":
                    current_stop = entry_price + be_buffer_points if be_moved else entry_price - trade_stop_pts
                    tp_price = entry_price + trade_stop_pts * rr_ratio
                    be_trigger = entry_price + trade_stop_pts * 1.0

                    if row["high"] >= tp_price:
                        exit_price = tp_price
                        pnl = (exit_price - entry_price) * contracts * point_value - comm
                        trades.append(Trade(entry_time, ts, "long", entry_price, exit_price,
                                           contracts, trade_stop_pts, "tp", pnl))
                        day.pnl += pnl
                        day.trades += 1
                        in_position = False
                        be_moved = False
                        continue

                    if row["low"] <= current_stop:
                        exit_price = current_stop
                        pnl = (exit_price - entry_price) * contracts * point_value - comm
                        reason = "be_stop" if be_moved else "sl"
                        trades.append(Trade(entry_time, ts, "long", entry_price, exit_price,
                                           contracts, trade_stop_pts, reason, pnl))
                        day.pnl += pnl
                        day.trades += 1
                        if not be_moved:
                            day.losses += 1
                        in_position = False
                        be_moved = False
                        continue

                    if not be_moved and row["high"] >= be_trigger:
                        be_moved = True

                    # Cloud-flip early exit: clouds turned bearish while we're long
                    # Only exit if close is still above SL (cutting loss smaller, not adding)
                    if cloud_flip_exit and not be_moved:
                        if row.get("both_red", False) and row["close"] > current_stop:
                            exit_price = row["close"]
                            pnl = (exit_price - entry_price) * contracts * point_value - comm
                            trades.append(Trade(entry_time, ts, "long", entry_price, exit_price,
                                               contracts, trade_stop_pts, "cloud_flip", pnl))
                            day.pnl += pnl
                            day.trades += 1
                            if pnl < 0:
                                day.losses += 1
                            in_position = False
                            be_moved = False
                            continue

                else:  # short
                    current_stop = entry_price - be_buffer_points if be_moved else entry_price + trade_stop_pts
                    tp_price = entry_price - trade_stop_pts * rr_ratio
                    be_trigger = entry_price - trade_stop_pts * 1.0

                    if row["low"] <= tp_price:
                        exit_price = tp_price
                        pnl = (entry_price - exit_price) * contracts * point_value - comm
                        trades.append(Trade(entry_time, ts, "short", entry_price, exit_price,
                                           contracts, trade_stop_pts, "tp", pnl))
                        day.pnl += pnl
                        day.trades += 1
                        in_position = False
                        be_moved = False
                        continue

                    if row["high"] >= current_stop:
                        exit_price = current_stop
                        pnl = (entry_price - exit_price) * contracts * point_value - comm
                        reason = "be_stop" if be_moved else "sl"
                        trades.append(Trade(entry_time, ts, "short", entry_price, exit_price,
                                           contracts, trade_stop_pts, reason, pnl))
                        day.pnl += pnl
                        day.trades += 1
                        if not be_moved:
                            day.losses += 1
                        in_position = False
                        be_moved = False
                        continue

                    if not be_moved and row["low"] <= be_trigger:
                        be_moved = True

                    # Cloud-flip early exit: clouds turned bullish while we're short
                    if cloud_flip_exit and not be_moved:
                        if row.get("both_green", False) and row["close"] < current_stop:
                            exit_price = row["close"]
                            pnl = (entry_price - exit_price) * contracts * point_value - comm
                            trades.append(Trade(entry_time, ts, "short", entry_price, exit_price,
                                               contracts, trade_stop_pts, "cloud_flip", pnl))
                            day.pnl += pnl
                            day.trades += 1
                            if pnl < 0:
                                day.losses += 1
                            in_position = False
                            be_moved = False
                            continue

            # Check if we should stop trading today
            if day.losses >= max_daily_losses:
                day.stopped_early = True
                break
            if day.trades >= max_daily_trades:
                break

            # New entry on signal
            if not in_position:
                # No-first-30min rule: skip entries before 10:00 AM
                if no_first_30min and ts.time() < dtime(10, 0):
                    continue

                if row["long_signal"]:
                    in_position = True
                    entry_price = row["close"]
                    entry_time = ts
                    side = "long"
                    be_moved = False
                    # Compute stop size: percentage takes priority over fixed points
                    trade_stop_pts = round(entry_price * stop_pct / 100, 1) if stop_pct else stop_points
                elif row["short_signal"]:
                    in_position = True
                    entry_price = row["close"]
                    entry_time = ts
                    side = "short"
                    be_moved = False
                    trade_stop_pts = round(entry_price * stop_pct / 100, 1) if stop_pct else stop_points

        # EOD: force close any open position
        if in_position and day_df is not None and len(day_df) > 0:
            last_row = day_df.iloc[-1]
            exit_price = last_row["close"]
            comm = commission_rt * contracts
            pnl = (exit_price - entry_price if side == "long" else entry_price - exit_price) * contracts * point_value - comm
            trades.append(Trade(entry_time, day_df.index[-1], side, entry_price, exit_price,
                               contracts, trade_stop_pts, "eod", pnl))
            day.pnl += pnl
            day.trades += 1

        day_stats.append(day)

    return trades, day_stats
