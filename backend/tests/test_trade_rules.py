"""Unit tests for the pure trading rules — no database or web server involved."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

import pytest

from app.domain.trade_rules import Fill, TradeDraft, derive_status, is_on_tick, validate_trade

NOW = datetime(2026, 10, 1, 20, 0, tzinfo=timezone.utc)
T0 = NOW - timedelta(hours=5)

ES_LONG = TradeDraft(
    asset_class="future", tick_size=D("0.25"), direction="long", planned_quantity=D("2"),
    planned_entry_price=D("5000"), initial_stop_price=D("4980"), current_stop_price=None,
    target_prices=[D("5040"), D("5060")],
)


def fields(draft: TradeDraft) -> list[str]:
    return [v.field for v in validate_trade(draft, NOW)]


# ---- tick grid ------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "price, tick, ok",
    [
        (D("5000.25"), D("0.25"), True),
        (D("5000.30"), D("0.25"), False),
        (D("112.515625"), D("0.015625"), True),  # ZN 112-16½
        (D("112.51"), D("0.015625"), False),
        (D("1.08505"), D("0.00005"), True),  # 6E
        (D("1.08507"), D("0.00005"), False),
        (D("425.25"), D("0.25"), True),  # corn, cents per bushel
    ],
)
def test_is_on_tick(price, tick, ok):
    assert is_on_tick(price, tick) is ok


# ---- status ---------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "entered, exited, expected",
    [(D(0), D(0), "planned"), (D(2), D(0), "open"), (D(2), D(1), "partially_closed"), (D(2), D(2), "closed")],
)
def test_derive_status(entered, exited, expected):
    assert derive_status(entered, exited) == expected


# ---- valid trades ---------------------------------------------------------------------------

def test_valid_planned_long_has_no_problems():
    assert fields(ES_LONG) == []


def test_valid_closed_short_has_no_problems():
    short = replace(
        ES_LONG, direction="short", initial_stop_price=D("5020"), target_prices=[D("4960")],
        entry=Fill(D("5000"), D("2"), T0), exit=Fill(D("4960"), D("2"), T0 + timedelta(hours=1)),
    )
    assert fields(short) == []


def test_stocks_allow_sub_penny_and_fractional_shares():
    stock = replace(
        ES_LONG, asset_class="stock", tick_size=None, planned_quantity=D("1.5"),
        planned_entry_price=D("187.1234"), initial_stop_price=D("180"), target_prices=[D("200")],
    )
    assert fields(stock) == []


# ---- invalid trades -------------------------------------------------------------------------

def test_long_stop_above_entry():
    assert fields(replace(ES_LONG, initial_stop_price=D("5010"))) == ["initial_stop_price"]


def test_short_stop_below_entry():
    assert "initial_stop_price" in fields(replace(ES_LONG, direction="short", target_prices=[]))


def test_long_target_below_entry():
    assert fields(replace(ES_LONG, target_prices=[D("5040"), D("4990")])) == ["targets.1.price"]


def test_stop_checked_against_actual_fill_too():
    # Planned 5000 with stop 4980 is fine, but the fill happened at 4975 — below the stop.
    draft = replace(ES_LONG, entry=Fill(D("4975"), D("2"), T0))
    assert fields(draft) == ["initial_stop_price"]


def test_off_tick_prices_flagged_per_field():
    draft = replace(ES_LONG, initial_stop_price=D("4980.10"), entry=Fill(D("5000.30"), D("2"), T0))
    assert set(fields(draft)) == {"initial_stop_price", "entry.price"}


def test_fractional_futures_quantity():
    assert fields(replace(ES_LONG, planned_quantity=D("1.5"))) == ["planned_quantity"]


def test_stop_without_any_entry_price():
    assert fields(replace(ES_LONG, planned_entry_price=None)) == ["planned_entry_price"]


def test_exit_without_entry():
    assert "exit" in fields(replace(ES_LONG, exit=Fill(D("5040"), D("2"), T0)))


def test_exit_before_entry():
    draft = replace(ES_LONG, entry=Fill(D("5000"), D("2"), T0), exit=Fill(D("5040"), D("2"), T0 - timedelta(minutes=1)))
    assert fields(draft) == ["exit.executed_at"]


def test_exit_larger_than_entry():
    draft = replace(ES_LONG, entry=Fill(D("5000"), D("2"), T0), exit=Fill(D("5040"), D("3"), T0 + timedelta(hours=1)))
    assert fields(draft) == ["exit.quantity"]


def test_execution_in_the_future():
    draft = replace(ES_LONG, entry=Fill(D("5000"), D("2"), NOW + timedelta(hours=1)))
    assert fields(draft) == ["entry.executed_at"]


def test_small_clock_difference_is_tolerated():
    draft = replace(ES_LONG, entry=Fill(D("5000"), D("2"), NOW + timedelta(minutes=2)))
    assert fields(draft) == []
