"""Strategy L: ORB Levels + EMA Cloud3 (34/50) as trend filter."""
import pandas as pd
from backtest.strategies.base import BaseStrategy


class ORBCloud3Strategy(BaseStrategy):
    name = "L: ORB + Cloud3 Trend"

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        return self._level_break_signals(
            df,
            long_levels=["orh"],
            short_levels=["orl"],
            long_filter=df["cloud3_green"],
            short_filter=~df["cloud3_green"],
            reentry=reentry,
        )
