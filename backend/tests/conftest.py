"""Shared test setup.

Tests run against a SEPARATE database (TEST_DATABASE_URL) so they can never touch real data.

- Once per test run: rebuild the test database from scratch using our Alembic migrations
  (downgrade to empty, then upgrade to latest). This also proves the migrations work.
- For each test: open a transaction and roll it back afterwards, so tests don't affect each other.
"""

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.db import get_db
from app.main import app
from app.models import User
from app.seed import seed_futures

BACKEND_DIR = __file__.rsplit("/tests/", 1)[0]


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    alembic_cfg = Config(f"{BACKEND_DIR}/alembic.ini")
    # "%" must be escaped for Alembic's config parser (passwords may contain it).
    alembic_cfg.set_main_option("sqlalchemy.url", settings.test_database_url.replace("%", "%%"))
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")

    test_engine = create_engine(settings.test_database_url)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    # Make every API request in this test use the test-database session.
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_user(db: Session, email: str) -> User:
    user = User(email=email, display_name=email.split("@")[0])
    db.add(user)
    db.flush()
    return user


def act_as(user: User) -> None:
    """Make API requests run as `user` (stands in for logging in)."""
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture
def alice(db: Session, client: TestClient) -> User:
    seed_futures(db)
    user = make_user(db, "alice@example.com")
    act_as(user)
    return user


@pytest.fixture
def bob(db: Session) -> User:
    return make_user(db, "bob@example.com")
