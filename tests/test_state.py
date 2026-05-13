import pytest
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
