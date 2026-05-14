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


def _compute_stop(
    side: str,
    entry: float,
    stop_pts: float,
    be_stage: int,
    be_buffer_points: int,
    ladder: list,   # list of (trigger_r, lock_r)
    use_ladder: bool,
) -> float:
    """Return the current protective stop price given trade state."""
    if be_stage == 0:
        # No BE move yet — initial hard stop
        return entry - stop_pts if side == "long" else entry + stop_pts

    if use_ladder:
        # Lock-in level from the last reached ladder step
        _, lock_r = ladder[be_stage - 1]
        if side == "long":
            return entry + lock_r * stop_pts
        return entry - lock_r * stop_pts
    else:
        # Legacy be_buffer_points: stop at entry ± buffer
        if side == "long":
            return entry + be_buffer_points
        return entry - be_buffer_points


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
    be_ladder: list[tuple[float, float]] | None = None,
    # Tiered stop ladder — overrides be_buffer_points when set.
    # Each entry is (trigger_r, lock_r):
    #   trigger_r — when price profit reaches this multiple of R, advance stage
    #   lock_r    — stop moves to entry + lock_r * stop (long) or entry - lock_r * stop (short)
    # Example: [(1.0, 0.5), (1.5, 1.0)]
    #   At 1R profit  → stop moves to entry + 0.5R  (lock half the first R)
    #   At 1.5R profit → stop moves to entry + 1.0R (lock full first R)
    # Entries must be sorted by trigger_r ascending. All lock_r values must be ≥ 0.
    commission_per_side: float = 0.59, # $ per contract per side (Tradovate all-in ~$0.59)
    min_range_pts: float = 0,          # skip day if prev_day_range < this (range filter)
    no_first_30min: bool = False,      # if True, skip all entries before 10:00 AM ET
    cloud_flip_exit: bool = False,     # if True, exit long when both_red flips True (and vice versa)
                                       # only triggers when exit price is better than the SL
) -> tuple[List[Trade], List[DayStats]]:
    """
    Simulate all trades from signal dataframe.

    Stop sizing (pick one):
      stop_points  — fixed absolute points, e.g. 60. Not era-comparable.
      stop_pct     — percentage of entry price, e.g. 0.20 → 58pts at 29k MNQ.
                     Preferred for multi-year backtests.

    BE / stop ladder (pick one):
      be_buffer_points — legacy single-step: at 1R, stop moves to entry ± N pts.
      be_ladder        — tiered R-based ladder (see parameter docs above).
                         Takes priority over be_buffer_points when set.

    Returns (trades, day_stats).
    """
    trades: List[Trade] = []
    day_stats: List[DayStats] = []

    # Prepare ladder
    use_ladder = be_ladder is not None
    sorted_ladder = sorted(be_ladder, key=lambda x: x[0]) if be_ladder else []
    # For legacy mode, synthesise a 1-step ladder equivalent to be_buffer_points
    # so the loop logic is unified. We still track via be_stage.

    df = df.copy()
    df["date"] = df.index.date
    commission_rt = commission_per_side * 2  # round-trip cost per contract

    for date, day_df in df.groupby("date"):
        if min_range_pts > 0 and "prev_day_range" in day_df.columns:
            prev_range = day_df["prev_day_range"].iloc[0]
            if not pd.isna(prev_range) and prev_range < min_range_pts:
                day_stats.append(DayStats(date=str(date)))
                continue

        day = DayStats(date=str(date))
        in_position = False
        entry_price = 0.0
        entry_time = None
        side = ""
        be_stage = 0            # 0 = initial stop; N = Nth ladder step reached
        trade_stop_pts: float = stop_points

        for ts, row in day_df.iterrows():
            if in_position:
                comm = commission_rt * contracts
                tp_price = (entry_price + trade_stop_pts * rr_ratio
                            if side == "long"
                            else entry_price - trade_stop_pts * rr_ratio)

                current_stop = _compute_stop(
                    side, entry_price, trade_stop_pts,
                    be_stage, be_buffer_points, sorted_ladder, use_ladder,
                )

                # ── Advance ladder stage ──────────────────────────────────
                if use_ladder:
                    while be_stage < len(sorted_ladder):
                        trigger_r, _ = sorted_ladder[be_stage]
                        trigger_price = (entry_price + trigger_r * trade_stop_pts
                                         if side == "long"
                                         else entry_price - trigger_r * trade_stop_pts)
                        if (side == "long" and row["high"] >= trigger_price) or \
                           (side == "short" and row["low"] <= trigger_price):
                            be_stage += 1
                            # Recompute stop after advancing
                            current_stop = _compute_stop(
                                side, entry_price, trade_stop_pts,
                                be_stage, be_buffer_points, sorted_ladder, use_ladder,
                            )
                        else:
                            break
                else:
                    # Legacy: single BE move at 1R
                    if be_stage == 0:
                        be_trigger = (entry_price + trade_stop_pts
                                      if side == "long"
                                      else entry_price - trade_stop_pts)
                        if (side == "long" and row["high"] >= be_trigger) or \
                           (side == "short" and row["low"] <= be_trigger):
                            be_stage = 1
                            current_stop = _compute_stop(
                                side, entry_price, trade_stop_pts,
                                be_stage, be_buffer_points, sorted_ladder, use_ladder,
                            )

                # ── Take profit ───────────────────────────────────────────
                tp_hit = (row["high"] >= tp_price if side == "long"
                          else row["low"] <= tp_price)
                if tp_hit:
                    exit_price = tp_price
                    pnl = ((exit_price - entry_price if side == "long"
                            else entry_price - exit_price)
                           * contracts * point_value - comm)
                    trades.append(Trade(entry_time, ts, side, entry_price, exit_price,
                                       contracts, trade_stop_pts, "tp", pnl))
                    day.pnl += pnl
                    day.trades += 1
                    in_position = False
                    be_stage = 0
                    continue

                # ── Stop loss / BE stop ───────────────────────────────────
                sl_hit = (row["low"] <= current_stop if side == "long"
                          else row["high"] >= current_stop)
                if sl_hit:
                    exit_price = current_stop
                    pnl = ((exit_price - entry_price if side == "long"
                            else entry_price - exit_price)
                           * contracts * point_value - comm)
                    reason = "be_stop" if be_stage > 0 else "sl"
                    trades.append(Trade(entry_time, ts, side, entry_price, exit_price,
                                       contracts, trade_stop_pts, reason, pnl))
                    day.pnl += pnl
                    day.trades += 1
                    if be_stage == 0:          # only a full SL counts as a daily loss
                        day.losses += 1
                    in_position = False
                    be_stage = 0
                    continue

                # ── Cloud-flip early exit ─────────────────────────────────
                if cloud_flip_exit and be_stage == 0:
                    flip = (row.get("both_red", False) if side == "long"
                            else row.get("both_green", False))
                    exit_better = (row["close"] > current_stop if side == "long"
                                   else row["close"] < current_stop)
                    if flip and exit_better:
                        exit_price = row["close"]
                        pnl = ((exit_price - entry_price if side == "long"
                                else entry_price - exit_price)
                               * contracts * point_value - comm)
                        trades.append(Trade(entry_time, ts, side, entry_price, exit_price,
                                           contracts, trade_stop_pts, "cloud_flip", pnl))
                        day.pnl += pnl
                        day.trades += 1
                        if pnl < 0:
                            day.losses += 1
                        in_position = False
                        be_stage = 0
                        continue

            # ── Daily limits ──────────────────────────────────────────────
            if day.losses >= max_daily_losses:
                day.stopped_early = True
                break
            if day.trades >= max_daily_trades:
                break

            # ── New entry ─────────────────────────────────────────────────
            if not in_position:
                if no_first_30min and ts.time() < dtime(10, 0):
                    continue
                signal = ("long" if row["long_signal"]
                          else "short" if row["short_signal"]
                          else None)
                if signal:
                    in_position = True
                    entry_price = row["close"]
                    entry_time = ts
                    side = signal
                    be_stage = 0
                    trade_stop_pts = (round(entry_price * stop_pct / 100, 1)
                                      if stop_pct else stop_points)

        # ── EOD close ────────────────────────────────────────────────────
        if in_position and len(day_df) > 0:
            last_row = day_df.iloc[-1]
            exit_price = last_row["close"]
            comm = commission_rt * contracts
            pnl = ((exit_price - entry_price if side == "long"
                    else entry_price - exit_price)
                   * contracts * point_value - comm)
            trades.append(Trade(entry_time, day_df.index[-1], side, entry_price,
                               exit_price, contracts, trade_stop_pts, "eod", pnl))
            day.pnl += pnl
            day.trades += 1

        day_stats.append(day)

    return trades, day_stats
