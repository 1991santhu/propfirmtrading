import asyncio
import logging
import uvicorn
from config import Settings
from db.state import StateDB
from broker.tradovate import TradovateClient
from bot.risk_manager import RiskManager
from bot.position_tracker import PositionTracker
from bot.order_manager import OrderManager
from bot.scheduler import BotScheduler
from bot.webhook import create_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    settings = Settings()

    db = StateDB()
    await db.init()

    broker = TradovateClient(settings)
    await broker.authenticate()

    tracker = PositionTracker(settings, broker, db)
    risk_manager = RiskManager(settings, db)
    order_manager = OrderManager(settings, broker, db, tracker)

    scheduler = BotScheduler(order_manager, db)
    scheduler.start()

    app = create_app(settings, risk_manager, order_manager)

    config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(config)

    try:
        await server.serve()
    finally:
        scheduler.stop()
        await db.close()
        logger.info("Bot shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
