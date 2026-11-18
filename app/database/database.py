from pathlib import Path

from app.database.base import Base
from app.core.config import settings
from app.database.session import engine

#import models so sqlalchemy registers them
from app.models.products import Product


def _ensure_sqlite_directory() -> None:
    """Create the parent directory when the app is using a file-based SQLite DB."""
    prefix = "sqlite:///"
    if not settings.DATABASE_URL.startswith(prefix):
        return

    database_path = settings.DATABASE_URL[len(prefix):]
    if database_path in {"", ":memory:"}:
        return

    Path(database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)


def create_database():
    _ensure_sqlite_directory()
    Base.metadata.create_all(bind=engine)
