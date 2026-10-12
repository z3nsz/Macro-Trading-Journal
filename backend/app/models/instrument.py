"""Tradable instruments and specific futures contracts.

Prices are stored in the exchange's *quoted* unit (e.g. corn in US cents per bushel,
ES in index points). `point_value` converts a 1.0 move in that quoted price into US dollars
per contract (or per share), so every asset class can use its own correct conversion.

Options will be added later as a new asset class with their own table
(underlying, strike, call/put, expiration) — no existing columns need to change.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

ASSET_CLASSES = ("stock", "future")
# How prices are written: plain decimals, or Treasury-style points-and-32nds.
PRICE_FORMATS = ("decimal", "thirty_seconds", "half_thirty_seconds")


class Instrument(Base):
    __tablename__ = "instruments"
    __table_args__ = (
        UniqueConstraint("asset_class", "symbol", name="uq_instruments_asset_class_symbol"),
        CheckConstraint(f"asset_class IN {ASSET_CLASSES}", name="asset_class_valid"),
        CheckConstraint(f"price_format IN {PRICE_FORMATS}", name="price_format_valid"),
        CheckConstraint("point_value > 0", name="point_value_positive"),
        CheckConstraint("tick_size IS NULL OR tick_size > 0", name="tick_size_positive"),
        # Futures must have an exchange-defined tick size; stocks may trade in sub-penny increments.
        CheckConstraint("asset_class <> 'future' OR tick_size IS NOT NULL", name="future_requires_tick_size"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_class: Mapped[str] = mapped_column(String(20))
    symbol: Mapped[str] = mapped_column(String(20))  # "AAPL", or the futures root "ES"
    name: Mapped[str] = mapped_column(String(200))
    exchange: Mapped[str | None] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(3), server_default="USD")
    price_unit: Mapped[str] = mapped_column(String(60))  # e.g. "index points", "US cents per bushel"
    price_format: Mapped[str] = mapped_column(String(30), server_default="decimal")
    tick_size: Mapped[Decimal | None] = mapped_column(Numeric(20, 10))
    # US dollars gained/lost per 1.0 move in the quoted price, per contract or share.
    point_value: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    spec_source_url: Mapped[str | None] = mapped_column(Text)
    spec_verified_on: Mapped[date | None] = mapped_column(Date)

    contracts: Mapped[list["FuturesContract"]] = relationship(back_populates="instrument")

    @property
    def tick_value(self) -> Decimal | None:
        """Dollar value of one minimum price move (e.g. ES: 0.25 × $50 = $12.50)."""
        return None if self.tick_size is None else self.tick_size * self.point_value


class FuturesContract(Base):
    """A specific delivery month of a futures product, e.g. ES December 2026 (ESZ2026)."""

    __tablename__ = "futures_contracts"
    __table_args__ = (
        UniqueConstraint("instrument_id", "contract_month", name="uq_futures_contracts_instrument_id_month"),
        CheckConstraint("EXTRACT(DAY FROM contract_month) = 1", name="contract_month_first_of_month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="RESTRICT"), index=True)
    code: Mapped[str] = mapped_column(String(20))  # e.g. "ESZ2026"
    contract_month: Mapped[date] = mapped_column(Date)  # stored as the 1st of the month
    # Last trading day. Rules differ by product (ES: 3rd Friday; CL: before the 25th of the
    # prior month), so it is stored explicitly rather than guessed.
    expiration_date: Mapped[date] = mapped_column(Date)

    instrument: Mapped[Instrument] = relationship(back_populates="contracts")
