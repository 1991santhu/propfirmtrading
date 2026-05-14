from backtest.strategies.breakout_retest import BreakoutRetestStrategy
import pandas as pd


class BreakoutRetestTrendEMAStrategy(BreakoutRetestStrategy):
    """
    Strategy G + daily trend filter + EMA cloud confirmation (all three):
      - Long only: both_green AND daily_trend_up (close > 20-day SMA)
      - Short only: both_red AND NOT daily_trend_up
    Requires add_key_levels() and add_ema_clouds() to have been called.
    """
    name = "O: Breakout + Retest + Trend + EMA"

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        df = super().generate_signals(df, reentry=reentry)

        has_trend = "daily_trend_up" in df.columns
        has_clouds = "both_green" in df.columns and "both_red" in df.columns

        if has_clouds:
            df["long_signal"]  = df["long_signal"]  & df["both_green"]
            df["short_signal"] = df["short_signal"] & df["both_red"]

        if has_trend:
            df["long_signal"]  = df["long_signal"]  & df["daily_trend_up"]
            df["short_signal"] = df["short_signal"] & ~df["daily_trend_up"]

        return df
