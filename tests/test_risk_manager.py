import pytest
from unittest.mock import AsyncMock
from bot.risk_manager import RiskManager, RejectionReason

def make_state(**overrides):
    base = {
        "daily_losses": 0,
        "daily_trades": 0,
        "in_position": False,
        "daily_pnl": 0.0,
        "total_pnl": 0.0,
        "position": None,
    }
    base.update(overrides)
    return base

@pytest.fixture
def settings(monkeypatch):
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
    return Settings()

@pytest.mark.asyncio
async def test_allows_valid_signal(settings):
    db = AsyncMock()
    db.get_state.return_value = make_state()
    rm = RiskManager(settings, db)
    approved, reason = await rm.check("long", "ws", hour_est=10)
    assert approved is True
    assert reason is None

@pytest.mark.asyncio
async def test_rejects_invalid_secret(settings):
    db = AsyncMock()
    db.get_state.return_value = make_state()
    rm = RiskManager(settings, db)
    approved, reason = await rm.check("long", "wrongsecret", hour_est=10)
    assert approved is False
    assert reason == RejectionReason.INVALID_SECRET

@pytest.mark.asyncio
async def test_rejects_when_in_position(settings):
    db = AsyncMock()
    db.get_state.return_value = make_state(in_position=True)
    rm = RiskManager(settings, db)
    approved, reason = await rm.check("long", "ws", hour_est=10)
    assert approved is False
    assert reason == RejectionReason.IN_POSITION

@pytest.mark.asyncio
async def test_rejects_when_max_losses_reached(settings):
    db = AsyncMock()
    db.get_state.return_value = make_state(daily_losses=2)
    rm = RiskManager(settings, db)
    approved, reason = await rm.check("long", "ws", hour_est=10)
    assert approved is False
    assert reason == RejectionReason.MAX_LOSSES

@pytest.mark.asyncio
async def test_rejects_when_max_trades_reached(settings):
    db = AsyncMock()
    db.get_state.return_value = make_state(daily_trades=5)
    rm = RiskManager(settings, db)
    approved, reason = await rm.check("long", "ws", hour_est=10)
    assert approved is False
    assert reason == RejectionReason.MAX_TRADES

@pytest.mark.asyncio
async def test_rejects_after_cutoff_time(settings):
    db = AsyncMock()
    db.get_state.return_value = make_state()
    rm = RiskManager(settings, db)
    approved, reason = await rm.check("long", "ws", hour_est=16, minute_est=31)
    assert approved is False
    assert reason == RejectionReason.AFTER_CUTOFF
