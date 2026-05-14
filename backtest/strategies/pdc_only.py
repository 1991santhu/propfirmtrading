"""Strategy J: PDC Only — trades solely at the Previous Day Close level."""
import pandas as pd
from backtest.strategies.base import BaseStrategy


class PDCOnlyStrategy(BaseStrategy):
    name = "J: PDC Only"

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        return self._level_break_signals(
            df,
            long_levels=["pdc"],
            short_levels=["pdc"],
            reentry=reentry,
        )
