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
        self.access_token = resp.json()["accessToken"]

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
            json={"accountId": self.settings.account_id, "symbol": symbol, "isAutomated": True},
            headers=self._headers()
        )
        resp.raise_for_status()
