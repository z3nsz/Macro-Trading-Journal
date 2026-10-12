"""Risk and P&L calculations — pure functions, no database, no web.

Definitions (see docs/LEARNING_NOTES.md for a worked example):

  m = point_value (USD per 1.0 move in the quoted price, per contract/share)
  s = +1 for long, -1 for short

  planned reward-to-risk (per target) = |target - planned entry| / |planned entry - initial stop|
  initial dollar risk                 = |avg entry - initial stop| x entered qty x m
  gross realized P&L                  = s x (avg exit - avg entry) x exited qty x m
  fees counted                        = all exit fees + entry fees x (exited qty / entered qty)
  net realized P&L                    = gross - fees counted
  realized R                          = net realized P&L / initial dollar risk
  unrealized P&L                      = s x (market price - avg entry) x open qty x m   (needs a real price)

Anything that cannot be calculated is returned as None together with a human-readable reason —
never as an invented 0.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
RATIO = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    """Round to cents, half-up (e.g. 515.625 -> 515.63)."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def ratio(value: Decimal) -> Decimal:
    return value.quantize(RATIO, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class FillData:
    kind: str  # "entry" or "exit"
    price: Decimal
    quantity: Decimal
    fees: Decimal


@dataclass(frozen=True)
class MarketPrice:
    """A quote we are allowed to use: must carry its source and timestamp."""

    price: Decimal
    source: str
    as_of: datetime


@dataclass(frozen=True)
class TargetRR:
    sequence: int
    price: Decimal
    reward_to_risk: Decimal | None


@dataclass
class TradeMetrics:
    entered_quantity: Decimal
    exited_quantity: Decimal
    open_quantity: Decimal
    average_entry_price: Decimal | None
    average_exit_price: Decimal | None

    planned_risk_per_unit: Decimal | None  # in price points
    planned_risk_amount: Decimal | None  # USD, planned entry x planned qty
    initial_risk_amount: Decimal | None  # USD, actual avg entry x entered qty
    targets: list[TargetRR]

    gross_realized_pnl: Decimal | None
    fees_counted: Decimal | None
    total_fees: Decimal
    net_realized_pnl: Decimal | None
    realized_r: Decimal | None

    unrealized_pnl: Decimal | None
    unrealized_price: MarketPrice | None

    unavailable: dict[str, str] = field(default_factory=dict)  # metric name -> reason


def _weighted_average(fills: list[FillData]) -> tuple[Decimal, Decimal | None]:
    quantity = sum((f.quantity for f in fills), Decimal(0))
    if quantity == 0:
        return quantity, None
    return quantity, sum((f.price * f.quantity for f in fills), Decimal(0)) / quantity


def calculate_trade_metrics(
    *,
    direction: str,
    point_value: Decimal,
    planned_quantity: Decimal,
    planned_entry_price: Decimal | None,
    initial_stop_price: Decimal | None,
    target_prices: list[Decimal],
    fills: list[FillData],
    market_price: MarketPrice | None = None,
) -> TradeMetrics:
    sign = Decimal(1) if direction == "long" else Decimal(-1)
    m = point_value
    reasons: dict[str, str] = {}

    entries = [f for f in fills if f.kind == "entry"]
    exits = [f for f in fills if f.kind == "exit"]
    entered, avg_entry = _weighted_average(entries)
    exited, avg_exit = _weighted_average(exits)
    open_qty = entered - exited
    total_fees = sum((f.fees for f in fills), Decimal(0))

    # ---- planned risk and reward-to-risk (uses the plan; falls back to the actual entry) ----
    plan_entry = planned_entry_price if planned_entry_price is not None else avg_entry
    planned_risk_per_unit = None
    if initial_stop_price is None:
        reasons["planned_risk"] = "No initial stop recorded."
    elif plan_entry is None:
        reasons["planned_risk"] = "No planned or actual entry price."
    elif plan_entry == initial_stop_price:
        reasons["planned_risk"] = "Entry equals stop, so risk is zero."
    else:
        planned_risk_per_unit = abs(plan_entry - initial_stop_price)

    planned_risk_amount = (
        money(planned_risk_per_unit * planned_quantity * m) if planned_risk_per_unit is not None else None
    )
    targets = [
        TargetRR(
            sequence=i + 1,
            price=price,
            reward_to_risk=ratio(abs(price - plan_entry) / planned_risk_per_unit)
            if planned_risk_per_unit is not None and plan_entry is not None
            else None,
        )
        for i, price in enumerate(target_prices)
    ]

    # ---- initial dollar risk actually taken ------------------------------------------------
    initial_risk_amount = None
    if avg_entry is None:
        reasons["initial_risk"] = "Trade not entered yet."
    elif initial_stop_price is None:
        reasons["initial_risk"] = "No initial stop recorded."
    else:
        risk = abs(avg_entry - initial_stop_price) * entered * m
        if risk == 0:
            reasons["initial_risk"] = "Entry equals stop, so risk is zero."
        else:
            initial_risk_amount = money(risk)

    # ---- realized P&L (only for the part that has been closed) ------------------------------
    gross = fees_counted = net = realized_r = None
    if exited == 0 or avg_entry is None or avg_exit is None:
        reasons["realized_pnl"] = "No exits yet."
    else:
        entry_fees = sum((f.fees for f in entries), Decimal(0))
        exit_fees = sum((f.fees for f in exits), Decimal(0))
        gross_exact = sign * (avg_exit - avg_entry) * exited * m
        fees_exact = exit_fees + entry_fees * exited / entered
        gross = money(gross_exact)
        fees_counted = money(fees_exact)
        net = money(gross_exact - fees_exact)
        if initial_risk_amount is None:
            reasons["realized_r"] = reasons.get("initial_risk", "Initial risk unavailable.")
        else:
            realized_r = ratio((gross_exact - fees_exact) / (abs(avg_entry - initial_stop_price) * entered * m))
    if "realized_r" not in reasons and realized_r is None:
        reasons["realized_r"] = reasons["realized_pnl"]

    # ---- unrealized P&L: only with a real market price -------------------------------------
    unrealized = None
    if open_qty == 0:
        reasons["unrealized_pnl"] = "No open position."
    elif market_price is None:
        reasons["unrealized_pnl"] = "No market price available."
    else:
        unrealized = money(sign * (market_price.price - avg_entry) * open_qty * m)

    return TradeMetrics(
        entered_quantity=entered,
        exited_quantity=exited,
        open_quantity=open_qty,
        average_entry_price=avg_entry,
        average_exit_price=avg_exit,
        planned_risk_per_unit=planned_risk_per_unit,
        planned_risk_amount=planned_risk_amount,
        initial_risk_amount=initial_risk_amount,
        targets=targets,
        gross_realized_pnl=gross,
        fees_counted=fees_counted,
        total_fees=money(total_fees),
        net_realized_pnl=net,
        realized_r=realized_r,
        unrealized_pnl=unrealized,
        unrealized_price=market_price if unrealized is not None else None,
        unavailable=reasons,
    )
