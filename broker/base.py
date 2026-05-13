from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class OrderResult:
    order_id: str
    fill_price: float
    contracts: int
    status: str  # "filled", "pending", "rejected"

@dataclass
class PositionResult:
    contracts: int
    entry_price: float
    current_price: float
    unrealized_pnl: float
    side: str  # "long" or "short"

class BrokerClient(ABC):

    @abstractmethod
    async def authenticate(self) -> None:
        """Authenticate with the broker. Must be called before any other method."""
        pass

    @abstractmethod
    async def place_market_order(self, symbol: str, action: str, contracts: int) -> OrderResult:
        """Place a market order. action is 'Buy' or 'Sell'."""
        pass

    @abstractmethod
    async def place_stop_order(self, symbol: str, action: str, contracts: int, stop_price: float) -> str:
        """Place a stop order. Returns order_id."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> None:
        """Cancel an open order by order_id."""
        pass

    @abstractmethod
    async def get_quote(self, symbol: str) -> float:
        """Get current last price for symbol."""
        pass

    @abstractmethod
    async def close_position(self, symbol: str) -> None:
        """Liquidate entire position for symbol immediately."""
        pass
