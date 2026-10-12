"""Import every model here so Alembic can see all tables when generating migrations."""

from app.models.base import Base
from app.models.instrument import FuturesContract, Instrument
from app.models.portfolio import CashFlow, Portfolio
from app.models.strategy import Strategy
from app.models.trade import Execution, Trade, TradeTarget
from app.models.user import User

__all__ = [
    "Base",
    "CashFlow",
    "Execution",
    "FuturesContract",
    "Instrument",
    "Portfolio",
    "Strategy",
    "Trade",
    "TradeTarget",
    "User",
]
