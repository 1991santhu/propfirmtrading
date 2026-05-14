"""Strategy I: All Key Levels, Afternoon Session Only (1:00-3:30 PM ET)."""
import pandas as pd
from backtest.strategies.base import BaseStrategy


class AfternoonOnlyStrategy(BaseStrategy):
    name = "I: Afternoon Only (13:00-15:30)"

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        afternoon = df.between_time("13:00", "15:29")
        long_levels  = ["orh", "pdh", "pmh", "pdc"]
        short_levels = ["orl", "pdl", "pml", "pdc"]
        signals = self._level_break_signals(afternoon, long_levels, short_levels, reentry=reentry)
        out = df.copy()
        out["long_signal"]  = False
        out["short_signal"] = False
        out.loc[signals.index, "long_signal"]  = signals["long_signal"]
        out.loc[signals.index, "short_signal"] = signals["short_signal"]
        return out
