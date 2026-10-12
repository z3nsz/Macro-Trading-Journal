"""Portfolios (e.g. "CME Competition") and their deposits/withdrawals.

Cash flows are stored separately from trades so deposits and withdrawals are
never mistaken for trading profit.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

ACCOUNT_TYPES = ("simulated", "real")
CASH_FLOW_KINDS = ("deposit", "withdrawal")


class Portfolio(Base):
    __tablename__ = "portfolios"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_portfolios_user_id_name"),
        CheckConstraint(f"account_type IN {ACCOUNT_TYPES}", name="account_type_valid"),
        CheckConstraint("starting_capital >= 0", name="starting_capital_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    account_type: Mapped[str] = mapped_column(String(20))  # "simulated" or "real"
    starting_capital: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), server_default="USD")
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trades: Mapped[list["Trade"]] = relationship(back_populates="portfolio", passive_deletes=True)  # noqa: F821
    cash_flows: Mapped[list["CashFlow"]] = relationship(back_populates="portfolio", passive_deletes=True)


class CashFlow(Base):
    __tablename__ = "cash_flows"
    __table_args__ = (
        CheckConstraint(f"kind IN {CASH_FLOW_KINDS}", name="kind_valid"),
        CheckConstraint("amount > 0", name="amount_positive"),  # direction comes from `kind`
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)

    portfolio: Mapped[Portfolio] = relationship(back_populates="cash_flows")
