from backtest.strategies.base import BaseStrategy
import pandas as pd


class KLCloud3Strategy(BaseStrategy):
    name = "D: Key Levels + Cloud 3"
    allows_early_entry = True

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        return self._level_break_signals(
            df,
            long_levels=['orh', 'pdh', 'pmh', 'pdc'],
            short_levels=['orl', 'pdl', 'pml', 'pdc'],
            long_filter=df['cloud3_green'],
            short_filter=~df['cloud3_green'],
            reentry=reentry,
        )
