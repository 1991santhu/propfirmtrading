from backtest.strategies.orb_only import ORBOnlyStrategy
from backtest.strategies.key_levels import KeyLevelsStrategy
from backtest.strategies.kl_cloud12 import KLCloud12Strategy
from backtest.strategies.kl_cloud3 import KLCloud3Strategy
from backtest.strategies.kl_all_clouds import KLAllCloudsStrategy
from backtest.strategies.cloud_at_level import CloudAtLevelStrategy
from backtest.strategies.breakout_retest import BreakoutRetestStrategy
from backtest.strategies.pdc_only import PDCOnlyStrategy
from backtest.strategies.premarket_only import PreMarketOnlyStrategy
from backtest.strategies.breakout_retest_ema import BreakoutRetestEMAStrategy
from backtest.strategies.breakout_retest_trend_ema import BreakoutRetestTrendEMAStrategy
from backtest.strategies.orb_retest import ORBRetestStrategy

# Removed: H (Morning Only), I (Afternoon Only), L (ORB+Cloud3), M (B+R+Trend)
ALL_STRATEGIES = [
    ORBOnlyStrategy(),        # A
    KeyLevelsStrategy(),      # B
    KLCloud12Strategy(),      # C
    KLCloud3Strategy(),       # D
    KLAllCloudsStrategy(),    # E
    CloudAtLevelStrategy(),   # F
    BreakoutRetestStrategy(), # G
    PDCOnlyStrategy(),        # J
    PreMarketOnlyStrategy(),  # K
    BreakoutRetestEMAStrategy(),     # N
    BreakoutRetestTrendEMAStrategy(), # O
    ORBRetestStrategy(),      # P (new: ORB breakout + retest)
]
