import asyncio
import logging

from broker.base import BrokerClient, OrderResult
from db.state import StateDB
from bot.position_tracker import PositionTracker

logger = logging.getLogger(__name__)


class OrderManager:

    def __init__(self, settings, broker: BrokerClient, db: StateDB, tracker: PositionTracker):
        self.settings = settings
        self.broker = broker
        self.db = db
        self.tracker = tracker

    async def open_position(self, side: str, price_hint: float) -> OrderResult:
        """
        Orchestrate opening a new position:
        1. Place market order (entry)
        2. Calculate stop price from actual fill
        3. Place stop order
        4. Persist position state to DB
        5. Increment daily trade counter
        6. Launch position tracker as background task
        7. Return the market OrderResult
        """
        # Step 1: determine market order action and place it
        entry_action = "Buy" if side == "long" else "Sell"
        order_result: OrderResult = await self.broker.place_market_order(
            self.settings.symbol, entry_action, self.settings.contracts
        )
        fill_price = order_result.fill_price

        # Step 2: calculate stop price using actual fill
        stop_price = self.tracker.calculate_stop_price(side, fill_price)

        # Step 3: place protective stop order (opposite side)
        stop_action = "Sell" if side == "long" else "Buy"
        stop_order_id: str = await self.broker.place_stop_order(
            self.settings.symbol, stop_action, order_result.contracts, stop_price
        )

        # Step 4: persist position to DB
        await self.db.set_position({
            "side": side,
            "entry_price": fill_price,
            "stop_price": stop_price,
            "contracts": order_result.contracts,
            "milestone": 0,
        })

        # Step 5: track this as a daily trade
        await self.db.increment_daily_trades()

        # Step 6: launch position tracker as a non-blocking background task
        asyncio.create_task(
            self.tracker.start(side, fill_price, order_result.contracts, stop_order_id)
        )

        logger.info(
            f"Opened {side} {order_result.contracts}x {self.settings.symbol} "
            f"@ {fill_price}, stop @ {stop_price} (order {order_result.order_id})"
        )

        return order_result

    async def close_position_eod(self) -> None:
        """
        End-of-day position close called by the scheduler.
        If a position is open, liquidate it, clear DB state, and stop the tracker.
        PnL is recorded as 0 because the exact realised P&L is not available here.
        """
        state = await self.db.get_state()
        if not state.get("in_position"):
            logger.info("EOD close: no open position, nothing to do.")
            return

        await self.broker.close_position(self.settings.symbol)
        await self.db.clear_position(0)
        self.tracker.stop()
        logger.info("EOD close: position liquidated and state cleared.")
