import pytest
import httpx
from unittest.mock import AsyncMock
from broker.base import OrderResult
from bot.risk_manager import RejectionReason
from bot.webhook import create_app


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
    monkeypatch.setenv("WEBHOOK_SECRET", "supersecret")
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


@pytest.fixture
def risk_manager():
    rm = AsyncMock()
    rm.check = AsyncMock(return_value=(True, None))
    return rm


@pytest.fixture
def order_manager():
    om = AsyncMock()
    om.open_position = AsyncMock(return_value=OrderResult(
        order_id="123", fill_price=20000.0, contracts=3, status="filled"
    ))
    return om


@pytest.fixture
def app(settings, risk_manager, order_manager):
    return create_app(settings, risk_manager, order_manager)


async def test_health_endpoint(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_signal_accepted(app, risk_manager, order_manager):
    risk_manager.check.return_value = (True, None)
    order_manager.open_position.return_value = OrderResult(
        order_id="123", fill_price=20000.0, contracts=3, status="filled"
    )

    payload = {"signal": "long", "symbol": "MNQM5", "price": 20000.0, "secret": "supersecret"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/signal", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["order_id"] == "123"
    assert data["fill_price"] == 20000.0
    order_manager.open_position.assert_awaited_once()


async def test_signal_rejected(app, risk_manager, order_manager):
    risk_manager.check.return_value = (False, RejectionReason.MAX_LOSSES)

    payload = {"signal": "long", "symbol": "MNQM5", "price": 20000.0, "secret": "supersecret"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/signal", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert data["reason"] == "max_daily_losses_reached"
    order_manager.open_position.assert_not_awaited()


async def test_signal_invalid_json(app):
    # Missing required 'secret' field → 422 Unprocessable Entity
    payload = {"signal": "long", "symbol": "MNQM5", "price": 20000.0}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/signal", json=payload)

    assert response.status_code == 422
