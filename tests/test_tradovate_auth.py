import pytest
import respx
import httpx

@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("TRADOVATE_USERNAME", "testuser")
    monkeypatch.setenv("TRADOVATE_PASSWORD", "testpass")
    monkeypatch.setenv("TRADOVATE_APP_ID", "MyApp")
    monkeypatch.setenv("TRADOVATE_APP_VERSION", "1.0")
    monkeypatch.setenv("TRADOVATE_CLIENT_ID", "123")
    monkeypatch.setenv("TRADOVATE_SECRET", "secret")
    monkeypatch.setenv("TRADOVATE_DEVICE_ID", "device1")
    monkeypatch.setenv("TRADOVATE_ENV", "demo")
    monkeypatch.setenv("TRADOVATE_ACCOUNT_ID", "99999")
    monkeypatch.setenv("TRADOVATE_ACCOUNT_SPEC", "testuser@firm")
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
@respx.mock
async def test_authenticate_success(settings):
    respx.post("https://demo.tradovateapi.com/v1/auth/accesstokenrequest").mock(
        return_value=httpx.Response(200, json={
            "accessToken": "token123",
            "expirationTime": "2026-05-13T15:00:00Z"
        })
    )
    from broker.tradovate import TradovateClient
    client = TradovateClient(settings)
    await client.authenticate()
    assert client.access_token == "token123"

@pytest.mark.asyncio
@respx.mock
async def test_authenticate_failure_raises(settings):
    respx.post("https://demo.tradovateapi.com/v1/auth/accesstokenrequest").mock(
        return_value=httpx.Response(401, json={"errorText": "invalid credentials"})
    )
    from broker.tradovate import TradovateClient
    client = TradovateClient(settings)
    with pytest.raises(RuntimeError, match="Authentication failed"):
        await client.authenticate()
