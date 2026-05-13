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

    async def check(self, signal: str, secret: str, hour_est: int, minute_est: int = 0) -> tuple[bool, RejectionReason | None]:
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
        if hour_est * 60 + minute_est >= cutoff_minutes:
            return False, RejectionReason.AFTER_CUTOFF

        return True, None
