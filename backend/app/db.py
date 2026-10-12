"""Database connection setup.

- `engine` manages a pool of connections to PostgreSQL.
- `SessionLocal` creates sessions: a session is one "conversation" with the database
  (load rows, change them, then commit or roll back).
- `get_db` gives each API request its own session and always closes it afterwards.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # quietly replace connections that went stale
    connect_args={
        "connect_timeout": 3,  # fail fast instead of hanging if Postgres is down
        "options": "-c timezone=UTC",  # return every timestamp in UTC, whatever the machine's timezone
    },
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def database_is_reachable(db: Session) -> bool:
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
