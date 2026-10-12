"""Reference data the app needs: futures contract specifications and a local development user.

Run with:  .venv/bin/python -m app.seed
Safe to run repeatedly — existing rows are updated, not duplicated.

Futures specs were checked against CME Group's official contract-spec pages on 2026-10-11.
Exchanges occasionally change specs; re-verify (spec_source_url) before relying on them.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Instrument, User

VERIFIED_ON = date(2026, 10, 11)
CME = "https://www.cmegroup.com/markets/"

DEV_USER_EMAIL = "dev@localhost.test"


@dataclass(frozen=True)
class FuturesSpec:
    symbol: str
    name: str
    exchange: str
    price_unit: str
    tick_size: Decimal
    point_value: Decimal  # USD per 1.0 move in the quoted price, per contract
    source_path: str
    price_format: str = "decimal"


FUTURES_SPECS: list[FuturesSpec] = [
    # Equity index — quoted in index points.
    FuturesSpec("ES", "E-mini S&P 500", "CME", "index points", Decimal("0.25"), Decimal("50"),
                "equities/sp/e-mini-sandp500.contractSpecs.html"),
    FuturesSpec("MES", "Micro E-mini S&P 500", "CME", "index points", Decimal("0.25"), Decimal("5"),
                "equities/sp/micro-e-mini-sandp-500.contractSpecs.html"),
    FuturesSpec("NQ", "E-mini Nasdaq-100", "CME", "index points", Decimal("0.25"), Decimal("20"),
                "equities/nasdaq/e-mini-nasdaq-100.contractSpecs.html"),
    FuturesSpec("MNQ", "Micro E-mini Nasdaq-100", "CME", "index points", Decimal("0.25"), Decimal("2"),
                "equities/nasdaq/micro-e-mini-nasdaq-100.contractSpecs.html"),
    # Energy — USD per barrel.
    FuturesSpec("CL", "Crude Oil (WTI)", "NYMEX", "USD per barrel", Decimal("0.01"), Decimal("1000"),
                "energy/crude-oil/light-sweet-crude.contractSpecs.html"),
    FuturesSpec("MCL", "Micro WTI Crude Oil", "NYMEX", "USD per barrel", Decimal("0.01"), Decimal("100"),
                "energy/crude-oil/micro-wti-crude-oil.contractSpecs.html"),
    # Metals — USD per troy ounce.
    FuturesSpec("GC", "Gold", "COMEX", "USD per troy ounce", Decimal("0.10"), Decimal("100"),
                "metals/precious/gold.contractSpecs.html"),
    # Treasuries — points and 32nds of a point; $100,000 face value => $1,000 per point.
    FuturesSpec("ZN", "10-Year T-Note", "CBOT", "points (par = 100)", Decimal("0.015625"), Decimal("1000"),
                "interest-rates/us-treasury/10-year-us-treasury-note.contractSpecs.html",
                price_format="half_thirty_seconds"),
    FuturesSpec("ZB", "U.S. Treasury Bond", "CBOT", "points (par = 100)", Decimal("0.03125"), Decimal("1000"),
                "interest-rates/us-treasury/30-year-us-treasury-bond.contractSpecs.html",
                price_format="thirty_seconds"),
    # FX — USD per euro; contract = 125,000 EUR.
    FuturesSpec("6E", "Euro FX", "CME", "USD per EUR", Decimal("0.00005"), Decimal("125000"),
                "fx/g10/euro-fx.contractSpecs.html"),
    # Grains — quoted in US *cents* per bushel; 5,000 bushels => $50 per 1 cent.
    FuturesSpec("ZC", "Corn", "CBOT", "US cents per bushel", Decimal("0.25"), Decimal("50"),
                "agriculture/grains/corn.contractSpecs.html"),
]


def seed_futures(db: Session) -> int:
    existing = {i.symbol: i for i in db.scalars(select(Instrument).where(Instrument.asset_class == "future"))}
    for spec in FUTURES_SPECS:
        instrument = existing.get(spec.symbol) or Instrument(asset_class="future", symbol=spec.symbol)
        instrument.name = spec.name
        instrument.exchange = spec.exchange
        instrument.currency = "USD"
        instrument.price_unit = spec.price_unit
        instrument.price_format = spec.price_format
        instrument.tick_size = spec.tick_size
        instrument.point_value = spec.point_value
        instrument.spec_source_url = CME + spec.source_path
        instrument.spec_verified_on = VERIFIED_ON
        db.add(instrument)
    db.flush()
    return len(FUTURES_SPECS)


def seed_dev_user(db: Session) -> User:
    """Temporary stand-in until real accounts exist (Phase 6)."""
    user = db.scalars(select(User).where(User.email == DEV_USER_EMAIL)).first()
    if user is None:
        user = User(email=DEV_USER_EMAIL, display_name="Local Dev User")
        db.add(user)
        db.flush()
    return user


def main() -> None:
    from app.db import SessionLocal

    with SessionLocal() as db:
        count = seed_futures(db)
        user = seed_dev_user(db)
        db.commit()
        print(f"Seeded {count} futures instruments and dev user id={user.id} ({user.email}).")


if __name__ == "__main__":
    main()
