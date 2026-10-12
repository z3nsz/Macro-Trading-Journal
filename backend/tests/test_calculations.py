"""Risk and P&L calculations. The first tests reproduce the worked example in LEARNING_NOTES.md."""

from datetime import datetime, timezone
from decimal import Decimal as D

import pytest

from app.domain.calculations import FillData, MarketPrice, calculate_trade_metrics, money


def entry(price, qty, fees="0"):
    return FillData("entry", D(price), D(qty), D(fees))


def exit_(price, qty, fees="0"):
    return FillData("exit", D(price), D(qty), D(fees))


def es_long(fills, **overrides):
    """ES long, 2 contracts: plan 5000, stop 4980, TP1 5040, TP2 5060. m = $50."""
    args = dict(
        direction="long", point_value=D("50"), planned_quantity=D("2"), planned_entry_price=D("5000"),
        initial_stop_price=D("4980"), target_prices=[D("5040"), D("5060")], fills=fills,
    )
    args.update(overrides)
    return calculate_trade_metrics(**args)


# ---- the worked example ---------------------------------------------------------------------

def test_planned_reward_to_risk_per_target():
    m = es_long([])
    assert [t.reward_to_risk for t in m.targets] == [D("2.00"), D("3.00")]
    assert m.planned_risk_per_unit == D("20")
    assert m.planned_risk_amount == D("2000.00")  # 20 pts x 2 x $50


def test_initial_risk_uses_actual_fill():
    m = es_long([entry("5000.25", "2", "4.20")])
    assert m.initial_risk_amount == D("2025.00")  # 20.25 x 2 x $50


def test_closed_trade_gross_net_and_r():
    m = es_long([entry("5000.25", "2", "4.20"), exit_("5040.50", "2", "4.20")])
    assert m.gross_realized_pnl == D("4025.00")
    assert m.fees_counted == D("8.40")
    assert m.net_realized_pnl == D("4016.60")
    assert m.realized_r == D("1.98")  # 4016.60 / 2025 = 1.9835
    assert m.open_quantity == 0


def test_partial_exit_allocates_entry_fees_proportionally():
    m = es_long([entry("5000.25", "2", "4.20"), exit_("5040", "1", "4.20")])
    assert m.gross_realized_pnl == D("1987.50")
    assert m.fees_counted == D("6.30")  # 4.20 exit + half of 4.20 entry
    assert m.net_realized_pnl == D("1981.20")
    assert m.realized_r == D("0.98")
    assert m.open_quantity == D("1")
    assert m.total_fees == D("8.40")


def test_short_profit_is_positive():
    m = calculate_trade_metrics(
        direction="short", point_value=D("1000"), planned_quantity=D("1"), planned_entry_price=D("72.50"),
        initial_stop_price=D("73.50"), target_prices=[D("70.00")],
        fills=[entry("72.48", "1"), exit_("70.95", "1")],
    )
    assert m.gross_realized_pnl == D("1530.00")
    assert m.targets[0].reward_to_risk == D("2.50")  # (72.50 - 70.00) / (73.50 - 72.50)
    assert m.initial_risk_amount == D("1020.00")  # (73.50 - 72.48) x 1000
    assert m.realized_r == D("1.50")  # 1530 / 1020


def test_losing_long_stopped_out_is_minus_one_r_before_fees():
    m = es_long([entry("5000", "2"), exit_("4980", "2")])
    assert m.net_realized_pnl == D("-2000.00")
    assert m.realized_r == D("-1.00")


# ---- multiple fills -------------------------------------------------------------------------

def test_scaling_in_uses_weighted_average_entry():
    # 1 @ 5000 and 3 @ 5004 -> average 5003; exit all 4 @ 5013 -> 10 pts x 4 x $50 = $2,000
    m = es_long(
        [entry("5000", "1"), entry("5004", "3"), exit_("5013", "4")], planned_quantity=D("4")
    )
    assert m.average_entry_price == D("5003")
    assert m.gross_realized_pnl == D("2000.00")
    assert m.initial_risk_amount == D("4600.00")  # (5003 - 4980) x 4 x $50


