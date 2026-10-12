"""Database-level rules for the journal tables.

These constraints are the last line of defense: even if API code has a bug,
PostgreSQL refuses impossible data.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Execution, FuturesContract, Instrument, Portfolio, Trade, TradeTarget, User

NOW = datetime(2026, 10, 1, 14, 30, tzinfo=timezone.utc)


@pytest.fixture
def user(db: Session) -> User:
    u = User(email="trader@example.com", display_name="Trader")
    db.add(u)
    db.flush()
    return u


@pytest.fixture
def portfolio(db: Session, user: User) -> Portfolio:
    p = Portfolio(user_id=user.id, name="CME Competition", account_type="simulated", starting_capital=Decimal("100000"))
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def es(db: Session) -> Instrument:
    i = Instrument(
        asset_class="future", symbol="ES", name="E-mini S&P 500", price_unit="index points",
        tick_size=Decimal("0.25"), point_value=Decimal("50"),
    )
    db.add(i)
    db.flush()
    return i


def make_trade(portfolio: Portfolio, instrument: Instrument, **overrides) -> Trade:
    fields = dict(
        portfolio_id=portfolio.id, instrument_id=instrument.id, direction="long",
        planned_quantity=Decimal("2"), planned_entry_price=Decimal("5000"), initial_stop_price=Decimal("4980"),
    )
    fields.update(overrides)
    return Trade(**fields)


def assert_rejected(db: Session, obj) -> None:
    db.add(obj)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


# ---- valid data ------------------------------------------------------------------------------

def test_full_trade_with_targets_and_executions_saves(db: Session, portfolio, es):
    contract = FuturesContract(
        instrument_id=es.id, code="ESZ2026", contract_month=date(2026, 12, 1), expiration_date=date(2026, 12, 18)
    )
    db.add(contract)
    db.flush()

    trade = make_trade(portfolio, es, futures_contract_id=contract.id, thesis="Soft CPI → risk-on")
    trade.targets = [TradeTarget(sequence=1, price=Decimal("5040")), TradeTarget(sequence=2, price=Decimal("5060"))]
    trade.executions = [
        Execution(kind="entry", quantity=Decimal("2"), price=Decimal("5000.25"), executed_at=NOW, fees=Decimal("4.20")),
        Execution(kind="exit", quantity=Decimal("1"), price=Decimal("5040"), executed_at=NOW.replace(hour=16)),
    ]
    db.add(trade)
    db.flush()
    db.expire_all()

    saved = db.get(Trade, trade.id)
    assert saved.status == "planned"  # database default
    assert [t.sequence for t in saved.targets] == [1, 2]
    assert saved.executions[0].price == Decimal("5000.25")
    assert saved.executions[1].fees == Decimal("0")  # database default
    assert saved.futures_contract.code == "ESZ2026"


def test_short_trade_with_stop_above_entry_is_valid(db: Session, portfolio, es):
    db.add(make_trade(portfolio, es, direction="short", initial_stop_price=Decimal("5020")))
    db.flush()


# ---- invalid data is rejected ----------------------------------------------------------------

def test_long_stop_above_entry_rejected(db: Session, portfolio, es):
    assert_rejected(db, make_trade(portfolio, es, initial_stop_price=Decimal("5010")))


def test_short_stop_below_entry_rejected(db: Session, portfolio, es):
    assert_rejected(db, make_trade(portfolio, es, direction="short", initial_stop_price=Decimal("4990")))


def test_zero_quantity_rejected(db: Session, portfolio, es):
    assert_rejected(db, make_trade(portfolio, es, planned_quantity=Decimal("0")))


def test_unknown_direction_rejected(db: Session, portfolio, es):
    assert_rejected(db, make_trade(portfolio, es, direction="sideways"))


def test_negative_execution_price_rejected(db: Session, portfolio, es):
    trade = make_trade(portfolio, es)
    trade.executions = [Execution(kind="entry", quantity=Decimal("1"), price=Decimal("-1"), executed_at=NOW)]
    assert_rejected(db, trade)


def test_future_without_tick_size_rejected(db: Session):
    assert_rejected(
        db, Instrument(asset_class="future", symbol="XX", name="Bad", price_unit="points", point_value=Decimal("1"))
    )


def test_portfolio_names_unique_per_user_only(db: Session, user, portfolio):
    other = User(email="other@example.com", display_name="Other")
    db.add(other)
    db.flush()
    # Another user may reuse the name...
    db.add(Portfolio(user_id=other.id, name="CME Competition", account_type="real", starting_capital=Decimal("0")))
    db.flush()
    # ...but the same user may not.
    assert_rejected(
        db, Portfolio(user_id=user.id, name="CME Competition", account_type="real", starting_capital=Decimal("0"))
    )


# ---- deletion behaviour ----------------------------------------------------------------------

def test_deleting_portfolio_deletes_its_trades_and_executions(db: Session, portfolio, es):
    trade = make_trade(portfolio, es)
    trade.executions = [Execution(kind="entry", quantity=Decimal("1"), price=Decimal("5000"), executed_at=NOW)]
    db.add(trade)
    db.flush()

    db.delete(portfolio)
    db.flush()
    db.expire_all()

    assert db.scalars(select(Trade)).all() == []
    assert db.scalars(select(Execution)).all() == []


def test_instrument_in_use_cannot_be_deleted(db: Session, portfolio, es):
    db.add(make_trade(portfolio, es))
    db.flush()

    db.delete(es)
    with pytest.raises(IntegrityError):
        db.flush()
