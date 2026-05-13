from backtest.strategies.base import BaseStrategy
import pandas as pd


class ORBOnlyStrategy(BaseStrategy):
    name = "A: ORB Only"

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        return self._level_break_signals(
            df,
            long_levels=['orh', 'pdc'],
            short_levels=['orl', 'pdc'],
            reentry=reentry,
        )
