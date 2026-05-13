from backtest.strategies.base import BaseStrategy
import pandas as pd


class KeyLevelsStrategy(BaseStrategy):
    name = "B: All Key Levels"

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        return self._level_break_signals(
            df,
            long_levels=['orh', 'pdh', 'pmh', 'pdc'],
            short_levels=['orl', 'pdl', 'pml', 'pdc'],
            reentry=reentry,
        )
