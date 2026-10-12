"""Trades, their profit targets, and their actual executions (fills).

A trade is the *plan and reasoning*. Executions are *what actually happened*:
one or more entry fills and zero or more exit fills. This supports partial exits
and scaling in, even though the first version of the UI uses one entry and one exit.

`initial_stop_price` is the stop at the time of entry and is never overwritten;
later stop moves go in `current_stop_price`. Initial risk (and therefore R-multiples)
is always measured against the initial stop.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.instrument import FuturesContract, Instrument
from app.models.portfolio import Portfolio
from app.models.strategy import Strategy

DIRECTIONS = ("long", "short")
TRADE_STATUSES = ("planned", "open", "partially_closed", "closed")
EXECUTION_KINDS = ("entry", "exit")

# Money: 2 decimals. Prices: up to 10 decimals (6E ticks are 0.00005; ZN ticks are 0.015625).
# Quantities: 6 decimals so fractional shares work; futures quantities are whole contracts.
PRICE = Numeric(20, 10)
QUANTITY = Numeric(18, 6)
MONEY = Numeric(18, 2)


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        CheckConstraint(f"direction IN {DIRECTIONS}", name="direction_valid"),
        CheckConstraint(f"status IN {TRADE_STATUSES}", name="status_valid"),
        CheckConstraint("planned_quantity > 0", name="planned_quantity_positive"),
        CheckConstraint("planned_entry_price IS NULL OR planned_entry_price > 0", name="planned_entry_positive"),
        CheckConstraint("initial_stop_price IS NULL OR initial_stop_price > 0", name="initial_stop_positive"),
        CheckConstraint("current_stop_price IS NULL OR current_stop_price > 0", name="current_stop_positive"),
        # A long's stop must sit below its entry; a short's stop above it.
        CheckConstraint(
            "initial_stop_price IS NULL OR planned_entry_price IS NULL"
            " OR (direction = 'long' AND initial_stop_price < planned_entry_price)"
            " OR (direction = 'short' AND initial_stop_price > planned_entry_price)",
            name="initial_stop_on_risk_side",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), index=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="RESTRICT"), index=True)
    futures_contract_id: Mapped[int | None] = mapped_column(
        ForeignKey("futures_contracts.id", ondelete="RESTRICT"), index=True
    )
    strategy_id: Mapped[int | None] = mapped_column(ForeignKey("strategies.id", ondelete="SET NULL"), index=True)

    direction: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), server_default="planned")

    planned_quantity: Mapped[Decimal] = mapped_column(QUANTITY)
    planned_entry_price: Mapped[Decimal | None] = mapped_column(PRICE)
    initial_stop_price: Mapped[Decimal | None] = mapped_column(PRICE)
    current_stop_price: Mapped[Decimal | None] = mapped_column(PRICE)

    thesis: Mapped[str | None] = mapped_column(Text)  # reasoning for the trade
    catalyst: Mapped[str | None] = mapped_column(Text)  # economic event / catalyst
    notes: Mapped[str | None] = mapped_column(Text)
    reflection: Mapped[str | None] = mapped_column(Text)  # post-trade review

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    portfolio: Mapped[Portfolio] = relationship(back_populates="trades")
    instrument: Mapped[Instrument] = relationship()
    futures_contract: Mapped[FuturesContract | None] = relationship()
    strategy: Mapped[Strategy | None] = relationship()
    targets: Mapped[list["TradeTarget"]] = relationship(
        back_populates="trade", cascade="all, delete-orphan", order_by="TradeTarget.sequence"
    )
    executions: Mapped[list["Execution"]] = relationship(
        back_populates="trade", cascade="all, delete-orphan", order_by="Execution.executed_at"
    )


class TradeTarget(Base):
    """A planned take-profit level. Sequence 1 = first target (TP1), 2 = TP2, ..."""

    __tablename__ = "trade_targets"
    __table_args__ = (
        UniqueConstraint("trade_id", "sequence", name="uq_trade_targets_trade_id_sequence"),
        CheckConstraint("sequence >= 1", name="sequence_positive"),
        CheckConstraint("price > 0", name="price_positive"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    trade_id: Mapped[int] = mapped_column(ForeignKey("trades.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(SmallInteger)
    price: Mapped[Decimal] = mapped_column(PRICE)
    quantity: Mapped[Decimal | None] = mapped_column(QUANTITY)  # optional: how much to close here

    trade: Mapped[Trade] = relationship(back_populates="targets")


class Execution(Base):
    """One actual fill. Entry fills open the position; exit fills reduce or close it."""

    __tablename__ = "executions"
    __table_args__ = (
        CheckConstraint(f"kind IN {EXECUTION_KINDS}", name="kind_valid"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("price > 0", name="price_positive"),
        CheckConstraint("fees >= 0", name="fees_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    trade_id: Mapped[int] = mapped_column(ForeignKey("trades.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(10))
    quantity: Mapped[Decimal] = mapped_column(QUANTITY)
    price: Mapped[Decimal] = mapped_column(PRICE)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fees: Mapped[Decimal] = mapped_column(MONEY, server_default="0")  # fees + commissions for this fill
    note: Mapped[str | None] = mapped_column(Text)

    trade: Mapped[Trade] = relationship(back_populates="executions")
