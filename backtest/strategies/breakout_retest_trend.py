from backtest.strategies.breakout_retest import BreakoutRetestStrategy
import pandas as pd


class BreakoutRetestTrendStrategy(BreakoutRetestStrategy):
    """
    Strategy G + daily trend filter:
      - Only long when close > 20-day SMA of daily closes
      - Only short when close < 20-day SMA of daily closes
    Requires add_key_levels() to have been called (provides daily_sma20 column).
    """
    name = "M: Breakout + Retest + Trend"

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        df = super().generate_signals(df, reentry=reentry)

        if "daily_trend_up" not in df.columns:
            return df

        # Suppress longs on bearish days, shorts on bullish days
        df["long_signal"]  = df["long_signal"]  & df["daily_trend_up"]
        df["short_signal"] = df["short_signal"] & ~df["daily_trend_up"]
        return df
