from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import LongText, Name

Capital = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)]


class PortfolioCreate(BaseModel):
    name: Name
    account_type: Literal["simulated", "real"]
    starting_capital: Capital
    description: LongText | None = None


class PortfolioUpdate(BaseModel):
    """PATCH: only the fields you send are changed."""

    name: Name | None = None
    account_type: Literal["simulated", "real"] | None = None
    starting_capital: Capital | None = None
    description: LongText | None = None


class PortfolioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    account_type: str
    starting_capital: Decimal
    currency: str
    description: str | None
    created_at: datetime


class PortfolioSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    account_type: str
