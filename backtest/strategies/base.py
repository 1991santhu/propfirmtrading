from abc import ABC, abstractmethod
import pandas as pd


class BaseStrategy(ABC):
    name: str = "Base"

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame, reentry: bool = False) -> pd.DataFrame:
        """
        Takes enriched DataFrame (with EMA clouds + key levels already computed).
        Returns copy with 'long_signal' and 'short_signal' boolean columns added.

        reentry=False: each key level triggers at most once per day
        reentry=True:  a level can trigger multiple times per day
        """
        pass

    def _level_break_signals(
        self,
        df: pd.DataFrame,
        long_levels: list,   # column names: e.g. ['orh', 'pdh', 'pmh']
        short_levels: list,  # column names: e.g. ['orl', 'pdl', 'pml']
        long_filter: pd.Series = None,   # boolean Series: additional filter for longs
        short_filter: pd.Series = None,  # boolean Series: additional filter for shorts
        reentry: bool = False,
    ) -> pd.DataFrame:
        """
        Shared helper: generate long/short signals when close crosses a key level.
        Signal fires on the bar where close crosses the level (from below for long,
        from above for short). Handles reentry flag and per-day level tracking.
        """
        df = df.copy()
        df['long_signal']  = False
        df['short_signal'] = False

        if long_filter is None:
            long_filter = pd.Series(True, index=df.index)
        if short_filter is None:
            short_filter = pd.Series(True, index=df.index)

        df['_date'] = df.index.date

        for date, day_df in df.groupby('_date'):
            used_long_levels  = set()
            used_short_levels = set()

            for ts, row in day_df.iterrows():
                # Long signals
                for lvl_col in long_levels:
                    lvl = row.get(lvl_col)
                    if pd.isna(lvl):
                        continue
                    if not reentry and lvl_col in used_long_levels:
                        continue
                    prev_close = df.loc[:ts, 'close'].iloc[-2] if len(df.loc[:ts]) > 1 else None
                    if prev_close is not None and prev_close < lvl <= row['close']:
                        if long_filter.loc[ts]:
                            df.loc[ts, 'long_signal'] = True
                            if not reentry:
                                used_long_levels.add(lvl_col)

                # Short signals
                for lvl_col in short_levels:
                    lvl = row.get(lvl_col)
                    if pd.isna(lvl):
                        continue
                    if not reentry and lvl_col in used_short_levels:
                        continue
                    prev_close = df.loc[:ts, 'close'].iloc[-2] if len(df.loc[:ts]) > 1 else None
                    if prev_close is not None and prev_close > lvl >= row['close']:
                        if short_filter.loc[ts]:
                            df.loc[ts, 'short_signal'] = True
                            if not reentry:
                                used_short_levels.add(lvl_col)

        df = df.drop(columns=['_date'])
        return df
