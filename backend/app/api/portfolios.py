from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models import User
from app.schemas.portfolio import PortfolioCreate, PortfolioOut, PortfolioUpdate
from app.schemas.strategy import StrategyCreate, StrategyOut
from app.services import portfolios as service

router = APIRouter()


@router.get("/portfolios", response_model=list[PortfolioOut])
def list_portfolios(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.list_portfolios(db, user)


@router.post("/portfolios", response_model=PortfolioOut, status_code=status.HTTP_201_CREATED)
def create_portfolio(data: PortfolioCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.create_portfolio(db, user, data)


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioOut)
def get_portfolio(portfolio_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.get_owned_portfolio(db, user, portfolio_id)


@router.patch("/portfolios/{portfolio_id}", response_model=PortfolioOut)
def update_portfolio(
    portfolio_id: int, data: PortfolioUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return service.update_portfolio(db, user, portfolio_id, data)


@router.delete("/portfolios/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio(portfolio_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Deletes the portfolio AND all of its trades. The UI must confirm first."""
    service.delete_portfolio(db, user, portfolio_id)


@router.get("/strategies", response_model=list[StrategyOut])
def list_strategies(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.list_strategies(db, user)


@router.post("/strategies", response_model=StrategyOut, status_code=status.HTTP_201_CREATED)
def create_strategy(data: StrategyCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.create_strategy(db, user, data)
