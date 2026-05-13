import pytest
from unittest.mock import AsyncMock
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
