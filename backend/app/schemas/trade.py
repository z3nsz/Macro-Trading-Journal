from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.schemas.common import LongText, Money, Price, Quantity
from app.schemas.instrument import ContractOut, InstrumentOut
from app.schemas.portfolio import PortfolioSummary
from app.schemas.strategy import StrategyOut


class FillIn(BaseModel):
    price: Price
    executed_at: AwareDatetime  # must include a timezone, e.g. "2026-10-01T14:30:00Z"
    quantity: Quantity | None = None  # entry defaults to planned quantity; exit defaults to entry quantity
    fees: Money = Decimal("0")


class TargetIn(BaseModel):
    price: Price
    quantity: Quantity | None = None


class TradeIn(BaseModel):
    """Body for creating (POST) or replacing (PUT) a trade. First version: one entry and one exit."""

    portfolio_id: int
    instrument_id: int
    futures_contract_id: int | None = None
    strategy_id: int | None = None
    direction: Literal["long", "short"]
    planned_quantity: Quantity
    planned_entry_price: Price | None = None
    initial_stop_price: Price | None = None
    current_stop_price: Price | None = None
    targets: list[TargetIn] = Field(default_factory=list, max_length=5)
    thesis: LongText | None = None
    catalyst: LongText | None = None
    notes: LongText | None = None
    reflection: LongText | None = None
    entry: FillIn | None = None
    exit: FillIn | None = None


class TargetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sequence: int
    price: Decimal
    quantity: Decimal | None


class ExecutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    quantity: Decimal
    price: Decimal
    executed_at: datetime
    fees: Decimal


class TradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portfolio: PortfolioSummary
    instrument: InstrumentOut
    futures_contract: ContractOut | None
    strategy: StrategyOut | None
    direction: str
    status: str
    planned_quantity: Decimal
    planned_entry_price: Decimal | None
    initial_stop_price: Decimal | None
    current_stop_price: Decimal | None
    targets: list[TargetOut]
    executions: list[ExecutionOut]
    thesis: str | None
    catalyst: str | None
    notes: str | None
    reflection: str | None
    created_at: datetime
    updated_at: datetime


TradeStatus = Literal["planned", "open", "partially_closed", "closed"]
