import pytest
import respx
import httpx

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
    monkeypatch.setenv("TRADOVATE_ACCOUNT_ID", "99999")
    monkeypatch.setenv("TRADOVATE_ACCOUNT_SPEC", "u@firm")
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

@pytest.fixture
def client(settings):
    from broker.tradovate import TradovateClient
    c = TradovateClient(settings)
    c.access_token = "token123"
    return c

@pytest.mark.asyncio
@respx.mock
async def test_place_market_order_buy(client):
    respx.post("https://demo.tradovateapi.com/v1/order/placeorder").mock(
        return_value=httpx.Response(200, json={"orderId": 111, "fillPrice": 19850.25, "filled": 3})
    )
    result = await client.place_market_order("MNQM5", "Buy", 3)
    assert result.order_id == "111"
    assert result.fill_price == 19850.25
    assert result.contracts == 3
    assert result.status == "filled"

@pytest.mark.asyncio
@respx.mock
async def test_place_stop_order(client):
    respx.post("https://demo.tradovateapi.com/v1/order/placeorder").mock(
        return_value=httpx.Response(200, json={"orderId": 222})
    )
    order_id = await client.place_stop_order("MNQM5", "Sell", 3, 19790.25)
    assert order_id == "222"

@pytest.mark.asyncio
@respx.mock
async def test_get_quote(client):
    respx.get("https://demo.tradovateapi.com/v1/quote/find").mock(
        return_value=httpx.Response(200, json={"entries": {"Last": {"price": 19860.5}}})
    )
    price = await client.get_quote("MNQM5")
    assert price == 19860.5

@pytest.mark.asyncio
@respx.mock
async def test_close_position(client):
    respx.post("https://demo.tradovateapi.com/v1/order/liquidateposition").mock(
        return_value=httpx.Response(200, json={"orderId": 333})
    )
    await client.close_position("MNQM5")

@pytest.mark.asyncio
@respx.mock
async def test_cancel_order(client):
    respx.post("https://demo.tradovateapi.com/v1/order/cancelorder").mock(
        return_value=httpx.Response(200, json={})
    )
    await client.cancel_order("222")
