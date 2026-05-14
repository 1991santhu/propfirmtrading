# PropFirm Trading Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated /MNQ futures trading bot that receives TradingView webhook signals, enforces all risk rules, and executes partial exit / trailing stop strategies on a LucidTrading LucidFlex 50k account via Tradovate.

**Architecture:** TradingView fires a JSON webhook → FastAPI bot validates signal against risk rules → places bracket order on Tradovate with hard 60-point stop → monitors price milestones and executes partial exits + trails stop ladder automatically → force-closes all positions at 4:40 PM EST.

**Tech Stack:** Python 3.11+, FastAPI, httpx, websockets, APScheduler, SQLite (via aiosqlite), pytest, python-dotenv

---

## File Map

```
propfirm_trading/
├── .env.template              # all config keys with descriptions
├── .env                       # actual secrets (never committed)
├── .gitignore
├── Dockerfile
├── requirements.txt
├── main.py                    # entry point — wires all components
├── config.py                  # loads .env, typed settings
├── broker/
│   ├── __init__.py
│   ├── base.py                # BrokerClient abstract interface
│   └── tradovate.py           # Tradovate implementation of BrokerClient
├── bot/
│   ├── __init__.py
│   ├── webhook.py             # FastAPI app + /signal endpoint
│   ├── risk_manager.py        # all pre-trade rule checks
│   ├── order_manager.py       # orchestrates entry/exit flow
│   ├── position_tracker.py    # milestone detection + stop ladder
│   └── scheduler.py           # 4:40 PM close, 9:30 AM reset
├── db/
│   ├── __init__.py
│   └── state.py               # SQLite read/write for bot state
└── tests/
    ├── conftest.py
    ├── test_config.py
    ├── test_state.py
    ├── test_risk_manager.py
    ├── test_position_tracker.py
    ├── test_order_manager.py
    └── test_webhook.py
```

---

## Task 1: Project Setup

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `.env.template`
- Create: `Dockerfile`

- [ ] **Step 1: Create `.gitignore`**

```
.env
__pycache__/
*.pyc
*.db
logs/
.pytest_cache/
```

- [ ] **Step 2: Create `requirements.txt`**

```
fastapi==0.115.0
uvicorn==0.30.0
httpx==0.27.0
websockets==12.0
apscheduler==3.10.4
aiosqlite==0.20.0
python-dotenv==1.0.1
pytest==8.2.0
pytest-asyncio==0.23.7
respx==0.21.1
```

- [ ] **Step 3: Create `.env.template`**

```
# Tradovate credentials
TRADOVATE_USERNAME=your_username
TRADOVATE_PASSWORD=your_password
TRADOVATE_APP_ID=your_app_id
TRADOVATE_APP_VERSION=1.0
TRADOVATE_CLIENT_ID=your_numeric_client_id
TRADOVATE_SECRET=your_secret
TRADOVATE_DEVICE_ID=your_device_id

# Use 'demo' for testing, 'live' for real money
TRADOVATE_ENV=demo

# Your Tradovate account details (found in account dashboard)
TRADOVATE_ACCOUNT_ID=your_numeric_account_id
TRADOVATE_ACCOUNT_SPEC=your_username@your_firm

# Bot config
WEBHOOK_SECRET=choose_a_long_random_string
SYMBOL=MNQM5
CONTRACTS=3
STOP_POINTS=60
MAX_DAILY_LOSSES=2
MAX_DAILY_TRADES=5
CLOSE_HOUR_EST=16
CLOSE_MINUTE_EST=40
```

- [ ] **Step 4: Create `Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

- [ ] **Step 5: Install dependencies**

```bash
cd /Users/ssomarapu/propfirm_trading
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Expected: All packages install without errors.

- [ ] **Step 6: Copy `.env.template` to `.env` and fill in values**

```bash
cp .env.template .env
```

Then edit `.env` with your actual Tradovate credentials from your Tradovate dashboard under Settings → API Access.

- [ ] **Step 7: Commit**

```bash
git init
git add .gitignore requirements.txt .env.template Dockerfile
git commit -m "chore: project setup"
```

---

## Task 2: Config Module

