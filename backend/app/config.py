"""Application settings, read from environment variables (or backend/.env).

Secrets such as API keys and database passwords live here. They are never sent to the frontend.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env, regardless of which folder the server is started from.
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    app_name: str = "Macro Trading Journal"
    environment: str = "development"

    # Format: postgresql+psycopg://USER:PASSWORD@HOST:PORT/DATABASE
    database_url: str = "postgresql+psycopg://macro_journal@localhost:5432/macro_journal"
    # Separate database that the test suite is allowed to wipe.
    test_database_url: str = "postgresql+psycopg://macro_journal@localhost:5432/macro_journal_test"


settings = Settings()
