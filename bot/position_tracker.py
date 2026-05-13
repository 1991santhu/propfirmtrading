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
        return self.milestone_price(side, entry, milestone - 1)

    def contracts_to_close(self, total_contracts: int, milestone: int) -> int:
        if milestone in (1, 2):
            return max(1, round(total_contracts * 0.20))
        return 0

    async def start(self, side: str, entry_price: float, total_contracts: int, stop_order_id: str):
        self._monitoring = True
        self._stop_order_id = stop_order_id
        if self.settings.exit_strategy == "fixed_2r":
            await self._run_fixed_2r(side, entry_price, total_contracts)
        else:
            await self._run_trailing(side, entry_price, total_contracts)

    async def _run_trailing(self, side: str, entry_price: float, total_contracts: int):
        while self._monitoring:
            await asyncio.sleep(5)
            try:
                current_price = await self.broker.get_quote(self.settings.symbol)
                pos = (await self.db.get_state())["position"]
                if pos is None:
                    break
                next_milestone = pos["milestone"] + 1
                next_price = self.milestone_price(side, entry_price, next_milestone)
                milestone_hit = (
                    (side == "long" and current_price >= next_price) or
                    (side == "short" and current_price <= next_price)
                )
                if milestone_hit:
                    await self._handle_milestone(side, entry_price, next_milestone, pos["contracts"])
            except Exception as e:
                logger.error(f"Position tracker error: {e}")

    async def _run_fixed_2r(self, side: str, entry_price: float, total_contracts: int):
        """Fixed 2R exit: move stop to breakeven at 1R, close 100% at 2R."""
        breakeven_moved = False
        target_1r = self.milestone_price(side, entry_price, 1)
        target_2r = self.milestone_price(side, entry_price, 2)
        breakeven_price = entry_price  # stop moves here at 1R hit

        while self._monitoring:
            await asyncio.sleep(5)
            try:
                current_price = await self.broker.get_quote(self.settings.symbol)
                pos = (await self.db.get_state())["position"]
                if pos is None:
                    break

                hit_1r = (side == "long" and current_price >= target_1r) or \
                         (side == "short" and current_price <= target_1r)
                hit_2r = (side == "long" and current_price >= target_2r) or \
                         (side == "short" and current_price <= target_2r)

                if hit_2r:
                    # Close entire position
                    close_action = "Sell" if side == "long" else "Buy"
                    await self.broker.place_market_order(self.settings.symbol, close_action, total_contracts)
                    if self._stop_order_id:
                        await self.broker.cancel_order(self._stop_order_id)
                    pnl = self.settings.stop_points * 2 * total_contracts * 2  # 2R × contracts × $2/pt
                    await self.db.clear_position(pnl)
                    logger.info(f"Fixed 2R hit — closed {total_contracts} contracts at {current_price}")
                    break

                elif hit_1r and not breakeven_moved:
                    # Move stop to breakeven
                    if self._stop_order_id:
                        await self.broker.cancel_order(self._stop_order_id)
                    stop_action = "Sell" if side == "long" else "Buy"
                    self._stop_order_id = await self.broker.place_stop_order(
                        self.settings.symbol, stop_action, total_contracts, breakeven_price
                    )
                    await self.db.update_milestone(1, breakeven_price, total_contracts)
                    breakeven_moved = True
                    logger.info(f"1R hit — stop moved to breakeven {breakeven_price}")

            except Exception as e:
                logger.error(f"Fixed 2R tracker error: {e}")

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
