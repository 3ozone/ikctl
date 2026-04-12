"""Configuración centralizada — variables de entorno via Pydantic BaseSettings.

Los adaptadores reciben estos valores por inyección desde el Composition Root
(main.py). Nunca importan Settings directamente.
"""
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centraliza todas las variables de entorno de la aplicación."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Base de datos
    DB_URL: str = "mysql+aiomysql://root:secret@localhost:3306/ikctl"

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # SMTP
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@ikctl.local"
    SMTP_FROM_NAME: str = "ikctl"

    # App
    APP_BASE_URL: str = "http://localhost:8089"

    # Valkey / Redis
    VALKEY_URL: str = "redis://localhost:6379/0"

    # GitHub OAuth
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    # Apunta al frontend — GitHub redirige el navegador a la página callback de Next.js
    GITHUB_REDIRECT_URI: str = "http://localhost:3000/login/github/callback"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://0.0.0.0:3000"]

    # Cifrado AES-256-GCM para credenciales en reposo (exactamente 32 bytes ASCII)
    ENCRYPTION_KEY: str = "dev-only-key-change-in-prod-0000"
