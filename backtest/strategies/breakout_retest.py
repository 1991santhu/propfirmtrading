from backtest.strategies.base import BaseStrategy
import pandas as pd
import numpy as np


class BreakoutRetestStrategy(BaseStrategy):
    name = "G: Breakout + Retest"
    tolerance: int = 5  # points — how close low/high must get to level for valid retest

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        """
        For each key level, tracks a 3-state machine per day:
          watching -> armed (close crossed level) -> retested (low/high touched level)
          -> signal fires when close crosses level again after retest

        Long levels: ORH, PDH, PMH, PDC
        Short levels: ORL, PDL, PML, PDC
        """
        df = df.copy()
        df['long_signal']  = False
        df['short_signal'] = False
        df['_date'] = df.index.date

        long_levels  = ['orh', 'pdh', 'pmh', 'pdc']
        short_levels = ['orl', 'pdl', 'pml', 'pdc']

        for date, day_df in df.groupby('_date'):
            # State: 'watching', 'armed', 'retested', 'done'
            long_states  = {lvl: 'watching' for lvl in long_levels}
            short_states = {lvl: 'watching' for lvl in short_levels}

            prev_close = None

            for ts, row in day_df.iterrows():
                # ── Long side ───────────────────────────────────────────────
                for lvl_col in long_levels:
                    lvl = row.get(lvl_col)
                    if pd.isna(lvl):
                        continue
                    state = long_states[lvl_col]

                    if state == 'watching':
                        # Breakout: close moves above level
                        if prev_close is not None and prev_close <= lvl < row['close']:
                            long_states[lvl_col] = 'armed'

                    elif state == 'armed':
                        # Full retest: low touches the level (within tolerance)
                        if row['low'] <= lvl + self.tolerance:
                            long_states[lvl_col] = 'retested'

                    elif state == 'retested':
                        # Re-breakout after retest: close above level -> entry signal
                        if row['close'] > lvl:
                            df.loc[ts, 'long_signal'] = True
                            long_states[lvl_col] = 'armed' if reentry else 'done'

                # ── Short side ──────────────────────────────────────────────
                for lvl_col in short_levels:
                    lvl = row.get(lvl_col)
                    if pd.isna(lvl):
                        continue
                    state = short_states[lvl_col]

                    if state == 'watching':
                        # Breakout: close moves below level
                        if prev_close is not None and prev_close >= lvl > row['close']:
                            short_states[lvl_col] = 'armed'

                    elif state == 'armed':
                        # Full retest: high touches the level (within tolerance)
                        if row['high'] >= lvl - self.tolerance:
                            short_states[lvl_col] = 'retested'

                    elif state == 'retested':
                        # Re-breakout after retest: close below level -> entry signal
                        if row['close'] < lvl:
                            df.loc[ts, 'short_signal'] = True
                            short_states[lvl_col] = 'armed' if reentry else 'done'

                prev_close = row['close']

        df = df.drop(columns=['_date'])
        return df
