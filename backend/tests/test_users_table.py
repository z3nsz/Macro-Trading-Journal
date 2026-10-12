"""Checks that the migration created the users table with the rules we expect."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User


def test_can_save_and_load_a_user(db: Session):
    db.add(User(email="student@example.com", display_name="Student"))
    db.flush()  # send the INSERT to the database (inside the test's transaction)

    loaded = db.scalars(select(User).where(User.email == "student@example.com")).one()
    assert loaded.id is not None
    assert loaded.display_name == "Student"
    assert loaded.created_at is not None  # filled in by the database default


def test_email_must_be_unique(db: Session):
    db.add(User(email="dup@example.com", display_name="First"))
    db.flush()

    db.add(User(email="dup@example.com", display_name="Second"))
    with pytest.raises(IntegrityError):
        db.flush()
