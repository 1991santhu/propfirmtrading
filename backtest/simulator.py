from dataclasses import dataclass, field
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
    stop_points: int
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
    point_value: float = 2.0,       # $2 per point per MNQ contract
    max_daily_losses: int = 2,
    max_daily_trades: int = 5,
) -> tuple[List[Trade], List[DayStats]]:
    """
    Simulate all trades from signal dataframe.
    Uses fixed_2r exit: stop at ±stop_points, BE at ±stop_points, TP at ±stop_points*2.

    Returns (trades, day_stats).
    """
    trades: List[Trade] = []
    day_stats: List[DayStats] = []

    # Group by date
    df = df.copy()
    df["date"] = df.index.date

    for date, day_df in df.groupby("date"):
        day = DayStats(date=str(date))
        in_position = False
        entry_price = 0.0
        entry_time = None
        side = ""
        be_moved = False  # whether stop has been moved to breakeven

        for ts, row in day_df.iterrows():
            # Check if we're in a position — simulate bar-by-bar exit
            if in_position:
                if side == "long":
                    current_stop = entry_price if be_moved else entry_price - stop_points
                    tp_price = entry_price + stop_points * 2
                    be_trigger = entry_price + stop_points

                    # Check 2R take profit first (use high)
                    if row["high"] >= tp_price:
                        exit_price = tp_price
                        pnl = (exit_price - entry_price) * contracts * point_value
                        trades.append(Trade(entry_time, ts, "long", entry_price, exit_price,
                                           contracts, stop_points, "tp", pnl))
                        day.pnl += pnl
                        day.trades += 1
                        in_position = False
                        be_moved = False
                        continue

                    # Check stop (use low)
                    if row["low"] <= current_stop:
                        exit_price = current_stop
                        pnl = (exit_price - entry_price) * contracts * point_value
                        reason = "be_stop" if be_moved else "sl"
                        trades.append(Trade(entry_time, ts, "long", entry_price, exit_price,
                                           contracts, stop_points, reason, pnl))
                        day.pnl += pnl
                        day.trades += 1
                        if not be_moved:   # only a real loss if stop not at BE
                            day.losses += 1
                        in_position = False
                        be_moved = False
                        continue

                    # Check BE trigger (use high)
                    if not be_moved and row["high"] >= be_trigger:
                        be_moved = True

                else:  # short
                    current_stop = entry_price if be_moved else entry_price + stop_points
                    tp_price = entry_price - stop_points * 2
                    be_trigger = entry_price - stop_points

                    if row["low"] <= tp_price:
                        exit_price = tp_price
                        pnl = (entry_price - exit_price) * contracts * point_value
                        trades.append(Trade(entry_time, ts, "short", entry_price, exit_price,
                                           contracts, stop_points, "tp", pnl))
                        day.pnl += pnl
                        day.trades += 1
                        in_position = False
                        be_moved = False
                        continue

                    if row["high"] >= current_stop:
                        exit_price = current_stop
                        pnl = (entry_price - exit_price) * contracts * point_value
                        reason = "be_stop" if be_moved else "sl"
                        trades.append(Trade(entry_time, ts, "short", entry_price, exit_price,
                                           contracts, stop_points, reason, pnl))
                        day.pnl += pnl
                        day.trades += 1
                        if not be_moved:
                            day.losses += 1
                        in_position = False
                        be_moved = False
                        continue

                    if not be_moved and row["low"] <= be_trigger:
                        be_moved = True

            # Check if we should stop trading today
            if day.losses >= max_daily_losses:
                day.stopped_early = True
                break
            if day.trades >= max_daily_trades:
                break

            # New entry on signal
            if not in_position:
                if row["long_signal"]:
                    in_position = True
                    entry_price = row["close"]
                    entry_time = ts
                    side = "long"
                    be_moved = False
                elif row["short_signal"]:
                    in_position = True
                    entry_price = row["close"]
                    entry_time = ts
                    side = "short"
                    be_moved = False

        # EOD: force close any open position
        if in_position and day_df is not None and len(day_df) > 0:
            last_row = day_df.iloc[-1]
            exit_price = last_row["close"]
            pnl = (exit_price - entry_price if side == "long" else entry_price - exit_price) * contracts * point_value
            trades.append(Trade(entry_time, day_df.index[-1], side, entry_price, exit_price,
                               contracts, stop_points, "eod", pnl))
            day.pnl += pnl
            day.trades += 1

        day_stats.append(day)

    return trades, day_stats
