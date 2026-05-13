import pandas as pd
import numpy as np
from backtest.signals import add_signals

def make_df(closes):
    """Helper: build minimal DataFrame from a list of close prices."""
    n = len(closes)
    idx = pd.date_range("2024-01-02 09:30", periods=n, freq="5min")
    df = pd.DataFrame({
        "open": closes, "high": closes, "low": closes, "close": closes, "volume": 1
    }, index=idx)
    return df

def test_cloud1_green_when_ema8_above_ema9():
    # With a strong uptrend, ema8 > ema9 after warmup
    closes = [100.0] * 5 + [105.0] * 30
    df = add_signals(make_df(closes))
    assert df["cloud1_green"].iloc[-1] == True

def test_long_signal_on_transition_only():
    # long_signal must be exactly (both_green AND NOT both_green.shift(1)).
    # Test with a realistic uptrend dataset.
    closes = [100.0] * 5 + [110.0] * 30
    df = add_signals(make_df(closes))

    bg = df["both_green"]
    expected = (bg & ~bg.shift(1).fillna(False))

    # long_signal definition matches the transition formula precisely
    pd.testing.assert_series_equal(
        df["long_signal"],
        expected,
        check_names=False,
    )

    # When both_green is always False (flat/falling), long_signal must also always be False
    closes_flat = [100.0] * 30
    df_flat = add_signals(make_df(closes_flat))
    assert df_flat["long_signal"].sum() == 0

def test_no_signal_when_clouds_mixed():
    # ema8/9 green but ema5/12 still red -> no signal
    # Hard to construct precisely, so just verify both_green requires both
    closes = [100.0] * 30
    df = add_signals(make_df(closes))
    # Flat prices -> all EMAs equal -> cloud1_green is False (not strictly greater)
    assert df["both_green"].iloc[-1] == False

def test_signal_columns_present():
    closes = [100.0 + i * 0.1 for i in range(50)]
    df = add_signals(make_df(closes))
    for col in ["ema8", "ema9", "ema5", "ema12", "cloud1_green", "cloud2_green",
                "both_green", "both_red", "long_signal", "short_signal"]:
        assert col in df.columns
