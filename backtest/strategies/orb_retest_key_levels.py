"""
Strategy Q: ORB Retest + Key Levels

Hybrid of P and B:
  - ORH/ORL: 3-state machine (breakout → retest → re-break) from P — high quality
  - PDH/PDL/PMH/PML/PDC: simple close-crosses-level from B — more signals

Rationale: ORH/ORL retest signals are the highest quality because the opening range
is a fresh, intraday-derived level with strong crowd attention. PDH/PDL etc. are
weaker individually but add useful signal volume to fill out the day.
"""
from backtest.strategies.breakout_retest import BreakoutRetestStrategy
import pandas as pd


class ORBRetestKeyLevelsStrategy(BreakoutRetestStrategy):
    name = "Q: ORB Retest + Key Levels"

    # Simple key levels handled with B-style logic (no retest required)
    _kl_long  = ['pdh', 'pmh', 'pdc']
    _kl_short = ['pdl', 'pml', 'pdc']

    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        df = df.copy()
        df['long_signal']  = False
        df['short_signal'] = False
        df['_date'] = df.index.date

        for date, day_df in df.groupby('_date'):
            # ── ORH/ORL: 3-state machine ─────────────────────────────────
            long_state  = 'watching'
            short_state = 'watching'
            prev_close  = None

            # ── PDH/PDL/PMH/PML/PDC: simple level-break (one fire per level) ─
            used_long_kl  = set()
            used_short_kl = set()

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

                # Simple key-level breaks (long)
                for lvl_col in self._kl_long:
                    if not reentry and lvl_col in used_long_kl:
                        continue
                    lvl = row.get(lvl_col)
                    if pd.isna(lvl):
                        continue
                    if prev_close is not None and prev_close < lvl <= row['close']:
                        df.loc[ts, 'long_signal'] = True
                        if not reentry:
                            used_long_kl.add(lvl_col)

                # Simple key-level breaks (short)
                for lvl_col in self._kl_short:
                    if not reentry and lvl_col in used_short_kl:
                        continue
                    lvl = row.get(lvl_col)
                    if pd.isna(lvl):
                        continue
                    if prev_close is not None and prev_close > lvl >= row['close']:
                        df.loc[ts, 'short_signal'] = True
                        if not reentry:
                            used_short_kl.add(lvl_col)

                prev_close = row['close']

        df = df.drop(columns=['_date'])
        return df
