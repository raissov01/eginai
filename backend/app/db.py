"""Дерекқор: тек пайдаланушы келісім берген жағдайлар сақталады.

Фото ешқашан сақталмайды. Координаталар 2 ондық белгіге дейін
дөңгелектенеді (~1 км) — нақты учаске емес, аудан деңгейі.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True,
                                                 default=lambda: datetime.now(timezone.utc))
    disease: Mapped[str] = mapped_column(String(40), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(10))  # web | bot | demo


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql+psycopg://eginai:eginai@localhost:5432/eginai")


def make_session_factory(url: str | None = None) -> sessionmaker:
    url = url or database_url()
    kw = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {
        "connect_args": {"connect_timeout": 3}}
    engine = create_engine(url, pool_pre_ping=True, **kw)
    return sessionmaker(engine, expire_on_commit=False)


def init_db(factory: sessionmaker) -> None:
    Base.metadata.create_all(factory.kw["bind"])
