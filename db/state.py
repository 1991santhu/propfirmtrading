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
