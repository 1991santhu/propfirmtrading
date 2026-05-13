import pandas as pd
import numpy as np
from backtest.signals import add_signals
from backtest.simulator import simulate_trades, Trade

def make_signal_df(long_at=None, short_at=None, prices=None, n=50):
    """Build a DataFrame with manual signal injection."""
    idx = pd.date_range("2024-01-02 09:30", periods=n, freq="5min",
                        tz="America/New_York")
    base = 20000.0
    if prices is None:
        prices = [base] * n
    df = pd.DataFrame({
        "open": prices, "high": prices, "low": prices, "close": prices, "volume": 1,
        "long_signal": False, "short_signal": False,
        "both_green": False, "both_red": False,
    }, index=idx)
    if long_at is not None:
        df.loc[df.index[long_at], "long_signal"] = True
    if short_at is not None:
        df.loc[df.index[short_at], "short_signal"] = True
    df["date"] = df.index.date
    return df

def test_tp_hit_long():
    """Price moves up 60 pts -> take profit."""
    entry = 20000.0
    stop = 30
    # Bars: entry bar, then price shoots to TP
    prices = [entry] * 5 + [entry + stop * 2 + 1] * 45
    highs = prices[:]
    lows  = prices[:]
    df = make_signal_df(long_at=0, prices=prices, n=50)
    df["high"] = highs
    df["low"] = lows
    trades, _ = simulate_trades(df, contracts=3, stop_points=stop)
    assert len(trades) == 1
    assert trades[0].exit_reason == "tp"
    assert trades[0].pnl == stop * 2 * 3 * 2  # 60 pts x 3 contracts x $2

def test_sl_hit_long():
    """Price drops 30 pts immediately -> stop loss."""
    entry = 20000.0
    stop = 30
    prices = [entry] * 5 + [entry - stop - 1] * 45
    df = make_signal_df(long_at=0, prices=prices, n=50)
    df["high"] = prices
    df["low"] = prices
    trades, _ = simulate_trades(df, contracts=3, stop_points=stop)
    assert len(trades) == 1
    assert trades[0].exit_reason == "sl"
    assert trades[0].pnl == -stop * 3 * 2  # -$180

def test_daily_loss_limit_stops_trading():
    """After 2 losses, no more trades taken."""
    entry = 20000.0
    stop = 30
    n = 50

    # Build bars where each signal fires, then the next bar immediately hits the stop.
    # Signal at bar 0 -> entry at 20000; bar 1: low = 19969 (hits -30 stop) -> loss 1
    # Signal at bar 5 -> entry at 20000; bar 6: low = 19969 (hits -30 stop) -> loss 2
    # Signal at bar 20 -> should be ignored (2-loss daily limit reached)
    closes = [entry] * n
    highs  = [entry] * n
    lows   = [entry] * n

    # First trade: signal at bar 0, loss hits on bar 1
    lows[1] = entry - stop - 1

    # Second trade: signal at bar 5, bar 5 price is neutral, loss hits on bar 6
    lows[6] = entry - stop - 1

    # Third trade: signal at bar 20 should NOT be taken
    lows[21] = entry - stop - 1

    df = make_signal_df(n=n, prices=closes)
    df.loc[df.index[0], "long_signal"] = True
    df.loc[df.index[5], "long_signal"] = True
    df.loc[df.index[20], "long_signal"] = True
    df["high"] = highs
    df["low"] = lows

    trades, day_stats = simulate_trades(df, contracts=3, stop_points=stop, max_daily_losses=2)
    # Only 2 stop-loss trades taken (3rd signal ignored after 2 losses)
    sl_trades = [t for t in trades if t.exit_reason == "sl"]
    assert len(sl_trades) == 2
    assert day_stats[0].stopped_early or day_stats[0].losses >= 2
