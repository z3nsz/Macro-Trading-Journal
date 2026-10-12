from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models import User
from app.schemas.trade import TradeIn, TradeOut, TradeStatus
from app.services import trades as service
from app.services.trades import TradeFilters

router = APIRouter()


@router.get("/trades", response_model=list[TradeOut])
def list_trades(
    portfolio_id: int | None = None,
    status: TradeStatus | None = None,
    direction: str | None = Query(None, pattern="^(long|short)$"),
    asset_class: str | None = Query(None, pattern="^(stock|future)$"),
    instrument_id: int | None = None,
    strategy_id: int | None = None,
    q: str | None = Query(None, max_length=100, description="Search symbol, name, thesis, notes…"),
    date_from: date | None = Query(None, description="Trade date on/after (UTC)"),
    date_to: date | None = Query(None, description="Trade date on/before (UTC)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    filters = TradeFilters(
        portfolio_id=portfolio_id, status=status, direction=direction, asset_class=asset_class,
        instrument_id=instrument_id, strategy_id=strategy_id, q=q, date_from=date_from, date_to=date_to,
        limit=limit, offset=offset,
    )
    return [service.to_trade_out(t) for t in service.list_trades(db, user, filters)]


@router.post("/trades", response_model=TradeOut, status_code=status.HTTP_201_CREATED)
def create_trade(data: TradeIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.to_trade_out(service.create_trade(db, user, data))


@router.get("/trades/{trade_id}", response_model=TradeOut)
def get_trade(trade_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.to_trade_out(service.get_owned_trade(db, user, trade_id))


@router.put("/trades/{trade_id}", response_model=TradeOut)
def replace_trade(trade_id: int, data: TradeIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.to_trade_out(service.replace_trade(db, user, trade_id, data))


@router.delete("/trades/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trade(trade_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service.delete_trade(db, user, trade_id)