**Files:**
- Create: `config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
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

    import importlib, config
    importlib.reload(config)
    from config import Settings
    s = Settings()
    assert s.base_url == "https://live.tradovateapi.com/v1"
    assert s.ws_url == "wss://live.tradovateapi.com/v1/websocket"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_config.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Implement `config.py`**

```python
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.tradovate_username = os.environ["TRADOVATE_USERNAME"]
        self.tradovate_password = os.environ["TRADOVATE_PASSWORD"]
        self.tradovate_app_id = os.environ["TRADOVATE_APP_ID"]
        self.tradovate_app_version = os.environ["TRADOVATE_APP_VERSION"]
        self.tradovate_client_id = int(os.environ["TRADOVATE_CLIENT_ID"])
        self.tradovate_secret = os.environ["TRADOVATE_SECRET"]
        self.tradovate_device_id = os.environ["TRADOVATE_DEVICE_ID"]
        self.tradovate_env = os.environ["TRADOVATE_ENV"]
        self.account_id = int(os.environ["TRADOVATE_ACCOUNT_ID"])
        self.account_spec = os.environ["TRADOVATE_ACCOUNT_SPEC"]
        self.webhook_secret = os.environ["WEBHOOK_SECRET"]
        self.symbol = os.environ["SYMBOL"]
        self.contracts = int(os.environ["CONTRACTS"])
        self.stop_points = int(os.environ["STOP_POINTS"])
        self.max_daily_losses = int(os.environ["MAX_DAILY_LOSSES"])
        self.max_daily_trades = int(os.environ["MAX_DAILY_TRADES"])
        self.close_hour_est = int(os.environ["CLOSE_HOUR_EST"])
        self.close_minute_est = int(os.environ["CLOSE_MINUTE_EST"])

        if self.tradovate_env == "live":
            self.base_url = "https://live.tradovateapi.com/v1"
            self.ws_url = "wss://live.tradovateapi.com/v1/websocket"
        else:
            self.base_url = "https://demo.tradovateapi.com/v1"
            self.ws_url = "wss://demo.tradovateapi.com/v1/websocket"

settings = Settings()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_config.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: config module with typed settings"
```

---

## Task 3: State Management (SQLite)

**Files:**
- Create: `db/__init__.py`
- Create: `db/state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_state.py
import pytest
import asyncio
from db.state import StateDB

@pytest.fixture
async def db(tmp_path):
    database = StateDB(db_path=str(tmp_path / "test.db"))
    await database.init()
    yield database
    await database.close()

@pytest.mark.asyncio
async def test_initial_state(db):
    state = await db.get_state()
    assert state["daily_losses"] == 0
    assert state["daily_trades"] == 0
    assert state["in_position"] == False
    assert state["daily_pnl"] == 0.0
    assert state["total_pnl"] == 0.0
    assert state["position"] is None

@pytest.mark.asyncio
async def test_increment_daily_losses(db):
    await db.increment_daily_losses()
    await db.increment_daily_losses()
    state = await db.get_state()
    assert state["daily_losses"] == 2

@pytest.mark.asyncio
async def test_increment_daily_trades(db):
    await db.increment_daily_trades()
    state = await db.get_state()
    assert state["daily_trades"] == 1

@pytest.mark.asyncio
async def test_set_position(db):
    pos = {"contracts": 3, "entry_price": 19850.0, "stop_price": 19790.0, "milestone": 0}
    await db.set_position(pos)
    state = await db.get_state()
    assert state["in_position"] == True
    assert state["position"]["entry_price"] == 19850.0
    assert state["position"]["milestone"] == 0

@pytest.mark.asyncio
async def test_clear_position(db):
    pos = {"contracts": 3, "entry_price": 19850.0, "stop_price": 19790.0, "milestone": 0}
    await db.set_position(pos)
    await db.clear_position(pnl=600.0)
    state = await db.get_state()
    assert state["in_position"] == False
    assert state["position"] is None
    assert state["daily_pnl"] == 600.0
    assert state["total_pnl"] == 600.0

@pytest.mark.asyncio
async def test_update_milestone(db):
    pos = {"contracts": 3, "entry_price": 19850.0, "stop_price": 19790.0, "milestone": 0}
    await db.set_position(pos)
    await db.update_milestone(milestone=1, new_stop=19850.0, contracts_remaining=2)
    state = await db.get_state()
    assert state["position"]["milestone"] == 1
    assert state["position"]["stop_price"] == 19850.0
    assert state["position"]["contracts"] == 2

@pytest.mark.asyncio
async def test_reset_daily(db):
    await db.increment_daily_losses()
    await db.increment_daily_trades()
    await db.reset_daily()
    state = await db.get_state()
    assert state["daily_losses"] == 0
    assert state["daily_trades"] == 0
    assert state["daily_pnl"] == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_state.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'db'`

- [ ] **Step 3: Create `db/__init__.py`**

```python
```

- [ ] **Step 4: Implement `db/state.py`**

```python
import json
import aiosqlite

