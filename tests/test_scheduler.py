"""Tests for BotScheduler (Task 10)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from bot.scheduler import BotScheduler


# ---------------------------------------------------------------------------
# Test 1: start() registers two jobs and starts the scheduler
# ---------------------------------------------------------------------------

def test_start_registers_two_jobs():
    """start() should add two cron jobs and call _scheduler.start()."""
    mock_order_manager = MagicMock()
    mock_db = MagicMock()

    with patch("bot.scheduler.AsyncIOScheduler") as MockScheduler:
        mock_sched_instance = MagicMock()
        MockScheduler.return_value = mock_sched_instance

        scheduler = BotScheduler(mock_order_manager, mock_db)
        scheduler.start()

        # Two jobs must be registered
        assert mock_sched_instance.add_job.call_count == 2
        # The underlying APScheduler start() must be called
        mock_sched_instance.start.assert_called_once()


# ---------------------------------------------------------------------------
# Test 2: stop() shuts down the scheduler with wait=False
# ---------------------------------------------------------------------------

def test_stop_shuts_down_scheduler():
    """stop() should call _scheduler.shutdown(wait=False)."""
    mock_order_manager = MagicMock()
    mock_db = MagicMock()

    with patch("bot.scheduler.AsyncIOScheduler") as MockScheduler:
        mock_sched_instance = MagicMock()
        MockScheduler.return_value = mock_sched_instance

        scheduler = BotScheduler(mock_order_manager, mock_db)
        scheduler.stop()

        mock_sched_instance.shutdown.assert_called_once_with(wait=False)


# ---------------------------------------------------------------------------
# Test 3: _eod_close() delegates to order_manager.close_position_eod()
# ---------------------------------------------------------------------------

async def test_eod_close_delegates_to_order_manager():
    """_eod_close() should await order_manager.close_position_eod()."""
    mock_order_manager = MagicMock()
    mock_order_manager.close_position_eod = AsyncMock()
    mock_db = MagicMock()

    scheduler = BotScheduler(mock_order_manager, mock_db)
    await scheduler._eod_close()

    mock_order_manager.close_position_eod.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 4: _daily_reset() delegates to db.reset_daily()
# ---------------------------------------------------------------------------

async def test_daily_reset_delegates_to_db():
    """_daily_reset() should await db.reset_daily()."""
    mock_order_manager = MagicMock()
    mock_db = MagicMock()
    mock_db.reset_daily = AsyncMock()

    scheduler = BotScheduler(mock_order_manager, mock_db)
    await scheduler._daily_reset()

    mock_db.reset_daily.assert_awaited_once()
