from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_database_url


class Base(DeclarativeBase):
    pass


def build_engine(database_url: Optional[str] = None):
    url = database_url or get_database_url()
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args)


engine = build_engine()
SessionLocal = sessionmaker(bind=engine)


def create_tables(eng=None):
    """Create all tables. Safe to call multiple times (CREATE IF NOT EXISTS)."""
    target = eng or engine
    Base.metadata.create_all(target)
