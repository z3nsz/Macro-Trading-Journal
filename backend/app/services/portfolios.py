"""Portfolio and strategy data access. Every query is limited to the current user's rows."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError
from app.models import Portfolio, Strategy, User
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate
from app.schemas.strategy import StrategyCreate


def list_portfolios(db: Session, user: User) -> list[Portfolio]:
    return list(db.scalars(select(Portfolio).where(Portfolio.user_id == user.id).order_by(Portfolio.name)))


def get_owned_portfolio(db: Session, user: User, portfolio_id: int) -> Portfolio:
    portfolio = db.scalars(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user.id)
    ).first()
    if portfolio is None:
        raise NotFoundError("Portfolio")
    return portfolio


def _save(db: Session, obj, duplicate_message: str):
    db.add(obj)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(duplicate_message) from exc
    db.commit()
    db.refresh(obj)
    return obj


def create_portfolio(db: Session, user: User, data: PortfolioCreate) -> Portfolio:
    portfolio = Portfolio(user_id=user.id, **data.model_dump())
    return _save(db, portfolio, f"You already have a portfolio named '{data.name}'.")


def update_portfolio(db: Session, user: User, portfolio_id: int, data: PortfolioUpdate) -> Portfolio:
    portfolio = get_owned_portfolio(db, user, portfolio_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(portfolio, key, value)
    return _save(db, portfolio, f"You already have a portfolio named '{data.name}'.")


def delete_portfolio(db: Session, user: User, portfolio_id: int) -> None:
    db.delete(get_owned_portfolio(db, user, portfolio_id))
    db.commit()


def list_strategies(db: Session, user: User) -> list[Strategy]:
    return list(db.scalars(select(Strategy).where(Strategy.user_id == user.id).order_by(Strategy.name)))


def get_owned_strategy(db: Session, user: User, strategy_id: int) -> Strategy:
    strategy = db.scalars(select(Strategy).where(Strategy.id == strategy_id, Strategy.user_id == user.id)).first()
    if strategy is None:
        raise NotFoundError("Strategy")
    return strategy


def create_strategy(db: Session, user: User, data: StrategyCreate) -> Strategy:
    return _save(db, Strategy(user_id=user.id, **data.model_dump()), f"You already have a strategy named '{data.name}'.")
