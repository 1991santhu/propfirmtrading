from backtest.strategies.base import BaseStrategy
import pandas as pd


class KLCloud12Strategy(BaseStrategy):
    name = "C: Key Levels + Cloud 1&2"

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        return self._level_break_signals(
            df,
            long_levels=['orh', 'pdh', 'pmh', 'pdc'],
            short_levels=['orl', 'pdl', 'pml', 'pdc'],
            long_filter=df['both_green'],
            short_filter=df['both_red'],
            reentry=reentry,
        )
