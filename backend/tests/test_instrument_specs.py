"""Futures specs must reproduce CME's published tick values exactly.

Published "$ per tick" figures copied from each contract's CME spec page (checked 2026-10-11).
They are written here independently of app/seed.py, so a typo in either place fails the test.
"""

from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Instrument
from app.seed import FUTURES_SPECS, seed_dev_user, seed_futures

PUBLISHED_TICK_VALUES = {
    "ES": Decimal("12.50"),
    "MES": Decimal("1.25"),
    "NQ": Decimal("5.00"),
    "MNQ": Decimal("0.50"),
    "CL": Decimal("10.00"),
    "MCL": Decimal("1.00"),
    "GC": Decimal("10.00"),
    "ZN": Decimal("15.625"),
    "ZB": Decimal("31.25"),
    "6E": Decimal("6.25"),
    "ZC": Decimal("12.50"),
}


def test_every_seeded_future_has_a_published_tick_value():
    assert {s.symbol for s in FUTURES_SPECS} == set(PUBLISHED_TICK_VALUES)


@pytest.mark.parametrize("spec", FUTURES_SPECS, ids=lambda s: s.symbol)
def test_tick_value_matches_cme(spec):
    assert spec.tick_size * spec.point_value == PUBLISHED_TICK_VALUES[spec.symbol]


def test_treasury_ticks_are_fractions_of_32nds():
    specs = {s.symbol: s for s in FUTURES_SPECS}
    assert specs["ZN"].tick_size == Decimal(1) / 32 / 2  # half of 1/32
    assert specs["ZB"].tick_size == Decimal(1) / 32


def test_seed_is_idempotent_and_round_trips_exact_decimals(db: Session):
    seed_futures(db)
    seed_futures(db)  # running twice must not create duplicates
    seed_dev_user(db)
    seed_dev_user(db)

    count = db.scalar(select(func.count()).select_from(Instrument).where(Instrument.asset_class == "future"))
    assert count == len(FUTURES_SPECS)

    db.expire_all()  # force a fresh read from PostgreSQL
    zn = db.scalars(select(Instrument).where(Instrument.symbol == "ZN")).one()
    assert zn.tick_size == Decimal("0.015625")  # NUMERIC keeps it exact (no float rounding)
    assert zn.tick_value == Decimal("15.625")
