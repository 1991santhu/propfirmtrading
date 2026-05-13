import os
import pytest

def test_config_loads_required_fields(monkeypatch):
    monkeypatch.setenv("TRADOVATE_USERNAME", "testuser")
    monkeypatch.setenv("TRADOVATE_PASSWORD", "testpass")
    monkeypatch.setenv("TRADOVATE_APP_ID", "MyApp")
    monkeypatch.setenv("TRADOVATE_APP_VERSION", "1.0")
    monkeypatch.setenv("TRADOVATE_CLIENT_ID", "12345")
    monkeypatch.setenv("TRADOVATE_SECRET", "secret")
    monkeypatch.setenv("TRADOVATE_DEVICE_ID", "device1")
    monkeypatch.setenv("TRADOVATE_ENV", "demo")
    monkeypatch.setenv("TRADOVATE_ACCOUNT_ID", "99999")
    monkeypatch.setenv("TRADOVATE_ACCOUNT_SPEC", "testuser@firm")
    monkeypatch.setenv("WEBHOOK_SECRET", "webhooksecret")
    monkeypatch.setenv("SYMBOL", "MNQM5")
    monkeypatch.setenv("CONTRACTS", "3")
    monkeypatch.setenv("STOP_POINTS", "60")
    monkeypatch.setenv("MAX_DAILY_LOSSES", "2")
    monkeypatch.setenv("MAX_DAILY_TRADES", "5")
    monkeypatch.setenv("CLOSE_HOUR_EST", "16")
    monkeypatch.setenv("CLOSE_MINUTE_EST", "40")

    import importlib
    import config as cfg_module
    importlib.reload(cfg_module)
    from config import Settings
    s = Settings()
    assert s.tradovate_username == "testuser"
    assert s.symbol == "MNQM5"
    assert s.contracts == 3
    assert s.stop_points == 60
    assert s.max_daily_losses == 2
    assert s.max_daily_trades == 5
    assert s.tradovate_env == "demo"
    assert s.base_url == "https://demo.tradovateapi.com/v1"
    assert s.ws_url == "wss://demo.tradovateapi.com/v1/websocket"

def test_config_live_urls(monkeypatch):
    monkeypatch.setenv("TRADOVATE_USERNAME", "u")
    monkeypatch.setenv("TRADOVATE_PASSWORD", "p")
    monkeypatch.setenv("TRADOVATE_APP_ID", "a")
    monkeypatch.setenv("TRADOVATE_APP_VERSION", "1.0")
    monkeypatch.setenv("TRADOVATE_CLIENT_ID", "1")
    monkeypatch.setenv("TRADOVATE_SECRET", "s")
    monkeypatch.setenv("TRADOVATE_DEVICE_ID", "d")
    monkeypatch.setenv("TRADOVATE_ENV", "live")
    monkeypatch.setenv("TRADOVATE_ACCOUNT_ID", "1")
    monkeypatch.setenv("TRADOVATE_ACCOUNT_SPEC", "u@f")
    monkeypatch.setenv("WEBHOOK_SECRET", "w")
    monkeypatch.setenv("SYMBOL", "MNQM5")
    monkeypatch.setenv("CONTRACTS", "3")
    monkeypatch.setenv("STOP_POINTS", "60")
    monkeypatch.setenv("MAX_DAILY_LOSSES", "2")
    monkeypatch.setenv("MAX_DAILY_TRADES", "5")
    monkeypatch.setenv("CLOSE_HOUR_EST", "16")
    monkeypatch.setenv("CLOSE_MINUTE_EST", "40")

    import importlib
    import config as cfg_module
    importlib.reload(cfg_module)
    from config import Settings
    s = Settings()
    assert s.base_url == "https://live.tradovateapi.com/v1"
    assert s.ws_url == "wss://live.tradovateapi.com/v1/websocket"
