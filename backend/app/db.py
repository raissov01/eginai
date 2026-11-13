"""Дерекқор: тек пайдаланушы келісім берген жағдайлар сақталады.

Фото ешқашан сақталмайды. Координаталар 2 ондық белгіге дейін
дөңгелектенеді (~1 км) — нақты учаске емес, аудан деңгейі.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, create_engine
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


class Feedback(Base):
    """«Диагноз дұрыс па?» жауабы. Фото да, координата да сақталмайды."""
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True,
                                                 default=lambda: datetime.now(timezone.utc))
    predicted: Mapped[str] = mapped_column(String(40), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    correct: Mapped[bool] = mapped_column(Boolean)
    actual: Mapped[str | None] = mapped_column(String(40), nullable=True)  # фермер/агроном білсе
    source: Mapped[str] = mapped_column(String(10))


class Subscription(Base):
    """Боттағы «ауданымдағы ошақ туралы ескерт» жазылымы. /stop_alerts толық өшіреді."""
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[str] = mapped_column(String(32), unique=True)
    lat: Mapped[float] = mapped_column(Float)          # ~1 км-ге дөңгелектенген
    lon: Mapped[float] = mapped_column(Float)
    radius_km: Mapped[float] = mapped_column(Float)
    lang: Mapped[str] = mapped_column(String(2))
    last_case_id: Mapped[int] = mapped_column(Integer, default=0)  # осыдан кейінгі ошақтар хабарланады
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 default=lambda: datetime.now(timezone.utc))


class BotDiagnosis(Base):
    """Бот диагноздарының тарихы (фотосыз): алқап бойынша қарау және CSV экспорт."""
    __tablename__ = "bot_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 default=lambda: datetime.now(timezone.utc))
    chat_id: Mapped[str] = mapped_column(String(32), index=True)
    disease: Mapped[str] = mapped_column(String(40))
    confidence: Mapped[float] = mapped_column(Float)
    field: Mapped[str | None] = mapped_column(String(60), nullable=True)


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
