from backtest.strategies.orb_only import ORBOnlyStrategy
from backtest.strategies.key_levels import KeyLevelsStrategy
from backtest.strategies.kl_cloud12 import KLCloud12Strategy
from backtest.strategies.kl_cloud3 import KLCloud3Strategy
from backtest.strategies.kl_all_clouds import KLAllCloudsStrategy
from backtest.strategies.cloud_at_level import CloudAtLevelStrategy
from backtest.strategies.breakout_retest import BreakoutRetestStrategy

ALL_STRATEGIES = [
    ORBOnlyStrategy(),
    KeyLevelsStrategy(),
    KLCloud12Strategy(),
    KLCloud3Strategy(),
    KLAllCloudsStrategy(),
    CloudAtLevelStrategy(),
    BreakoutRetestStrategy(),
]
