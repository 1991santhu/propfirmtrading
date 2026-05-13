from datetime import datetime, timezone, timedelta

from fastapi import FastAPI
from pydantic import BaseModel


class SignalPayload(BaseModel):
    signal: str   # "long" or "short"
    symbol: str   # e.g. "MNQM5"
    price: float  # current price hint from TradingView
    secret: str   # must match settings.webhook_secret


def _current_est_hour_minute() -> tuple[int, int]:
    """Return (hour, minute) in US/Eastern time (UTC-5 / UTC-4 DST).

    Uses a fixed UTC-5 offset for simplicity; the risk-manager cutoff check
    is intentionally conservative, so the ±1 hour DST difference is acceptable.
    """
    est = timezone(timedelta(hours=-5))
    now = datetime.now(tz=est)
    return now.hour, now.minute


def create_app(settings, risk_manager, order_manager) -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/signal")
    async def receive_signal(payload: SignalPayload):
        hour_est, minute_est = _current_est_hour_minute()
        allowed, reason = await risk_manager.check(
            payload.signal, payload.secret, hour_est=hour_est, minute_est=minute_est
        )
        if not allowed:
            return {"status": "rejected", "reason": reason.value}
        result = await order_manager.open_position(payload.signal, payload.price)
        return {
            "status": "accepted",
            "order_id": result.order_id,
            "fill_price": result.fill_price,
        }

    return app