class StateDB:
    def __init__(self, db_path: str = "bot_state.db"):
        self.db_path = db_path
        self._conn = None

    async def init(self):
        self._conn = await aiosqlite.connect(self.db_path)
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        await self._conn.commit()
        await self._ensure_defaults()

    async def _ensure_defaults(self):
        defaults = {
            "daily_losses": "0",
            "daily_trades": "0",
            "in_position": "false",
            "daily_pnl": "0.0",
            "total_pnl": "0.0",
            "position": "null",
        }
        for key, value in defaults.items():
            await self._conn.execute(
                "INSERT OR IGNORE INTO state (key, value) VALUES (?, ?)",
                (key, value)
            )
        await self._conn.commit()

    async def _get(self, key: str):
        async with self._conn.execute("SELECT value FROM state WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return json.loads(row[0]) if row else None

    async def _set(self, key: str, value):
        await self._conn.execute(
            "INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)",
            (key, json.dumps(value))
        )
        await self._conn.commit()

    async def get_state(self) -> dict:
        return {
            "daily_losses": await self._get("daily_losses"),
            "daily_trades": await self._get("daily_trades"),
            "in_position": await self._get("in_position"),
            "daily_pnl": await self._get("daily_pnl"),
            "total_pnl": await self._get("total_pnl"),
            "position": await self._get("position"),
        }

    async def increment_daily_losses(self):
        current = await self._get("daily_losses")
        await self._set("daily_losses", current + 1)

    async def increment_daily_trades(self):
        current = await self._get("daily_trades")
        await self._set("daily_trades", current + 1)

    async def set_position(self, position: dict):
        await self._set("position", position)
        await self._set("in_position", True)

    async def clear_position(self, pnl: float):
        await self._set("position", None)
        await self._set("in_position", False)
        daily = await self._get("daily_pnl")
        total = await self._get("total_pnl")
        await self._set("daily_pnl", daily + pnl)
        await self._set("total_pnl", total + pnl)

    async def update_milestone(self, milestone: int, new_stop: float, contracts_remaining: int):
        pos = await self._get("position")
        pos["milestone"] = milestone
        pos["stop_price"] = new_stop
        pos["contracts"] = contracts_remaining
        await self._set("position", pos)

    async def reset_daily(self):
        await self._set("daily_losses", 0)
        await self._set("daily_trades", 0)
        await self._set("daily_pnl", 0.0)

    async def close(self):
        if self._conn:
            await self._conn.close()
```

- [ ] **Step 5: Add `conftest.py`**

```python
# tests/conftest.py
import pytest

pytest_plugins = ["pytest_asyncio"]
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_state.py -v
```

Expected: All 7 tests PASS

- [ ] **Step 7: Commit**

```bash
git add db/ tests/test_state.py tests/conftest.py
git commit -m "feat: SQLite state management"
```

---

## Task 4: Broker Abstraction Interface

**Files:**
- Create: `broker/__init__.py`
- Create: `broker/base.py`

- [ ] **Step 1: Create `broker/__init__.py`**

```python
```

- [ ] **Step 2: Implement `broker/base.py`**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class OrderResult:
    order_id: str
    fill_price: float
    contracts: int
    status: str  # "filled", "pending", "rejected"

@dataclass
class PositionResult:
    contracts: int
    entry_price: float
    current_price: float
    unrealized_pnl: float
    side: str  # "long" or "short"

class BrokerClient(ABC):

    @abstractmethod
    async def authenticate(self) -> None:
        """Authenticate with the broker. Must be called before any other method."""
        pass

    @abstractmethod
    async def place_market_order(self, symbol: str, action: str, contracts: int) -> OrderResult:
        """Place a market order. action is 'Buy' or 'Sell'."""
        pass

    @abstractmethod
    async def place_stop_order(self, symbol: str, action: str, contracts: int, stop_price: float) -> str:
        """Place a stop order. Returns order_id."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> None:
        """Cancel an open order by order_id."""
        pass

    @abstractmethod
    async def get_quote(self, symbol: str) -> float:
        """Get current last price for symbol."""
        pass

    @abstractmethod
    async def close_position(self, symbol: str) -> None:
        """Liquidate entire position for symbol immediately."""
        pass

    @abstractmethod
    async def modify_stop(self, order_id: str, new_stop_price: float, contracts: int) -> str:
        """Cancel existing stop and place new stop. Returns new order_id."""
        pass
```

- [ ] **Step 3: Commit**

```bash
git add broker/
git commit -m "feat: broker abstraction interface"
```

---

## Task 5: Tradovate Authentication

**Files:**
- Create: `broker/tradovate.py`
- Create: `tests/test_tradovate_auth.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tradovate_auth.py
import pytest
import respx
import httpx
from config import Settings
from broker.tradovate import TradovateClient

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
    client = TradovateClient(settings)
    await client.authenticate()
    assert client.access_token == "token123"

@pytest.mark.asyncio
@respx.mock
async def test_authenticate_failure_raises(settings):
    respx.post("https://demo.tradovateapi.com/v1/auth/accesstokenrequest").mock(
        return_value=httpx.Response(401, json={"errorText": "invalid credentials"})
    )
    client = TradovateClient(settings)
    with pytest.raises(RuntimeError, match="Authentication failed"):
        await client.authenticate()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_tradovate_auth.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'broker.tradovate'`

- [ ] **Step 3: Implement `broker/tradovate.py` (auth only)**

```python
import asyncio
import httpx
from broker.base import BrokerClient, OrderResult

class TradovateClient(BrokerClient):

    def __init__(self, settings):
        self.settings = settings
        self.access_token: str | None = None
        self._http = httpx.AsyncClient()

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def authenticate(self) -> None:
        payload = {
            "name": self.settings.tradovate_username,
            "password": self.settings.tradovate_password,
            "appId": self.settings.tradovate_app_id,
            "appVersion": self.settings.tradovate_app_version,
            "cid": self.settings.tradovate_client_id,
            "sec": self.settings.tradovate_secret,
            "deviceId": self.settings.tradovate_device_id,
        }
        resp = await self._http.post(
            f"{self.settings.base_url}/auth/accesstokenrequest",
            json=payload
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Authentication failed: {resp.text}")
        data = resp.json()
        self.access_token = data["accessToken"]

    # Stub remaining interface methods — implemented in Task 6
    async def place_market_order(self, symbol, action, contracts): raise NotImplementedError
    async def place_stop_order(self, symbol, action, contracts, stop_price): raise NotImplementedError
    async def cancel_order(self, order_id): raise NotImplementedError
    async def get_quote(self, symbol): raise NotImplementedError
    async def close_position(self, symbol): raise NotImplementedError
    async def modify_stop(self, order_id, new_stop_price, contracts): raise NotImplementedError
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_tradovate_auth.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add broker/tradovate.py tests/test_tradovate_auth.py
git commit -m "feat: Tradovate authentication"
```

---

## Task 6: Tradovate Order Execution

**Files:**
- Modify: `broker/tradovate.py`
- Create: `tests/test_tradovate_orders.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_tradovate_orders.py
import pytest
import respx
import httpx
from broker.tradovate import TradovateClient

@pytest.fixture
def client(settings):
    c = TradovateClient(settings)
    c.access_token = "token123"
    return c

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
    from config import Settings
    return Settings()

@pytest.mark.asyncio
@respx.mock
async def test_place_market_order_buy(client):
    respx.post("https://demo.tradovateapi.com/v1/order/placeorder").mock(
        return_value=httpx.Response(200, json={
            "orderId": 111,
            "fillPrice": 19850.25,
            "filled": 3
        })
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_tradovate_orders.py -v
```

Expected: FAIL with `NotImplementedError`

- [ ] **Step 3: Implement order methods in `broker/tradovate.py`**

Replace the stub methods with full implementations:

```python
    async def place_market_order(self, symbol: str, action: str, contracts: int) -> OrderResult:
        payload = {
            "accountSpec": self.settings.account_spec,
            "accountId": self.settings.account_id,
            "action": action,
            "symbol": symbol,
            "orderQty": contracts,
            "orderType": "Market",
            "isAutomated": True,
        }
        resp = await self._http.post(
            f"{self.settings.base_url}/order/placeorder",
            json=payload,
            headers=self._headers()
        )
        resp.raise_for_status()
        data = resp.json()
        return OrderResult(
            order_id=str(data["orderId"]),
            fill_price=data.get("fillPrice", 0.0),
            contracts=data.get("filled", contracts),
            status="filled" if data.get("fillPrice") else "pending"
        )

    async def place_stop_order(self, symbol: str, action: str, contracts: int, stop_price: float) -> str:
        payload = {
            "accountSpec": self.settings.account_spec,
            "accountId": self.settings.account_id,
            "action": action,
            "symbol": symbol,
            "orderQty": contracts,
            "orderType": "Stop",
            "stopPrice": stop_price,
            "isAutomated": True,
        }
        resp = await self._http.post(
            f"{self.settings.base_url}/order/placeorder",
            json=payload,
            headers=self._headers()
        )
        resp.raise_for_status()
        return str(resp.json()["orderId"])

    async def cancel_order(self, order_id: str) -> None:
        resp = await self._http.post(
            f"{self.settings.base_url}/order/cancelorder",
            json={"orderId": int(order_id)},
            headers=self._headers()
        )
        resp.raise_for_status()

    async def get_quote(self, symbol: str) -> float:
        resp = await self._http.get(
            f"{self.settings.base_url}/quote/find",
            params={"name": symbol},
            headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()["entries"]["Last"]["price"]

    async def close_position(self, symbol: str) -> None:
        resp = await self._http.post(
            f"{self.settings.base_url}/order/liquidateposition",
            json={
                "accountId": self.settings.account_id,
                "symbol": symbol,
                "isAutomated": True,
            },
            headers=self._headers()
        )
        resp.raise_for_status()

    async def modify_stop(self, order_id: str, new_stop_price: float, contracts: int) -> str:
        await self.cancel_order(order_id)
        # Determine action: if we're long we need a Sell stop, if short a Buy stop
        # Position side is tracked externally — caller passes correct action via separate method
        # For now, close_position handles full exit; this is called by position tracker
        raise NotImplementedError("Use cancel_order + place_stop_order separately")
```

- [ ] **Step 4: Fix `modify_stop` — position tracker calls cancel + place directly**

Update the interface in `broker/base.py` — remove `modify_stop`, add note:

```python
    # Note: to modify a stop, call cancel_order() then place_stop_order()
    # This keeps each method single-purpose and avoids needing to know position side here
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_tradovate_orders.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add broker/tradovate.py tests/test_tradovate_orders.py
git commit -m "feat: Tradovate order execution methods"
```

---

## Task 7: Risk Manager

**Files:**
- Create: `bot/__init__.py`
- Create: `bot/risk_manager.py`
- Create: `tests/test_risk_manager.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_risk_manager.py
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
    from config import Settings
    return Settings()

@pytest.mark.asyncio
async def test_allows_valid_signal(settings):
    db = AsyncMock()
    db.get_state.return_value = make_state()
    rm = RiskManager(settings, db)
    approved, reason = await rm.check("long", "webhooksecret", hour_est=10)
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_risk_manager.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `bot/__init__.py`**

```python
```

- [ ] **Step 4: Implement `bot/risk_manager.py`**

```python
from enum import Enum

class RejectionReason(Enum):
    INVALID_SECRET = "invalid_secret"
    IN_POSITION = "already_in_position"
    MAX_LOSSES = "max_daily_losses_reached"
    MAX_TRADES = "max_daily_trades_reached"
    AFTER_CUTOFF = "after_cutoff_time"

class RiskManager:

    def __init__(self, settings, db):
        self.settings = settings
        self.db = db

    async def check(
        self,
        signal: str,
        secret: str,
        hour_est: int,
        minute_est: int = 0
    ) -> tuple[bool, RejectionReason | None]:

        if secret != self.settings.webhook_secret:
            return False, RejectionReason.INVALID_SECRET

        state = await self.db.get_state()

        if state["in_position"]:
            return False, RejectionReason.IN_POSITION

        if state["daily_losses"] >= self.settings.max_daily_losses:
            return False, RejectionReason.MAX_LOSSES

        if state["daily_trades"] >= self.settings.max_daily_trades:
            return False, RejectionReason.MAX_TRADES

        cutoff_minutes = self.settings.close_hour_est * 60 + self.settings.close_minute_est - 10
        current_minutes = hour_est * 60 + minute_est
        if current_minutes >= cutoff_minutes:
            return False, RejectionReason.AFTER_CUTOFF

        return True, None
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_risk_manager.py -v
```

Expected: All 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git add bot/__init__.py bot/risk_manager.py tests/test_risk_manager.py
git commit -m "feat: risk manager with all pre-trade rule checks"
```

---

## Task 8: Position Tracker (Partial Exits + Stop Ladder)

**Files:**
- Create: `bot/position_tracker.py`
- Create: `tests/test_position_tracker.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_position_tracker.py
import pytest
from unittest.mock import AsyncMock, MagicMock
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
    from config import Settings
    settings = Settings()
    broker = AsyncMock()
    db = AsyncMock()
    return settings, broker, db

def test_calculate_stop_price_long(setup):
    settings, broker, db = setup
    pt = PositionTracker(settings, broker, db)
    stop = pt.calculate_stop_price("long", entry=19850.0)
    assert stop == 19790.0  # 19850 - 60

def test_calculate_stop_price_short(setup):
    settings, broker, db = setup
    pt = PositionTracker(settings, broker, db)
    stop = pt.calculate_stop_price("short", entry=19850.0)
    assert stop == 19910.0  # 19850 + 60

def test_milestone_thresholds_long(setup):
    settings, broker, db = setup
    pt = PositionTracker(settings, broker, db)
    assert pt.milestone_price("long", entry=19850.0, milestone=1) == 19910.0  # +60
    assert pt.milestone_price("long", entry=19850.0, milestone=2) == 19970.0  # +120
    assert pt.milestone_price("long", entry=19850.0, milestone=3) == 20030.0  # +180

def test_milestone_thresholds_short(setup):
    settings, broker, db = setup
    pt = PositionTracker(settings, broker, db)
    assert pt.milestone_price("short", entry=19850.0, milestone=1) == 19790.0  # -60
    assert pt.milestone_price("short", entry=19850.0, milestone=2) == 19730.0  # -120

def test_new_stop_at_milestone_long(setup):
    settings, broker, db = setup
    pt = PositionTracker(settings, broker, db)
    # At milestone 1, stop moves to entry (breakeven)
    assert pt.stop_at_milestone("long", entry=19850.0, milestone=1) == 19850.0
    # At milestone 2, stop moves to entry + 1R
    assert pt.stop_at_milestone("long", entry=19850.0, milestone=2) == 19910.0
    # At milestone 3, stop moves to entry + 2R
    assert pt.stop_at_milestone("long", entry=19850.0, milestone=3) == 19970.0

@pytest.mark.asyncio
async def test_contracts_to_close_at_milestone(setup):
    settings, broker, db = setup
    pt = PositionTracker(settings, broker, db)
    # 3 contracts: 20% = 0.6 → 1 contract at milestones 1 and 2
    assert pt.contracts_to_close(total_contracts=3, milestone=1) == 1
    assert pt.contracts_to_close(total_contracts=3, milestone=2) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_position_tracker.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `bot/position_tracker.py`**

```python
import asyncio
import logging

logger = logging.getLogger(__name__)

class PositionTracker:

    def __init__(self, settings, broker, db):
        self.settings = settings
        self.broker = broker
        self.db = db
        self._monitoring = False
        self._stop_order_id: str | None = None

    def calculate_stop_price(self, side: str, entry: float) -> float:
        if side == "long":
            return entry - self.settings.stop_points
        return entry + self.settings.stop_points

    def milestone_price(self, side: str, entry: float, milestone: int) -> float:
        offset = self.settings.stop_points * milestone
        if side == "long":
            return entry + offset
        return entry - offset

    def stop_at_milestone(self, side: str, entry: float, milestone: int) -> float:
        # Stop trails at current_milestone - 1R
        return self.milestone_price(side, entry, milestone - 1)

    def contracts_to_close(self, total_contracts: int, milestone: int) -> int:
        # 20% at milestones 1 and 2, rest trails
        if milestone in (1, 2):
            return max(1, round(total_contracts * 0.20))
        return 0

    async def start(self, side: str, entry_price: float, total_contracts: int, stop_order_id: str):
        self._monitoring = True
        self._stop_order_id = stop_order_id
        state = await self.db.get_state()
        position = state["position"]

        while self._monitoring:
            await asyncio.sleep(5)
            try:
                current_price = await self.broker.get_quote(self.settings.symbol)
                pos = (await self.db.get_state())["position"]
                if pos is None:
                    break
                milestone = pos["milestone"]
                next_milestone = milestone + 1
                next_price = self.milestone_price(side, entry_price, next_milestone)

                milestone_hit = (
                    (side == "long" and current_price >= next_price) or
                    (side == "short" and current_price <= next_price)
                )

                if milestone_hit:
                    await self._handle_milestone(
                        side, entry_price, next_milestone, pos["contracts"]
                    )
            except Exception as e:
                logger.error(f"Position tracker error: {e}")

    async def _handle_milestone(self, side: str, entry: float, milestone: int, contracts: int):
        to_close = self.contracts_to_close(contracts, milestone)
        close_action = "Sell" if side == "long" else "Buy"

        if to_close > 0:
            await self.broker.place_market_order(self.settings.symbol, close_action, to_close)
            contracts_remaining = contracts - to_close
        else:
            contracts_remaining = contracts

        new_stop = self.stop_at_milestone(side, entry, milestone)

        if self._stop_order_id:
            await self.broker.cancel_order(self._stop_order_id)

        stop_action = "Sell" if side == "long" else "Buy"
        self._stop_order_id = await self.broker.place_stop_order(
            self.settings.symbol, stop_action, contracts_remaining, new_stop
        )

        await self.db.update_milestone(milestone, new_stop, contracts_remaining)
        logger.info(f"Milestone {milestone} hit — closed {to_close}, stop now at {new_stop}")

    def stop(self):
        self._monitoring = False
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_position_tracker.py -v
```

Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add bot/position_tracker.py tests/test_position_tracker.py
git commit -m "feat: position tracker with partial exits and trailing stop ladder"
```

---

## Task 9: Order Manager (Orchestrator)

**Files:**
- Create: `bot/order_manager.py`
- Create: `tests/test_order_manager.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_order_manager.py
import pytest
from unittest.mock import AsyncMock, patch
from bot.order_manager import OrderManager

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
    from config import Settings
    from broker.base import OrderResult
    settings = Settings()
    broker = AsyncMock()
    broker.place_market_order.return_value = OrderResult("111", 19850.0, 3, "filled")
    broker.place_stop_order.return_value = "222"
    db = AsyncMock()
    return settings, broker, db

@pytest.mark.asyncio
async def test_execute_long_places_entry_and_stop(setup):
    settings, broker, db = setup
    tracker = AsyncMock()
    om = OrderManager(settings, broker, db, tracker)
    await om.execute("long")
    broker.place_market_order.assert_called_once_with("MNQM5", "Buy", 3)
    broker.place_stop_order.assert_called_once_with("MNQM5", "Sell", 3, 19790.0)
    db.set_position.assert_called_once()
    db.increment_daily_trades.assert_called_once()

@pytest.mark.asyncio
async def test_execute_short_places_correct_stop(setup):
    settings, broker, db = setup
    tracker = AsyncMock()
    om = OrderManager(settings, broker, db, tracker)
    await om.execute("short")
    broker.place_market_order.assert_called_once_with("MNQM5", "Sell", 3)
    broker.place_stop_order.assert_called_once_with("MNQM5", "Buy", 3, 19910.0)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_order_manager.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `bot/order_manager.py`**

```python
import asyncio
import logging
from bot.position_tracker import PositionTracker

logger = logging.getLogger(__name__)

class OrderManager:

    def __init__(self, settings, broker, db, tracker: PositionTracker):
        self.settings = settings
        self.broker = broker
        self.db = db
        self.tracker = tracker

    async def execute(self, side: str):
        action = "Buy" if side == "long" else "Sell"
        stop_action = "Sell" if side == "long" else "Buy"

        result = await self.broker.place_market_order(
            self.settings.symbol, action, self.settings.contracts
        )
        logger.info(f"Entry filled: {side} {result.contracts} @ {result.fill_price}")

        stop_price = self.tracker.calculate_stop_price(side, result.fill_price)
        stop_order_id = await self.broker.place_stop_order(
            self.settings.symbol, stop_action, result.contracts, stop_price
        )
        logger.info(f"Stop placed at {stop_price}, order_id={stop_order_id}")

        position = {
            "contracts": result.contracts,
            "entry_price": result.fill_price,
            "stop_price": stop_price,
            "milestone": 0,
            "side": side,
        }
        await self.db.set_position(position)
        await self.db.increment_daily_trades()

        asyncio.create_task(
            self.tracker.start(side, result.fill_price, result.contracts, stop_order_id)
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_order_manager.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bot/order_manager.py tests/test_order_manager.py
git commit -m "feat: order manager orchestrates entry, stop placement, and position tracking"
```

---

## Task 10: Scheduler

**Files:**
- Create: `bot/scheduler.py`
- Create: `tests/test_scheduler.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_scheduler.py
import pytest
from unittest.mock import AsyncMock, patch
from bot.scheduler import BotScheduler

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
    from config import Settings
    settings = Settings()
    broker = AsyncMock()
    db = AsyncMock()
    tracker = AsyncMock()
    return settings, broker, db, tracker

@pytest.mark.asyncio
async def test_eod_close_calls_close_position_when_in_position(setup):
    settings, broker, db, tracker = setup
    db.get_state.return_value = {
        "in_position": True,
        "position": {"contracts": 3, "entry_price": 19850.0, "stop_price": 19790.0, "milestone": 0, "side": "long"},
        "daily_losses": 0, "daily_trades": 1, "daily_pnl": 0.0, "total_pnl": 0.0
    }
    sched = BotScheduler(settings, broker, db, tracker)
    await sched.eod_close()
    broker.close_position.assert_called_once_with(settings.symbol)
    tracker.stop.assert_called_once()

@pytest.mark.asyncio
async def test_eod_close_skips_when_flat(setup):
    settings, broker, db, tracker = setup
    db.get_state.return_value = {
        "in_position": False, "position": None,
        "daily_losses": 0, "daily_trades": 0, "daily_pnl": 0.0, "total_pnl": 0.0
    }
    sched = BotScheduler(settings, broker, db, tracker)
    await sched.eod_close()
    broker.close_position.assert_not_called()

@pytest.mark.asyncio
async def test_daily_reset_resets_counters(setup):
    settings, broker, db, tracker = setup
    sched = BotScheduler(settings, broker, db, tracker)
    await sched.daily_reset()
    db.reset_daily.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scheduler.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `bot/scheduler.py`**

```python
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

class BotScheduler:

    def __init__(self, settings, broker, db, tracker):
        self.settings = settings
        self.broker = broker
        self.db = db
        self.tracker = tracker
        self._scheduler = AsyncIOScheduler(timezone="America/New_York")

    def start(self):
        self._scheduler.add_job(
            self.eod_close,
            CronTrigger(
                hour=self.settings.close_hour_est,
                minute=self.settings.close_minute_est,
                timezone="America/New_York"
            ),
            id="eod_close"
        )
        self._scheduler.add_job(
            self.daily_reset,
            CronTrigger(hour=9, minute=30, timezone="America/New_York"),
            id="daily_reset"
        )
        self._scheduler.start()
        logger.info("Scheduler started — EOD close at 4:40 PM EST, reset at 9:30 AM EST")

    def shutdown(self):
        self._scheduler.shutdown()

    async def eod_close(self):
        state = await self.db.get_state()
        if state["in_position"]:
            logger.info("EOD close triggered — closing position")
            self.tracker.stop()
            await self.broker.close_position(self.settings.symbol)
        else:
            logger.info("EOD close — no position open")

    async def daily_reset(self):
        await self.db.reset_daily()
        logger.info("Daily counters reset")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scheduler.py -v
```

Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add bot/scheduler.py tests/test_scheduler.py
git commit -m "feat: scheduler with EOD close and daily reset"
```

---

## Task 11: Webhook Receiver (FastAPI)

**Files:**
- Create: `bot/webhook.py`
- Create: `tests/test_webhook.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_webhook.py
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

@pytest.fixture
def app_client(monkeypatch):
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
    monkeypatch.setenv("WEBHOOK_SECRET", "correctsecret")
    monkeypatch.setenv("SYMBOL", "MNQM5")
    monkeypatch.setenv("CONTRACTS", "3")
    monkeypatch.setenv("STOP_POINTS", "60")
    monkeypatch.setenv("MAX_DAILY_LOSSES", "2")
    monkeypatch.setenv("MAX_DAILY_TRADES", "5")
    monkeypatch.setenv("CLOSE_HOUR_EST", "16")
    monkeypatch.setenv("CLOSE_MINUTE_EST", "40")
    from bot.webhook import create_app
    risk_manager = AsyncMock()
    risk_manager.check.return_value = (True, None)
    order_manager = AsyncMock()
    app = create_app(risk_manager, order_manager)
    return TestClient(app)

def test_valid_signal_accepted(app_client):
    resp = app_client.post("/signal", json={
        "signal": "long",
        "symbol": "MNQM5",
        "price": 19850.0,
        "secret": "correctsecret"
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"

def test_missing_signal_field_rejected(app_client):
    resp = app_client.post("/signal", json={
        "symbol": "MNQM5",
        "price": 19850.0,
        "secret": "correctsecret"
    })
    assert resp.status_code == 422

def test_invalid_signal_value_rejected(app_client):
    resp = app_client.post("/signal", json={
        "signal": "sideways",
        "symbol": "MNQM5",
        "price": 19850.0,
        "secret": "correctsecret"
    })
    assert resp.status_code == 422

def test_health_check(app_client):
    resp = app_client.get("/health")
    assert resp.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_webhook.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `bot/webhook.py`**

```python
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from fastapi import FastAPI
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

class SignalPayload(BaseModel):
    signal: str
    symbol: str
    price: float
    secret: str

    @field_validator("signal")
    @classmethod
    def signal_must_be_valid(cls, v):
        if v not in ("long", "short"):
            raise ValueError("signal must be 'long' or 'short'")
        return v

def create_app(risk_manager, order_manager) -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/signal")
    async def receive_signal(payload: SignalPayload):
        now_est = datetime.now(ZoneInfo("America/New_York"))
        approved, reason = await risk_manager.check(
            payload.signal,
            payload.secret,
            hour_est=now_est.hour,
            minute_est=now_est.minute,
        )
        if not approved:
            logger.info(f"Signal rejected: {reason}")
            return {"status": "rejected", "reason": str(reason)}

        await order_manager.execute(payload.signal)
        logger.info(f"Signal accepted: {payload.signal} @ {payload.price}")
        return {"status": "accepted"}

    return app
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_webhook.py -v
```

Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add bot/webhook.py tests/test_webhook.py
git commit -m "feat: FastAPI webhook receiver with signal validation"
```

---

## Task 12: Main Entry Point

**Files:**
- Create: `main.py`

- [ ] **Step 1: Implement `main.py`**

```python
import asyncio
import logging
import uvicorn
from config import settings
from broker.tradovate import TradovateClient
from db.state import StateDB
from bot.risk_manager import RiskManager
from bot.position_tracker import PositionTracker
from bot.order_manager import OrderManager
from bot.scheduler import BotScheduler
from bot.webhook import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/bot.log"),
    ]
)

async def main():
    import os
    os.makedirs("logs", exist_ok=True)

    db = StateDB()
    await db.init()

    broker = TradovateClient(settings)
    await broker.authenticate()

    tracker = PositionTracker(settings, broker, db)
    order_manager = OrderManager(settings, broker, db, tracker)
    risk_manager = RiskManager(settings, db)
    scheduler = BotScheduler(settings, broker, db, tracker)
    scheduler.start()

    app = create_app(risk_manager, order_manager)

    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)

    logging.getLogger(__name__).info(
        f"Bot started — {settings.tradovate_env.upper()} | "
        f"{settings.symbol} | {settings.contracts} contracts | "
        f"Stop: {settings.stop_points}pts"
    )

    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run all tests**

```bash
pytest tests/ -v
```

Expected: All tests PASS

- [ ] **Step 3: Start the bot in demo mode**

Make sure `.env` has `TRADOVATE_ENV=demo`, then:

```bash
python main.py
```

Expected output:
```
INFO — Bot started — DEMO | MNQM5 | 3 contracts | Stop: 60pts
INFO — Scheduler started — EOD close at 4:40 PM EST, reset at 9:30 AM EST
```

- [ ] **Step 4: Test with a manual webhook call**

In a second terminal:

```bash
curl -X POST http://localhost:8000/signal \
  -H "Content-Type: application/json" \
  -d '{"signal":"long","symbol":"MNQM5","price":19850.0,"secret":"your_webhook_secret"}'
```

Expected: `{"status":"accepted"}` and order activity in logs.

- [ ] **Step 5: Test health endpoint**

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "feat: main entry point — wires all components and starts bot"
```

---

## Task 13: Switch to Live and Final Verification

- [ ] **Step 1: Update `.env` for live trading**

```
TRADOVATE_ENV=live
CONTRACTS=3
STOP_POINTS=60
```

- [ ] **Step 2: Restart bot and verify it authenticates against live Tradovate**

```bash
python main.py
```

Expected: `Bot started — LIVE | MNQM5 | 3 contracts | Stop: 60pts`

- [ ] **Step 3: Send a manual test signal and verify order appears in Tradovate dashboard**

```bash
curl -X POST http://localhost:8000/signal \
  -H "Content-Type: application/json" \
  -d '{"signal":"long","symbol":"MNQM5","price":0,"secret":"your_webhook_secret"}'
```

Check Tradovate dashboard — a Buy Market order for 3 MNQ should appear with a stop 60 points below fill.

- [ ] **Step 4: Verify stop is placed correctly, then manually close the position**

- [ ] **Step 5: Commit final state**

```bash
git add .
git commit -m "chore: verified live connection and end-to-end trade flow"
```

---

## Running All Tests

```bash
pytest tests/ -v --tb=short
```

All tests should pass before switching to live.
