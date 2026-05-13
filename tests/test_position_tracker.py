import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from bot.position_tracker import PositionTracker

@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv("TRADOVATE_USERNAME", "u")
    monkeypatch.setenv("TRADOVATE_PASSWORD", "p")
    monkeypatch.setenv("TRADOVATE_APP_ID", "a")
    monkeypatch.setenv("TRADOVATE_APP_VERSION", "1.0")
    monkeypatch.setenv("TRADOVATE_CLIENT_ID", "1")
    monkeypatch.setenv("TRADOVATE_SECRET", "s")
    monkeypatch.setenv("TRADOVATE_DEVICE_ID", "d")
    monkeypatch.setenv("TRADOVATE_ENV", "demo")
    monkeypatch.setenv("TRADOVATE_ACCOUNT_ID", "1")
    monkeypatch.setenv("TRADOVATE_ACCOUNT_SPEC", "u@f")
    monkeypatch.setenv("WEBHOOK_SECRET", "ws")
    monkeypatch.setenv("SYMBOL", "MNQM5")
    monkeypatch.setenv("CONTRACTS", "3")
    monkeypatch.setenv("STOP_POINTS", "60")
    monkeypatch.setenv("MAX_DAILY_LOSSES", "2")
    monkeypatch.setenv("MAX_DAILY_TRADES", "5")
    monkeypatch.setenv("CLOSE_HOUR_EST", "16")
    monkeypatch.setenv("CLOSE_MINUTE_EST", "40")
    import importlib, config as cfg
    importlib.reload(cfg)
    from config import Settings
    settings = Settings()
    broker = AsyncMock()
    db = AsyncMock()
    return settings, broker, db

def test_calculate_stop_price_long(setup):
    settings, broker, db = setup
    pt = PositionTracker(settings, broker, db)
    assert pt.calculate_stop_price("long", entry=19850.0) == 19790.0

def test_calculate_stop_price_short(setup):
    settings, broker, db = setup
    pt = PositionTracker(settings, broker, db)
    assert pt.calculate_stop_price("short", entry=19850.0) == 19910.0

def test_milestone_thresholds_long(setup):
    settings, broker, db = setup
    pt = PositionTracker(settings, broker, db)
    assert pt.milestone_price("long", entry=19850.0, milestone=1) == 19910.0
    assert pt.milestone_price("long", entry=19850.0, milestone=2) == 19970.0
    assert pt.milestone_price("long", entry=19850.0, milestone=3) == 20030.0

def test_milestone_thresholds_short(setup):
    settings, broker, db = setup
    pt = PositionTracker(settings, broker, db)
    assert pt.milestone_price("short", entry=19850.0, milestone=1) == 19790.0
    assert pt.milestone_price("short", entry=19850.0, milestone=2) == 19730.0

def test_stop_at_milestone_long(setup):
    settings, broker, db = setup
    pt = PositionTracker(settings, broker, db)
    assert pt.stop_at_milestone("long", entry=19850.0, milestone=1) == 19850.0
    assert pt.stop_at_milestone("long", entry=19850.0, milestone=2) == 19910.0
    assert pt.stop_at_milestone("long", entry=19850.0, milestone=3) == 19970.0

def test_contracts_to_close_at_milestone(setup):
    settings, broker, db = setup
    pt = PositionTracker(settings, broker, db)
    assert pt.contracts_to_close(total_contracts=3, milestone=1) == 1
    assert pt.contracts_to_close(total_contracts=3, milestone=2) == 1
    assert pt.contracts_to_close(total_contracts=3, milestone=3) == 0


async def test_fixed_2r_moves_stop_at_1r(setup):
    settings, broker, db = setup
    settings.exit_strategy = "fixed_2r"
    settings.stop_points = 30

    # First poll: price at 1R (19880 = 19850 + 30), triggers breakeven stop move.
    # Second poll: db.get_state returns position=None so the loop exits cleanly.
    broker.get_quote = AsyncMock(side_effect=[19880.0, 19880.0])
    broker.cancel_order = AsyncMock()
    broker.place_stop_order = AsyncMock(return_value="stop2")

    db.get_state = AsyncMock(side_effect=[
        {"position": {"milestone": 0, "contracts": 3}},
        {"position": None},
    ])
    db.update_milestone = AsyncMock()
    db.clear_position = AsyncMock()

    pt = PositionTracker(settings, broker, db)
    pt._stop_order_id = "stop1"
    pt._monitoring = True

    with patch("bot.position_tracker.asyncio.sleep", new=AsyncMock()):
        await pt._run_fixed_2r("long", 19850.0, 3)

    broker.cancel_order.assert_called_with("stop1")
    broker.place_stop_order.assert_called_once_with("MNQM5", "Sell", 3, 19850.0)
    db.update_milestone.assert_called_once_with(1, 19850.0, 3)


async def test_fixed_2r_closes_at_2r(setup):
    settings, broker, db = setup
    settings.exit_strategy = "fixed_2r"
    settings.stop_points = 30

    # Price immediately at 2R (19910 = entry 19850 + 60)
    broker.get_quote = AsyncMock(return_value=19910.0)
    broker.place_market_order = AsyncMock()
    broker.cancel_order = AsyncMock()
    broker.place_stop_order = AsyncMock(return_value="stop2")

    db.get_state = AsyncMock(return_value={"position": {"milestone": 0, "contracts": 3}})
    db.clear_position = AsyncMock()

    pt = PositionTracker(settings, broker, db)
    pt._stop_order_id = "stop1"
    pt._monitoring = True

    with patch("bot.position_tracker.asyncio.sleep", new=AsyncMock()):
        await pt._run_fixed_2r("long", 19850.0, 3)

    broker.place_market_order.assert_called_once_with("MNQM5", "Sell", 3)
    broker.cancel_order.assert_called_once_with("stop1")
    db.clear_position.assert_called_once()


async def test_start_routes_to_fixed_2r(setup):
    settings, broker, db = setup
    settings.exit_strategy = "fixed_2r"
    pt = PositionTracker(settings, broker, db)
    with patch.object(pt, "_run_fixed_2r", new=AsyncMock()) as mock_fixed:
        await pt.start("long", 19850.0, 3, "stop1")
        mock_fixed.assert_called_once_with("long", 19850.0, 3)


async def test_start_routes_to_trailing(setup):
    settings, broker, db = setup
    settings.exit_strategy = "trailing"
    pt = PositionTracker(settings, broker, db)
    with patch.object(pt, "_run_trailing", new=AsyncMock()) as mock_trail:
        await pt.start("long", 19850.0, 3, "stop1")
        mock_trail.assert_called_once_with("long", 19850.0, 3)
