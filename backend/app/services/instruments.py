"""Instruments are shared reference data (AAPL is AAPL for everyone)."""

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domain.trade_rules import RuleViolation
from app.errors import ConflictError, NotFoundError, RulesViolated
from app.models import FuturesContract, Instrument
from app.schemas.instrument import ContractCreate, StockCreate

# CME month codes: F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec
MONTH_CODES = "FGHJKMNQUVXZ"


def list_instruments(db: Session, asset_class: str | None = None, q: str | None = None) -> list[Instrument]:
    query = select(Instrument).order_by(Instrument.asset_class, Instrument.symbol)
    if asset_class:
        query = query.where(Instrument.asset_class == asset_class)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(or_(Instrument.symbol.ilike(pattern), Instrument.name.ilike(pattern)))
    return list(db.scalars(query))


def get_instrument(db: Session, instrument_id: int) -> Instrument:
    instrument = db.get(Instrument, instrument_id)
    if instrument is None:
        raise NotFoundError("Instrument")
    return instrument


def create_stock(db: Session, data: StockCreate) -> Instrument:
    exists = db.scalars(
        select(Instrument).where(Instrument.asset_class == "stock", Instrument.symbol == data.symbol)
    ).first()
    if exists:
        raise ConflictError(f"Stock {data.symbol} already exists (id {exists.id}).")
    stock = Instrument(
        asset_class="stock", symbol=data.symbol, name=data.name, exchange=data.exchange,
        price_unit="USD per share", price_format="decimal",
        tick_size=None,  # stocks can fill at sub-penny prices (e.g. midpoint), so no grid is enforced
        point_value=1,
    )
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return stock


def list_contracts(db: Session, instrument_id: int) -> list[FuturesContract]:
    get_instrument(db, instrument_id)
    return list(
        db.scalars(
            select(FuturesContract)
            .where(FuturesContract.instrument_id == instrument_id)
            .order_by(FuturesContract.contract_month)
        )
    )


def create_contract(db: Session, instrument_id: int, data: ContractCreate) -> FuturesContract:
    instrument = get_instrument(db, instrument_id)
    if instrument.asset_class != "future":
        raise RulesViolated([RuleViolation("instrument_id", "Only futures have contract months.")])

    year, month = (int(x) for x in data.contract_month.split("-"))
    contract_month = date(year, month, 1)
    # Expiration must fall between ~2 months before the delivery month (e.g. CL expires the month
    # before) and the end of the delivery month.
    earliest = date(year - 1, month + 10, 1) if month <= 2 else date(year, month - 2, 1)
    latest = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    if not (earliest <= data.expiration_date < latest):
        raise RulesViolated([
            RuleViolation("expiration_date", "Expiration must be in, or shortly before, the contract month.")
        ])

    exists = db.scalars(
        select(FuturesContract).where(
            FuturesContract.instrument_id == instrument_id, FuturesContract.contract_month == contract_month
        )
    ).first()
    if exists:
        raise ConflictError(f"{exists.code} already exists (id {exists.id}).")

    contract = FuturesContract(
        instrument_id=instrument_id,
        code=f"{instrument.symbol}{MONTH_CODES[month - 1]}{year}",
        contract_month=contract_month,
        expiration_date=data.expiration_date,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract
