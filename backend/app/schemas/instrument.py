from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Symbol = Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Za-z0-9.\-]{1,20}$")]


class StockCreate(BaseModel):
    """Users may add stocks. Futures come only from the verified seed data."""

    symbol: Symbol
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    exchange: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)] | None = None


class InstrumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_class: str
    symbol: str
    name: str
    exchange: str | None
    currency: str
    price_unit: str
    price_format: str
    tick_size: Decimal | None
    point_value: Decimal
    tick_value: Decimal | None
    spec_source_url: str | None
    spec_verified_on: date | None


class ContractCreate(BaseModel):
    contract_month: Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = Field(
        description="Delivery month as YYYY-MM, e.g. 2026-12"
    )
    expiration_date: date = Field(description="Last trading day, from the exchange's calendar")


class ContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    instrument_id: int
    code: str
    contract_month: date
    expiration_date: date
