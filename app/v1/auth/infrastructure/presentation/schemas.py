"""Schemas Pydantic para requests y responses de los endpoints auth.

Solo responsabilidad HTTP: validar entrada y serializar salida.
No contienen lógica de negocio — delegan a use cases.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# REQUEST schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """Body para POST /api/v1/auth/register."""

    name: str = Field(..., min_length=1, max_length=255,
                      examples=["Juan Pérez"])
    email: EmailStr = Field(..., examples=["juan@example.com"])
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        examples=["SecurePass123!"],
        description="Mínimo 8 caracteres, 1 mayúscula, 1 minúscula, 1 número",
    )

    @field_validator("password")
    @classmethod
    def password_no_null_bytes(cls, v: str) -> str:
        """Rechaza contraseñas que contengan null bytes."""
        if "\x00" in v:
            raise ValueError("La contraseña no puede contener null bytes")
        return v


class VerifyEmailRequest(BaseModel):
    """Body para POST /api/v1/auth/verify-email."""

    token: str = Field(..., min_length=1)


class ResendVerificationRequest(BaseModel):
    """Body para POST /api/v1/auth/resend-verification."""

    email: EmailStr


class LoginRequest(BaseModel):
    """Body para POST /api/v1/auth/login."""

    email: EmailStr = Field(..., examples=["juan@example.com"])
    password: str = Field(..., min_length=1, examples=["SecurePass123!"])


class Login2FARequest(BaseModel):
    """Body para POST /api/v1/auth/login/2fa."""

    temp_token: str = Field(...,
                            description="Token temporal recibido tras login básico")
    code: str = Field(..., min_length=6, max_length=6, examples=["123456"])


class RefreshRequest(BaseModel):
    """Body para POST /api/v1/auth/refresh."""

    refresh_token: str = Field(..., min_length=1)


class LogoutRequest(BaseModel):
    """Body para POST /api/v1/auth/logout."""

    refresh_token: str = Field(..., min_length=1)


class ForgotPasswordRequest(BaseModel):
    """Body para POST /api/v1/auth/password/forgot."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Body para POST /api/v1/auth/password/reset."""

    token: str = Field(..., min_length=1)
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        examples=["NewSecurePass123!"],
    )


class UpdateProfileRequest(BaseModel):
    """Body para PUT /api/v1/auth/users/me."""

    name: str = Field(..., min_length=1, max_length=255,
                      examples=["Juan Pérez"])


class ChangePasswordRequest(BaseModel):
    """Body para PUT /api/v1/auth/users/me/password."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class Enable2FAVerifyRequest(BaseModel):
    """Body para POST /api/v1/auth/users/me/2fa/verify — confirma el setup."""

    code: str = Field(..., min_length=6, max_length=6, examples=["123456"])


class Disable2FARequest(BaseModel):
    """Body para POST /api/v1/auth/users/me/2fa/disable."""

    code: str = Field(..., min_length=6, max_length=6, examples=["123456"])


# ---------------------------------------------------------------------------
# RESPONSE schemas
# ---------------------------------------------------------------------------

class MessageResponse(BaseModel):
    """Respuesta genérica con mensaje."""

    message: str


class RegisterResponse(BaseModel):
    """Response para POST /api/v1/auth/register — 201."""

    message: str
    user_id: str


class TokenResponse(BaseModel):
    """Response con access_token — el refresh_token va en HttpOnly cookie (T-51.2)."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(
        description="Segundos hasta la expiración del access_token")


class LoginResponse(TokenResponse):
    """Response para POST /api/v1/auth/login — puede incluir indicadores de estado."""

    refresh_token: Optional[str] = Field(
        default=None,
        description="Refresh token para renovar el access token",
    )
    requires_2fa: bool = False
    temp_token: Optional[str] = Field(
        default=None,
        description="Token temporal si se requiere 2FA para completar login",
    )


class UserProfileResponse(BaseModel):
    """Response para GET /api/v1/auth/users/me."""

    id: str
    name: str
    email: str
    is_verified: bool
    is_2fa_enabled: bool
    created_at: datetime
    updated_at: datetime


class TOTPSetupResponse(BaseModel):
    """Response para POST /api/v1/auth/users/me/2fa/enable."""

    secret: str
    qr_code_uri: str
    provisioning_uri: str
    backup_codes: list[str]


class GitHubAuthResponse(BaseModel):
    """Response para POST /api/v1/auth/login/github."""

    authorization_url: str


class ErrorResponse(BaseModel):
    """Schema estándar para respuestas de error."""

    detail: str
