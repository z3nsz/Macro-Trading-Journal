"""Reusable field types. Decimals are serialized as strings in JSON to keep exact precision."""

from decimal import Decimal
from typing import Annotated

from pydantic import Field, StringConstraints

Price = Annotated[Decimal, Field(gt=0, max_digits=20, decimal_places=10)]
Quantity = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=6)]
Money = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=10_000)]
