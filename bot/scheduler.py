"""Scheduler for end-of-day position close and daily counter reset."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler


class BotScheduler:
    """Manages two daily cron jobs:

    - 4:40 PM EST: force-close any open position (EOD rule).
    - 9:30 AM EST: reset daily counters (losses, trades, PnL).
    """

    def __init__(self, order_manager, db):
        self._scheduler = AsyncIOScheduler(timezone="America/New_York")
        self._order_manager = order_manager
        self._db = db

    def start(self):
        """Add both cron jobs and start the underlying scheduler."""
        # EOD close: 4:40 PM EST every trading day
        self._scheduler.add_job(self._eod_close, "cron", hour=16, minute=40)
        # Daily reset: 9:30 AM EST every trading day
        self._scheduler.add_job(self._daily_reset, "cron", hour=9, minute=30)
        self._scheduler.start()

    def stop(self):
        """Shut down the scheduler without waiting for running jobs."""
        self._scheduler.shutdown(wait=False)

    async def _eod_close(self):
        """Force-close any open position at end of day."""
        await self._order_manager.close_position_eod()

    async def _daily_reset(self):
        """Reset daily counters at market open."""
        await self._db.reset_daily()
