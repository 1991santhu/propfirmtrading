import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from broker.base import OrderResult
from bot.order_manager import OrderManager


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
    monkeypatch.setenv("STOP_POINTS", "30")
    monkeypatch.setenv("MAX_DAILY_LOSSES", "2")
    monkeypatch.setenv("MAX_DAILY_TRADES", "5")
    monkeypatch.setenv("CLOSE_HOUR_EST", "16")
    monkeypatch.setenv("CLOSE_MINUTE_EST", "40")
    import importlib, config as cfg
    importlib.reload(cfg)
    from config import Settings
    return Settings()


@pytest.fixture
def broker():
    b = AsyncMock()
    b.place_market_order = AsyncMock(return_value=OrderResult(
        order_id="1", fill_price=20000.0, contracts=3, status="filled"
    ))
    b.place_stop_order = AsyncMock(return_value="stop-order-42")
    b.close_position = AsyncMock()
    return b


@pytest.fixture
def db():
    d = AsyncMock()
    d.set_position = AsyncMock()
    d.increment_daily_trades = AsyncMock()
    d.clear_position = AsyncMock()
    d.get_state = AsyncMock(return_value={"in_position": True})
    return d


@pytest.fixture
def tracker(settings, broker, db):
    from bot.position_tracker import PositionTracker
    from unittest.mock import MagicMock
    pt = PositionTracker(settings, broker, db)
    pt.start = AsyncMock()
    pt.stop = MagicMock()
    return pt


async def test_open_long_position(settings, broker, db, tracker):
    with patch("asyncio.create_task") as mock_create_task:
        om = OrderManager(settings, broker, db, tracker)
        result = await om.open_position("long", price_hint=20000.0)

    # Returns the OrderResult from market order
    assert result.order_id == "1"
    assert result.fill_price == 20000.0
    assert result.contracts == 3
    assert result.status == "filled"

    # Market order placed correctly (long = "Buy")
    broker.place_market_order.assert_awaited_once_with("MNQM5", "Buy", 3)

    # Stop placed at entry - stop_points = 20000.0 - 30 = 19970.0, action "Sell"
    broker.place_stop_order.assert_awaited_once_with("MNQM5", "Sell", 3, 19970.0)

    # set_position called with correct dict
    db.set_position.assert_awaited_once_with({
        "side": "long",
        "entry_price": 20000.0,
        "stop_price": 19970.0,
        "contracts": 3,
        "milestone": 0,
    })

    # increment_daily_trades called
    db.increment_daily_trades.assert_awaited_once()

    # tracker.start wrapped in asyncio.create_task
    mock_create_task.assert_called_once()


async def test_open_short_position(settings, broker, db, tracker):
    broker.place_market_order = AsyncMock(return_value=OrderResult(
        order_id="2", fill_price=20000.0, contracts=3, status="filled"
    ))
    broker.place_stop_order = AsyncMock(return_value="stop-order-99")

    with patch("asyncio.create_task") as mock_create_task:
        om = OrderManager(settings, broker, db, tracker)
        result = await om.open_position("short", price_hint=20000.0)

    # Returns the OrderResult
    assert result.order_id == "2"

    # Market order placed with "Sell" for short
    broker.place_market_order.assert_awaited_once_with("MNQM5", "Sell", 3)

    # Stop placed at entry + stop_points = 20000.0 + 30 = 20030.0, action "Buy"
    broker.place_stop_order.assert_awaited_once_with("MNQM5", "Buy", 3, 20030.0)

    # set_position with short side
    db.set_position.assert_awaited_once_with({
        "side": "short",
        "entry_price": 20000.0,
        "stop_price": 20030.0,
        "contracts": 3,
        "milestone": 0,
    })

    db.increment_daily_trades.assert_awaited_once()
    mock_create_task.assert_called_once()


async def test_close_position_eod_when_in_position(settings, broker, db, tracker):
    db.get_state = AsyncMock(return_value={"in_position": True})

    om = OrderManager(settings, broker, db, tracker)
    await om.close_position_eod()

    broker.close_position.assert_awaited_once_with("MNQM5")
    db.clear_position.assert_awaited_once_with(0)
    tracker.stop.assert_called_once()


async def test_close_position_eod_when_not_in_position(settings, broker, db, tracker):
    db.get_state = AsyncMock(return_value={"in_position": False})

    om = OrderManager(settings, broker, db, tracker)
    await om.close_position_eod()

    broker.close_position.assert_not_awaited()
    db.clear_position.assert_not_awaited()
