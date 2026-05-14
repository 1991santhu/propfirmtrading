from backtest.strategies.breakout_retest import BreakoutRetestStrategy
import pandas as pd


class BreakoutRetestEMAStrategy(BreakoutRetestStrategy):
    """
    Strategy G + EMA cloud confirmation:
      - Long only when both EMA clouds are green (ema8>ema9 AND ema5>ema12)
      - Short only when both EMA clouds are red (~ema8>ema9 AND ~ema5>ema12)
    Requires add_ema_clouds() to have been called (provides both_green/both_red columns).
    """
    name = "N: Breakout + Retest + EMA"

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        df = super().generate_signals(df, reentry=reentry)

        if "both_green" not in df.columns or "both_red" not in df.columns:
            return df

        df["long_signal"]  = df["long_signal"]  & df["both_green"]
        df["short_signal"] = df["short_signal"] & df["both_red"]
        return df