def test_multiple_exits_use_weighted_average_exit():
    m = es_long([entry("5000", "2"), exit_("5040", "1"), exit_("5060", "1")])
    assert m.average_exit_price == D("5050")
    assert m.gross_realized_pnl == D("5000.00")
    assert m.realized_r == D("2.50")


# ---- different price conventions ------------------------------------------------------------

def test_corn_quoted_in_cents():
    # 425.25 -> 429.50 cents = 4.25 cents x $50 per cent
    m = calculate_trade_metrics(
        direction="long", point_value=D("50"), planned_quantity=D("1"), planned_entry_price=D("425.25"),
        initial_stop_price=D("420"), target_prices=[], fills=[entry("425.25", "1"), exit_("429.50", "1")],
    )
    assert m.gross_realized_pnl == D("212.50")


def test_treasury_half_cent_rounds_half_up():
    # ZN 112'16.5 -> 113'01 = 33 ticks x $15.625 = $515.625 -> $515.63
    m = calculate_trade_metrics(
        direction="long", point_value=D("1000"), planned_quantity=D("1"), planned_entry_price=D("112.515625"),
        initial_stop_price=D("112.25"), target_prices=[], fills=[entry("112.515625", "1"), exit_("113.03125", "1")],
    )
    assert m.gross_realized_pnl == D("515.63")


def test_fractional_shares_and_sub_penny_prices():
    m = calculate_trade_metrics(
        direction="long", point_value=D("1"), planned_quantity=D("10.5"), planned_entry_price=D("187.1234"),
        initial_stop_price=D("180"), target_prices=[], fills=[entry("187.1234", "10.5", "0.35"), exit_("190.00", "10.5", "0.35")],
    )
    assert m.gross_realized_pnl == D("30.20")  # 2.8766 x 10.5 = 30.2043
    assert m.net_realized_pnl == D("29.50")


# ---- unavailable values are reported, never invented -------------------------------------------

def test_missing_stop_makes_risk_and_r_unavailable():
    m = es_long([entry("5000", "2"), exit_("5040", "2")], initial_stop_price=None)
    assert m.initial_risk_amount is None
    assert m.realized_r is None
    assert m.net_realized_pnl == D("4000.00")  # P&L itself is still known
    assert m.unavailable["realized_r"] == "No initial stop recorded."
    assert [t.reward_to_risk for t in m.targets] == [None, None]


def test_planned_trade_has_no_realized_values():
    m = es_long([])
    assert m.net_realized_pnl is None
    assert m.realized_r is None
    assert m.initial_risk_amount is None
    assert m.unavailable["realized_pnl"] == "No exits yet."
    assert m.unavailable["initial_risk"] == "Trade not entered yet."


def test_reward_to_risk_falls_back_to_actual_entry_without_plan():
    m = es_long([entry("5000", "2")], planned_entry_price=None)
    assert [t.reward_to_risk for t in m.targets] == [D("2.00"), D("3.00")]


def test_unrealized_requires_a_market_price():
    open_trade = [entry("5000", "2"), exit_("5040", "1")]
    assert es_long(open_trade).unrealized_pnl is None
    assert es_long(open_trade).unavailable["unrealized_pnl"] == "No market price available."

    quote = MarketPrice(D("5010.25"), source="Example feed (delayed)", as_of=datetime(2026, 10, 1, 15, tzinfo=timezone.utc))
    m = es_long(open_trade, market_price=quote)
    assert m.unrealized_pnl == D("512.50")  # 10.25 x 1 open x $50
    assert m.unrealized_price.source == "Example feed (delayed)"


def test_closed_trade_has_no_unrealized():
    m = es_long([entry("5000", "2"), exit_("5040", "2")])
    assert m.unavailable["unrealized_pnl"] == "No open position."


@pytest.mark.parametrize("value, expected", [("515.625", "515.63"), ("515.615", "515.62"), ("-2.345", "-2.35")])
def test_money_rounding_half_up(value, expected):
    assert money(D(value)) == D(expected)
