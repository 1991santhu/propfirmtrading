"""
Strategy P: ORB Breakout + Retest

Same 3-state machine as G (Breakout+Retest) but ONLY watches ORH (long)
and ORL (short). Much more selective than G — waits for the opening range
to form, then requires a breakout, a pullback retest of the ORH/ORL, and
a confirmed re-breakout before entering.

Because ORH/ORL are NaN before 10:00 AM, this strategy cannot arm until
after the opening range closes — no_first_30min is implicit.
"""
from backtest.strategies.breakout_retest import BreakoutRetestStrategy
import pandas as pd


class ORBRetestStrategy(BreakoutRetestStrategy):
    name = "P: ORB Breakout + Retest"

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        df = df.copy()
        df['long_signal']  = False
        df['short_signal'] = False
        df['_date'] = df.index.date

        for date, day_df in df.groupby('_date'):
            long_state  = 'watching'
            short_state = 'watching'
            prev_close  = None

            for ts, row in day_df.iterrows():
                orh = row.get('orh')
                orl = row.get('orl')

                # ── Long: ORH breakout → retest → re-break ──────────────────
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

                # ── Short: ORL breakdown → retest → re-break ────────────────
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

                prev_close = row['close']

        df = df.drop(columns=['_date'])
        return df
