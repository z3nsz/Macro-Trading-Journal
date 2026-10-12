"""Pure trading rules: no database, no web framework — just inputs in, problems out.

Keeping these separate makes them easy to test and guarantees every screen and
endpoint applies exactly the same rules.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

# Allow a little clock difference between the user's device and the server.
FUTURE_TOLERANCE = timedelta(minutes=5)


@dataclass(frozen=True)
class RuleViolation:
    field: str  # which input is wrong, e.g. "initial_stop_price" or "exit.executed_at"
    message: str


@dataclass(frozen=True)
class Fill:
    price: Decimal
    quantity: Decimal
    executed_at: datetime


@dataclass(frozen=True)
class TradeDraft:
    """Everything the rules need to know about a trade being created or edited."""

    asset_class: str  # "stock" or "future"
    tick_size: Decimal | None
    direction: str  # "long" or "short"
    planned_quantity: Decimal
    planned_entry_price: Decimal | None
    initial_stop_price: Decimal | None
    current_stop_price: Decimal | None
    target_prices: list[Decimal] = field(default_factory=list)
    entry: Fill | None = None
    exit: Fill | None = None


def is_on_tick(price: Decimal, tick_size: Decimal) -> bool:
    """True if price is an exact multiple of the tick size (Decimal math, so no float error)."""
    return price % tick_size == 0


def derive_status(entry_quantity: Decimal, exit_quantity: Decimal) -> str:
    if entry_quantity == 0:
        return "planned"
    if exit_quantity == 0:
        return "open"
    if exit_quantity < entry_quantity:
        return "partially_closed"
    return "closed"


def validate_trade(draft: TradeDraft, now: datetime) -> list[RuleViolation]:
    problems: list[RuleViolation] = []
    is_long = draft.direction == "long"

    # --- futures: whole contracts and prices on the exchange's tick grid ---------------------
    if draft.asset_class == "future":
        quantities = {"planned_quantity": draft.planned_quantity}
        if draft.entry:
            quantities["entry.quantity"] = draft.entry.quantity
        if draft.exit:
            quantities["exit.quantity"] = draft.exit.quantity
        for name, qty in quantities.items():
            if qty != qty.to_integral_value():
                problems.append(RuleViolation(name, "Futures are traded in whole contracts."))

        if draft.tick_size:
            prices = {
                "planned_entry_price": draft.planned_entry_price,
                "initial_stop_price": draft.initial_stop_price,
                "current_stop_price": draft.current_stop_price,
                "entry.price": draft.entry.price if draft.entry else None,
                "exit.price": draft.exit.price if draft.exit else None,
            }
            prices.update({f"targets.{i}.price": p for i, p in enumerate(draft.target_prices)})
            for name, price in prices.items():
                if price is not None and not is_on_tick(price, draft.tick_size):
                    problems.append(
                        RuleViolation(name, f"Price must be a multiple of the tick size ({draft.tick_size.normalize()}).")
                    )

    # --- stop and targets must be on the correct side of entry -------------------------------
    references = {
        "planned entry": draft.planned_entry_price,
        "entry fill": draft.entry.price if draft.entry else None,
    }
    references = {k: v for k, v in references.items() if v is not None}

    if not references and (draft.initial_stop_price is not None or draft.target_prices):
        problems.append(
            RuleViolation("planned_entry_price", "Enter a planned entry or an actual entry to check the stop and targets.")
        )

    for label, ref in references.items():
        stop = draft.initial_stop_price
        if stop is not None and (stop >= ref if is_long else stop <= ref):
            side = "below" if is_long else "above"
            problems.append(RuleViolation("initial_stop_price", f"A {draft.direction} stop must be {side} the {label} ({ref.normalize()})."))
        for i, target in enumerate(draft.target_prices):
            if target <= ref if is_long else target >= ref:
                side = "above" if is_long else "below"
                problems.append(
                    RuleViolation(f"targets.{i}.price", f"A {draft.direction} target must be {side} the {label} ({ref.normalize()}).")
                )

    # --- executions: order, size and timing ---------------------------------------------------
    if draft.exit and not draft.entry:
        problems.append(RuleViolation("exit", "A trade needs an entry before it can have an exit."))

    for name, fill in (("entry", draft.entry), ("exit", draft.exit)):
        if fill and fill.executed_at > now + FUTURE_TOLERANCE:
            problems.append(RuleViolation(f"{name}.executed_at", "Execution time cannot be in the future."))

    if draft.entry and draft.exit:
        if draft.exit.executed_at < draft.entry.executed_at:
            problems.append(RuleViolation("exit.executed_at", "Exit time cannot be before entry time."))
        if draft.exit.quantity > draft.entry.quantity:
            problems.append(RuleViolation("exit.quantity", "Cannot exit more than was entered."))

    return problems
