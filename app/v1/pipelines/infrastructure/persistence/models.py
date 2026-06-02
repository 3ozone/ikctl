"""Modelos SQLAlchemy para persistencia del módulo pipelines."""
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.types import TypeDecorator


class _JsonText(TypeDecorator):
    """Tipo JSON portable: usa LONGTEXT en MariaDB/MySQL, TEXT en SQLite (tests)."""

    impl = LONGTEXT
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name in ("mysql", "mariadb"):
            return dialect.type_descriptor(LONGTEXT())
        return dialect.type_descriptor(String())

    def process_bind_param(self, value: Any, dialect) -> str | None:
        if value is None:
            return None
        import json
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value: str | None, dialect) -> Any:
        if value is None:
            return None
        import json
        return json.loads(value)


Base = declarative_base()


class PipelineModel(Base):
    """Modelo SQLAlchemy para la tabla pipelines."""

    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    targets: Mapped[Any] = mapped_column(_JsonText, nullable=False, default="[]")
    kits: Mapped[Any] = mapped_column(_JsonText, nullable=False, default="[]")
    values: Mapped[Any] = mapped_column(_JsonText, nullable=False, default="{}")
    sudo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    debug_level: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_pipelines_user_id", "user_id"),
        Index("ix_pipelines_name", "name"),
    )


class PipelineExecutionModel(Base):
    """Modelo SQLAlchemy para la tabla pipeline_executions."""

    __tablename__ = "pipeline_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    pipeline_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    operation_ids: Mapped[Any] = mapped_column(_JsonText, nullable=False, default="[]")
    snapshot: Mapped[Any] = mapped_column(_JsonText, nullable=False, default="{}")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_pipeline_executions_pipeline_id", "pipeline_id"),
        Index("ix_pipeline_executions_user_id", "user_id"),
        Index("ix_pipeline_executions_status", "status"),
    )
