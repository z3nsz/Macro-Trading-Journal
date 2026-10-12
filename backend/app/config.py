"""Application settings, read from environment variables (or backend/.env).

Secrets such as API keys will live here later. They are never sent to the frontend.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env, regardless of which folder the server is started from.
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    app_name: str = "Macro Trading Journal"
    environment: str = "development"


settings = Settings()
