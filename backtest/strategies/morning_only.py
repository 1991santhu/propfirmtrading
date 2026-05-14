"""Strategy H: All Key Levels, Morning Session Only (9:30-11:30 AM ET)."""
import pandas as pd
from backtest.strategies.base import BaseStrategy


class MorningOnlyStrategy(BaseStrategy):
    name = "H: Morning Only (9:30-11:30)"

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        morning = df.between_time("09:30", "11:29")
        long_levels  = ["orh", "pdh", "pmh", "pdc"]
        short_levels = ["orl", "pdl", "pml", "pdc"]
        signals = self._level_break_signals(morning, long_levels, short_levels, reentry=reentry)
        out = df.copy()
        out["long_signal"]  = False
        out["short_signal"] = False
        out.loc[signals.index, "long_signal"]  = signals["long_signal"]
        out.loc[signals.index, "short_signal"] = signals["short_signal"]
        return out
