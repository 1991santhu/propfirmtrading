"""
Strategy Q: Cloud Flip Near Key Level + ORB Retest (F + P combined)

Takes the union of two signal sources:
  - F: cloud flip (both_green/both_red just turned on) within 30pt of any key level
  - P: ORH/ORL 3-state machine (breakout → retest → re-break)

Rationale: F fires on momentum confirmation at structure; P fires on high-quality
ORB breakout/retest. Together they cover both intraday momentum and opening-range
continuation without duplicating each other's logic.

allows_early_entry=True inherited from the cloud flip component (F fires pre-10AM).
"""
from backtest.strategies.breakout_retest import BreakoutRetestStrategy
import pandas as pd


class ORBRetestCloudFlipStrategy(BreakoutRetestStrategy):
    name = "Q: Cloud Flip + ORB Retest"
    proximity_points: int = 30
    allows_early_entry = True

    _cloud_long_levels  = ['orh', 'pdh', 'pmh', 'pdc']
    _cloud_short_levels = ['orl', 'pdl', 'pml', 'pdc']

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        df = df.copy()
        df['long_signal']  = False
        df['short_signal'] = False

        # ── F component: cloud flip transitions ───────────────────────
        cloud_long  = df['both_green'] & ~df['both_green'].shift(1).fillna(False)
        cloud_short = df['both_red']   & ~df['both_red'].shift(1).fillna(False)

        df['_date'] = df.index.date

        for date, day_df in df.groupby('_date'):
            # ── P component: ORH/ORL 3-state machine ──────────────────
            long_state  = 'watching'
            short_state = 'watching'
            prev_close  = None

            for ts, row in day_df.iterrows():
                orh = row.get('orh')
                orl = row.get('orl')

                # ORH 3-state (long)
                if not pd.isna(orh):
                    if long_state == 'watching':
                        if prev_close is not None and prev_close <= orh < row['close']:
                            long_state = 'armed'
                    elif long_state == 'armed':
                        if row['low'] <= orh + self.tolerance:
                            long_state = 'retested'
                    elif long_state == 'retested':
                        if row['close'] > orh:
                            df.loc[ts, 'long_signal'] = True
                            long_state = 'armed' if reentry else 'done'

                # ORL 3-state (short)
                if not pd.isna(orl):
                    if short_state == 'watching':
                        if prev_close is not None and prev_close >= orl > row['close']:
                            short_state = 'armed'
                    elif short_state == 'armed':
                        if row['high'] >= orl - self.tolerance:
                            short_state = 'retested'
                    elif short_state == 'retested':
                        if row['close'] < orl:
                            df.loc[ts, 'short_signal'] = True
                            short_state = 'armed' if reentry else 'done'

                # F component: cloud flip near key level
                if cloud_long.loc[ts]:
                    for lvl_col in self._cloud_long_levels:
                        lvl = row.get(lvl_col)
                        if not pd.isna(lvl) and abs(row['close'] - lvl) <= self.proximity_points:
                            df.loc[ts, 'long_signal'] = True
                            break

                if cloud_short.loc[ts]:
                    for lvl_col in self._cloud_short_levels:
                        lvl = row.get(lvl_col)
                        if not pd.isna(lvl) and abs(row['close'] - lvl) <= self.proximity_points:
                            df.loc[ts, 'short_signal'] = True
                            break

                prev_close = row['close']

        df = df.drop(columns=['_date'])
        return df
