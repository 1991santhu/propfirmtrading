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
    trades, _ = simulate_trades(df, contracts=3, stop_points=stop, commission_per_side=0)
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
    trades, _ = simulate_trades(df, contracts=3, stop_points=stop, commission_per_side=0)
    assert len(trades) == 1
    assert trades[0].exit_reason == "sl"
    assert trades[0].pnl == -stop * 3 * 2  # -$180

def test_be_buffer_long():
    """After 1R hit, stop moves to entry + be_buffer; if price reverses, exits at that level."""
    entry = 20000.0
    stop  = 30          # SL at 19970, 1R at 20030, TP at 20060
    buf   = 10          # BE stop at 20010 (entry + 10)
    n = 20
    closes = [entry] * n
    # Bar 0: signal; bar 1: price goes to 20031 (triggers BE move); bar 2: price falls to 20010 (BE stop hit)
    highs = [entry] * n
    lows  = [entry] * n
    highs[1] = entry + stop + 1   # triggers 1R → BE move
    lows[2]  = entry + buf - 1    # falls below BE stop (entry+10)

    df = make_signal_df(long_at=0, n=n)
    df["high"] = highs
    df["low"]  = lows
    df["close"] = closes

    trades, _ = simulate_trades(df, contracts=1, stop_points=stop, be_buffer_points=buf, commission_per_side=0)
    assert len(trades) == 1
    t = trades[0]
    assert t.exit_reason == "be_stop"
    assert t.pnl == buf * 1 * 2  # 10 pts × 1 contract × $2 = $20 profit


def test_be_buffer_short():
    """Short: after 1R hit, stop moves to entry - be_buffer; reversal exits at small profit."""
    entry = 20000.0
    stop  = 30          # SL at 20030, 1R at 19970, TP at 19940
    buf   = 10          # BE stop at 19990 (entry - 10)
    n = 20
    closes = [entry] * n
    highs = [entry] * n
    lows  = [entry] * n
    lows[1]  = entry - stop - 1   # triggers 1R → BE move for short
    highs[2] = entry - buf + 1    # rallies above BE stop (entry-10)

    df = make_signal_df(short_at=0, n=n)
    df["high"] = highs
    df["low"]  = lows
    df["close"] = closes

    trades, _ = simulate_trades(df, contracts=1, stop_points=stop, be_buffer_points=buf, commission_per_side=0)
    assert len(trades) == 1
    t = trades[0]
    assert t.exit_reason == "be_stop"
    assert t.pnl == buf * 1 * 2  # 10 pts × 1 contract × $2 = $20 profit


def test_be_buffer_zero_is_breakeven():
    """be_buffer_points=0 means exact breakeven — BE stop gives $0 P&L."""
    entry = 20000.0
    stop  = 30
    n = 20
    closes = [entry] * n
    highs = [entry] * n
    lows  = [entry] * n
    highs[1] = entry + stop + 1   # triggers 1R → BE move
    lows[2]  = entry - 1          # falls to exactly below entry

    df = make_signal_df(long_at=0, n=n)
    df["high"] = highs
    df["low"]  = lows
    df["close"] = closes

    trades, _ = simulate_trades(df, contracts=1, stop_points=stop, be_buffer_points=0, commission_per_side=0)
    assert len(trades) == 1
    t = trades[0]
    assert t.exit_reason == "be_stop"
    assert t.pnl == 0.0


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

    trades, day_stats = simulate_trades(df, contracts=3, stop_points=stop, max_daily_losses=2, commission_per_side=0)
    # Only 2 stop-loss trades taken (3rd signal ignored after 2 losses)
    sl_trades = [t for t in trades if t.exit_reason == "sl"]
    assert len(sl_trades) == 2
    assert day_stats[0].stopped_early or day_stats[0].losses >= 2
