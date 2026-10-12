"""Trade data access: ownership checks, validation, and saving trades with their fills.

Rules themselves live in app/domain/trade_rules.py; this module gathers the facts
(instrument, contract, existing fills) and applies the rules' verdict.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.domain.trade_rules import Fill, RuleViolation, TradeDraft, derive_status, validate_trade
from app.errors import ConflictError, NotFoundError, RulesViolated
from app.models import Execution, FuturesContract, Instrument, Portfolio, Trade, TradeTarget, User
from app.schemas.trade import FillIn, TradeIn
from app.services.instruments import get_instrument
from app.services.portfolios import get_owned_portfolio, get_owned_strategy

_LOAD_EVERYTHING = (
    selectinload(Trade.portfolio),
    selectinload(Trade.instrument),
    selectinload(Trade.futures_contract),
    selectinload(Trade.strategy),
    selectinload(Trade.targets),
    selectinload(Trade.executions),
)

# The trade's date = time of its first entry fill, or when it was created if it has none (planned).
_first_entry_at = (
    select(func.min(Execution.executed_at))
    .where(Execution.trade_id == Trade.id, Execution.kind == "entry")
    .correlate(Trade)
    .scalar_subquery()
)
trade_date = func.coalesce(_first_entry_at, Trade.created_at)


@dataclass
class TradeFilters:
    portfolio_id: int | None = None
    status: str | None = None
    direction: str | None = None
    asset_class: str | None = None
    instrument_id: int | None = None
    strategy_id: int | None = None
    q: str | None = None  # free-text search
    date_from: date | None = None  # inclusive, UTC
    date_to: date | None = None  # inclusive, UTC
    limit: int = 100
    offset: int = 0


def list_trades(db: Session, user: User, f: TradeFilters) -> list[Trade]:
    query = (
        select(Trade)
        .join(Portfolio, Trade.portfolio_id == Portfolio.id)
        .join(Instrument, Trade.instrument_id == Instrument.id)
        .where(Portfolio.user_id == user.id)  # ownership: only this user's trades
        .options(*_LOAD_EVERYTHING)
    )
    if f.portfolio_id is not None:
        query = query.where(Trade.portfolio_id == f.portfolio_id)
    if f.status:
        query = query.where(Trade.status == f.status)
    if f.direction:
        query = query.where(Trade.direction == f.direction)
    if f.asset_class:
        query = query.where(Instrument.asset_class == f.asset_class)
    if f.instrument_id is not None:
        query = query.where(Trade.instrument_id == f.instrument_id)
    if f.strategy_id is not None:
        query = query.where(Trade.strategy_id == f.strategy_id)
    if f.q:
        pattern = f"%{f.q.strip()}%"
        query = query.where(
            or_(
                Instrument.symbol.ilike(pattern),
                Instrument.name.ilike(pattern),
                Trade.thesis.ilike(pattern),
                Trade.catalyst.ilike(pattern),
                Trade.notes.ilike(pattern),
                Trade.reflection.ilike(pattern),
            )
        )
    if f.date_from:
        query = query.where(trade_date >= datetime.combine(f.date_from, time.min, timezone.utc))
    if f.date_to:
        query = query.where(trade_date < datetime.combine(f.date_to + timedelta(days=1), time.min, timezone.utc))

    query = query.order_by(trade_date.desc(), Trade.id.desc()).limit(f.limit).offset(f.offset)
    return list(db.scalars(query))


def get_owned_trade(db: Session, user: User, trade_id: int) -> Trade:
    trade = db.scalars(
        select(Trade)
        .join(Portfolio, Trade.portfolio_id == Portfolio.id)
        .where(Trade.id == trade_id, Portfolio.user_id == user.id)
        .options(*_LOAD_EVERYTHING)
    ).first()
    if trade is None:
        raise NotFoundError("Trade")
    return trade


def create_trade(db: Session, user: User, data: TradeIn) -> Trade:
    trade = Trade()
    _apply(db, user, trade, data)
    db.add(trade)
    db.commit()
    db.expire_all()  # reload from PostgreSQL so the response shows exactly what was stored
    return get_owned_trade(db, user, trade.id)


def replace_trade(db: Session, user: User, trade_id: int, data: TradeIn) -> Trade:
    trade = get_owned_trade(db, user, trade_id)

    entries = [e for e in trade.executions if e.kind == "entry"]
    exits = [e for e in trade.executions if e.kind == "exit"]
    if len(entries) > 1 or len(exits) > 1:
        raise ConflictError("This trade has multiple fills; edit its executions individually.")

    # Preserve planned risk: once a trade has been entered, its initial stop is fixed.
    if entries and data.initial_stop_price != trade.initial_stop_price:
        raise RulesViolated([
            RuleViolation(
                "initial_stop_price",
                "The initial stop is locked after entry. Record stop moves in current_stop_price.",
            )
        ])

    _apply(db, user, trade, data)
    db.commit()
    db.expire_all()
    return get_owned_trade(db, user, trade.id)


def delete_trade(db: Session, user: User, trade_id: int) -> None:
    db.delete(get_owned_trade(db, user, trade_id))
    db.commit()


# ---- helpers ----------------------------------------------------------------------------------

def _apply(db: Session, user: User, trade: Trade, data: TradeIn) -> None:
    """Check references and rules, then copy `data` onto `trade` (new or existing)."""
    portfolio = get_owned_portfolio(db, user, data.portfolio_id)
    instrument = get_instrument(db, data.instrument_id)
    strategy = get_owned_strategy(db, user, data.strategy_id) if data.strategy_id is not None else None
    contract = _check_contract(db, instrument, data.futures_contract_id)

    entry = _to_fill(data.entry, default_quantity=data.planned_quantity)
    exit_ = _to_fill(data.exit, default_quantity=entry.quantity if entry else data.planned_quantity)

    draft = TradeDraft(
        asset_class=instrument.asset_class,
        tick_size=instrument.tick_size,
        direction=data.direction,
        planned_quantity=data.planned_quantity,
        planned_entry_price=data.planned_entry_price,
        initial_stop_price=data.initial_stop_price,
        current_stop_price=data.current_stop_price,
        target_prices=[t.price for t in data.targets],
        entry=entry,
        exit=exit_,
    )
    violations = validate_trade(draft, now=datetime.now(timezone.utc))
    if violations:
        raise RulesViolated(violations)

    trade.portfolio = portfolio
    trade.instrument = instrument
    trade.futures_contract = contract
    trade.strategy = strategy
    for name in (
        "direction", "planned_quantity", "planned_entry_price", "initial_stop_price",
        "current_stop_price", "thesis", "catalyst", "notes", "reflection",
    ):
        setattr(trade, name, getattr(data, name))

    if trade.id is not None:
        # Remove old targets/fills first so new rows (e.g. a new TP1) don't collide with old ones.
        trade.targets.clear()
        trade.executions.clear()
        db.flush()

    trade.targets = [TradeTarget(sequence=i + 1, price=t.price, quantity=t.quantity) for i, t in enumerate(data.targets)]
    trade.executions = [
        Execution(kind=kind, price=fill.price, quantity=fill.quantity, executed_at=fill.executed_at, fees=fees)
        for kind, fill, fees in (
            ("entry", entry, data.entry.fees if data.entry else None),
            ("exit", exit_, data.exit.fees if data.exit else None),
        )
        if fill is not None
    ]
    trade.status = derive_status(
        entry.quantity if entry else Decimal(0),
        exit_.quantity if exit_ else Decimal(0),
    )


def _check_contract(db: Session, instrument: Instrument, contract_id: int | None) -> FuturesContract | None:
    if instrument.asset_class != "future":
        if contract_id is not None:
            raise RulesViolated([RuleViolation("futures_contract_id", "Only futures trades have a contract month.")])
        return None
    if contract_id is None:
        raise RulesViolated([RuleViolation("futures_contract_id", "Choose the specific futures contract (e.g. ESZ2026).")])
    contract = db.get(FuturesContract, contract_id)
    if contract is None or contract.instrument_id != instrument.id:
        raise RulesViolated([RuleViolation("futures_contract_id", f"That contract is not a {instrument.symbol} contract.")])
    return contract


def _to_fill(fill: FillIn | None, default_quantity: Decimal) -> Fill | None:
    if fill is None:
        return None
    return Fill(price=fill.price, quantity=fill.quantity or default_quantity, executed_at=fill.executed_at)
