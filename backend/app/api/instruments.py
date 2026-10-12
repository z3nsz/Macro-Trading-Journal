from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.schemas.instrument import ContractCreate, ContractOut, InstrumentOut, StockCreate
from app.services import instruments as service

# Instruments are shared reference data, but you still need to be a (logged-in) user to use them.
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/instruments", response_model=list[InstrumentOut])
def list_instruments(
    asset_class: Literal["stock", "future"] | None = None,
    q: str | None = Query(None, max_length=50),
    db: Session = Depends(get_db),
):
    return service.list_instruments(db, asset_class, q)


@router.post("/instruments/stocks", response_model=InstrumentOut, status_code=status.HTTP_201_CREATED)
def create_stock(data: StockCreate, db: Session = Depends(get_db)):
    return service.create_stock(db, data)


@router.get("/instruments/{instrument_id}/contracts", response_model=list[ContractOut])
def list_contracts(instrument_id: int, db: Session = Depends(get_db)):
    return service.list_contracts(db, instrument_id)


@router.post(
    "/instruments/{instrument_id}/contracts", response_model=ContractOut, status_code=status.HTTP_201_CREATED
)
def create_contract(instrument_id: int, data: ContractCreate, db: Session = Depends(get_db)):
    return service.create_contract(db, instrument_id, data)
