"""Modelos SQLAlchemy para persistencia del módulo servers."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


class CredentialModel(Base):
    """Modelo SQLAlchemy para tabla credentials."""

    __tablename__ = "credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Almacenados cifrados con AES-256 — nunca en texto plano
    password_encrypted: Mapped[str | None] = mapped_column(
        String(2048), nullable=True)
    private_key_encrypted: Mapped[str | None] = mapped_column(
        String(8192), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_credentials_user_id", "user_id"),
        Index("ix_credentials_type", "type"),
    )


class ServerModel(Base):
    """Modelo SQLAlchemy para tabla servers."""

    __tablename__ = "servers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    credential_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("credentials.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        String(1024), nullable=True)
    os_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    os_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    os_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_servers_user_id", "user_id"),
        Index("ix_servers_status", "status"),
        Index("ix_servers_credential_id", "credential_id"),
    )


class GroupModel(Base):
    """Modelo SQLAlchemy para tabla groups."""

    __tablename__ = "groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(
        String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (Index("ix_groups_user_id", "user_id"),)


class GroupMemberModel(Base):
    """Modelo SQLAlchemy para tabla group_members."""

    __tablename__ = "group_members"

    group_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    server_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("servers.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (PrimaryKeyConstraint("group_id", "server_id"),)
