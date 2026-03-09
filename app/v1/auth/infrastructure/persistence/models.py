"""Modelos SQLAlchemy para persistencia."""
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, declarative_base

Base = declarative_base()


class UserModel(Base):
    """Modelo SQLAlchemy para tabla users."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    totp_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_2fa_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index('ix_users_email', 'email'),
        Index('ix_users_created_at', 'created_at'),
    )


class RefreshTokenModel(Base):
    """Modelo SQLAlchemy para tabla refresh_tokens."""
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    token: Mapped[str] = mapped_column(
        String(500), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index('ix_refresh_tokens_token', 'token'),
        Index('ix_refresh_tokens_user_id', 'user_id'),
        Index('ix_refresh_tokens_expires_at', 'expires_at'),
    )


class VerificationTokenModel(Base):
    """Modelo SQLAlchemy para tabla verification_tokens."""
    __tablename__ = "verification_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    token: Mapped[str] = mapped_column(
        String(500), unique=True, nullable=False)
    token_type: Mapped[str] = mapped_column(
        String(50), nullable=False)  # email_verification, password_reset
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index('ix_verification_tokens_token', 'token'),
        Index('ix_verification_tokens_user_id', 'user_id'),
        Index('ix_verification_tokens_type', 'token_type'),
        Index('ix_verification_tokens_expires_at', 'expires_at'),
    )


class PasswordHistoryModel(Base):
    """Modelo SQLAlchemy para tabla password_history."""
    __tablename__ = "password_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index('ix_password_history_user_created', 'user_id', 'created_at'),
    )
