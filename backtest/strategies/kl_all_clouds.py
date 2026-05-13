from backtest.strategies.base import BaseStrategy
import pandas as pd


class KLAllCloudsStrategy(BaseStrategy):
    name = "E: Key Levels + All Clouds"

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        all_green = df['both_green'] & df['cloud3_green']
        all_red   = df['both_red']   & ~df['cloud3_green']
        return self._level_break_signals(
            df,
            long_levels=['orh', 'pdh', 'pmh', 'pdc'],
            short_levels=['orl', 'pdl', 'pml', 'pdc'],
            long_filter=all_green,
            short_filter=all_red,
            reentry=reentry,
        )
