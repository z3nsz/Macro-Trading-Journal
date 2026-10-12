"""Shared request dependencies."""

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.seed import DEV_USER_EMAIL


def get_current_user(db: Session = Depends(get_db)) -> User:
    """TEMPORARY: always the local development user.

    Phase 6 replaces this with real login. Because every endpoint already asks
    "who is the current user?", no endpoint will need to change.
    """
    user = db.scalars(select(User).where(User.email == DEV_USER_EMAIL)).first()
    if user is None:
        raise HTTPException(status_code=503, detail="Development user missing. Run: .venv/bin/python -m app.seed")
    return user
