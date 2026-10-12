"""Alembic runtime configuration.

The database URL comes from app.config.settings (backend/.env), so it lives in one place
and is never committed. Tests can override it with `config.set_main_option("sqlalchemy.url", ...)`.
"""

from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from app.config import settings
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic compares this metadata (our models) with the real database to autogenerate migrations.
target_metadata = Base.metadata


def get_url() -> str:
    return config.get_main_option("sqlalchemy.url") or settings.database_url


def run_migrations_offline() -> None:
    """Write the migration SQL to stdout instead of running it (`alembic upgrade head --sql`)."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the database and apply migrations."""
    connectable = create_engine(get_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
