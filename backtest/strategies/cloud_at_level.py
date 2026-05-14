from backtest.strategies.base import BaseStrategy
import pandas as pd
import numpy as np


class CloudAtLevelStrategy(BaseStrategy):
    name = "F: Cloud Flip Near Key Level"
    proximity_points: int = 30  # within 1R of a key level
    allows_early_entry = True

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        df = df.copy()
        df['long_signal']  = False
        df['short_signal'] = False

        long_levels  = ['orh', 'pdh', 'pmh', 'pdc']
        short_levels = ['orl', 'pdl', 'pml', 'pdc']

        # Cloud 1+2 transition signals
        cloud_long  = df['both_green'] & ~df['both_green'].shift(1).fillna(False)
        cloud_short = df['both_red']   & ~df['both_red'].shift(1).fillna(False)

        for ts, row in df.iterrows():
            if cloud_long.loc[ts]:
                for lvl_col in long_levels:
                    lvl = row.get(lvl_col)
                    if not pd.isna(lvl) and abs(row['close'] - lvl) <= self.proximity_points:
                        df.loc[ts, 'long_signal'] = True
                        break
            if cloud_short.loc[ts]:
                for lvl_col in short_levels:
                    lvl = row.get(lvl_col)
                    if not pd.isna(lvl) and abs(row['close'] - lvl) <= self.proximity_points:
                        df.loc[ts, 'short_signal'] = True
                        break

        return df
