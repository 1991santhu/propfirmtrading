"""Strategy K: Pre-Market Levels Only — PMH and PML breakouts."""
import pandas as pd
from backtest.strategies.base import BaseStrategy


class PreMarketOnlyStrategy(BaseStrategy):
    name = "K: Pre-Market Levels Only"

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        return self._level_break_signals(
            df,
            long_levels=["pmh"],
            short_levels=["pml"],
            reentry=reentry,
        )
