"""Import every model here so Alembic can see all tables when generating migrations."""

from app.models.base import Base
from app.models.user import User

__all__ = ["Base", "User"]
