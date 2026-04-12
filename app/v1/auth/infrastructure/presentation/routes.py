"""Router FastAPI para el módulo auth.

Endpoints:
    POST /api/v1/auth/register                  — registro de usuario (T-34)
    POST /api/v1/auth/verify-email              — verificación de email (T-35)
    POST /api/v1/auth/resend-verification       — reenviar email de verificación (T-36)
    POST /api/v1/auth/login                     — login con email/password (T-37)
    POST /api/v1/auth/login/github              — inicio OAuth GitHub (T-38)
    GET  /api/v1/auth/login/github/callback     — callback OAuth GitHub (T-39)
    POST /api/v1/auth/login/2fa                 — completar login con TOTP (T-40)
    POST /api/v1/auth/refresh                   — renovar access token (T-41)
    POST /api/v1/auth/logout                    — cerrar sesión (T-42)
    POST /api/v1/auth/password/forgot           — solicitar reset de contraseña (T-43)
    POST /api/v1/auth/password/reset            — confirmar reset de contraseña (T-44)
    GET  /api/v1/auth/users/me                  — obtener perfil del usuario (T-45)
    PUT  /api/v1/auth/users/me                  — actualizar perfil del usuario (T-46)
    PUT  /api/v1/auth/users/me/password         — cambiar contraseña (T-47)
    POST /api/v1/auth/users/me/2fa/enable       — iniciar setup 2FA (T-48)
    POST /api/v1/auth/users/me/2fa/verify       — verificar código TOTP (T-49)
    POST /api/v1/auth/users/me/2fa/disable      — deshabilitar 2FA (T-50)
"""
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.v1.shared.infrastructure.logger import get_logger


from app.v1.auth.application.commands.authenticate_with_github import AuthenticateWithGitHub
from app.v1.auth.application.commands.create_tokens import CreateTokens
from app.v1.auth.application.commands.refresh_access_token import RefreshAccessToken
from app.v1.auth.application.commands.generate_verification_token import GenerateVerificationToken
from app.v1.auth.application.commands.register_user import RegisterUser
from app.v1.auth.application.commands.reset_password import ResetPassword
from app.v1.auth.application.commands.revoke_refresh_token import RevokeRefreshToken
from app.v1.auth.application.commands.verify_email import VerifyEmail
from app.v1.auth.application.commands.update_user_profile import UpdateUserProfile
from app.v1.auth.application.commands.change_password import ChangePassword
from app.v1.auth.application.commands.enable_2fa import Enable2FA
from app.v1.auth.application.commands.disable_2fa import Disable2FA
from app.v1.auth.application.queries.get_user_profile import GetUserProfile
from app.v1.auth.application.exceptions import ResourceNotFoundError, UserBlockedError
from app.v1.auth.application.interfaces.email_service import EmailService
from app.v1.auth.application.interfaces.github_oauth import GitHubOAuth
from app.v1.auth.application.interfaces.jwt_provider import JWTProvider
from app.v1.auth.application.interfaces.login_attempt_tracker import LoginAttemptTracker
from app.v1.auth.application.interfaces.totp_provider import TOTPProvider
from app.v1.auth.application.queries.hash_password import HashPassword
from app.v1.auth.application.queries.verify_password import VerifyPassword
from app.v1.auth.application.queries.verify_2fa import Verify2FA
from app.v1.auth.domain.entities.refresh_token import RefreshToken
from app.v1.auth.domain.entities.verification_token import VerificationToken
from app.v1.auth.infrastructure.presentation.deps import (
    get_email_service,
    get_event_bus,
    get_github_oauth,
    get_jwt_provider,
    get_login_attempt_tracker,
    get_password_history_repository,
    get_refresh_token_repository,
    get_totp_provider,
    get_user_repository,
    get_verification_token_repository,
    require_verified_email,
)
from app.v1.auth.infrastructure.presentation.schemas import (
    ChangePasswordRequest,
    Disable2FARequest,
    Enable2FAVerifyRequest,
    ForgotPasswordRequest,
    GitHubAuthResponse,
    Login2FARequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    UserProfileResponse,
    TOTPSetupResponse,
    VerifyEmailRequest,
)
from app.v1.auth.infrastructure.repositories.refresh_token_repository import (
    SQLAlchemyRefreshTokenRepository,
)
from app.v1.auth.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from app.v1.auth.infrastructure.repositories.verification_token_repository import (
    SQLAlchemyVerificationTokenRepository,
)
from app.v1.auth.infrastructure.repositories.password_history_repository import (
    SQLAlchemyPasswordHistoryRepository,
)
from app.v1.shared.application.interfaces.event_bus import EventBus
from app.v1.shared.domain.exceptions import DomainException

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
logger = get_logger(__name__)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar usuario",
    description=(
        "Crea una cuenta nueva. "
        "Devuelve el user_id y un mensaje indicando que se debe verificar el email."
    ),
)
async def register(
    body: RegisterRequest,
    user_repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
    verification_token_repository: Annotated[SQLAlchemyVerificationTokenRepository, Depends(get_verification_token_repository)],
    email_service: Annotated[EmailService, Depends(get_email_service)],
    event_bus: Annotated[EventBus, Depends(get_event_bus)],
) -> RegisterResponse:
    """Endpoint POST /api/v1/auth/register — T-34.

    Args:
        body: RegisterRequest con name, email y password.
        user_repository: Repositorio de usuarios (scoped al request).
        verification_token_repository: Repositorio de tokens (scoped al request).
        email_service: Servicio de email para enviar verificación.
        event_bus: EventBus singleton para publicar UserRegistered.

    Returns:
        RegisterResponse con message y user_id.

    Raises:
        InvalidEmailError: 400 si el email es inválido.
        InvalidUserError: 400 si el nombre o la contraseña son inválidos.
    """
    hash_password = HashPassword()
    password_hash = hash_password.execute(body.password)

    use_case = RegisterUser(
        event_bus=event_bus,
        user_repository=user_repository,
    )
    result = await use_case.execute(
        name=body.name,
        email=body.email,
        password_hash=password_hash,
    )

    gen_token = GenerateVerificationToken(
        verification_token_repository=verification_token_repository,
    )
    token_result = await gen_token.execute(
        user_id=result.user_id,
        token_type="email_verification",
    )

    await email_service.send_verification_email(
        to_email=result.email,
        token=token_result.token,
        user_name=body.name,
    )

    return RegisterResponse(
        message="Usuario registrado. Verifica tu email para activar tu cuenta.",
        user_id=result.user_id,
    )


@router.post(
    "/verify-email",
    status_code=status.HTTP_200_OK,
    summary="Verificar email",
    description="Verifica el email del usuario usando el token recibido por correo.",
)
async def verify_email(
    body: VerifyEmailRequest,
    verification_token_repository: Annotated[SQLAlchemyVerificationTokenRepository, Depends(get_verification_token_repository)],
    user_repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
    event_bus: Annotated[EventBus, Depends(get_event_bus)],
) -> MessageResponse:
    """Endpoint POST /api/v1/auth/verify-email — T-35.

    Args:
        body: VerifyEmailRequest con el token de verificación.
        verification_token_repository: Repositorio de tokens (scoped al request).
        user_repository: Repositorio de usuarios (scoped al request).
        event_bus: EventBus singleton para publicar EmailVerified.

    Returns:
        MessageResponse con confirmación de verificación.

    Raises:
        ResourceNotFoundError: 404 si el token no existe o el usuario no existe.
        InvalidVerificationTokenError: 400 si el token ha expirado o es inválido.
    """
    token = await verification_token_repository.find_by_token(body.token)
    if token is None:
        raise ResourceNotFoundError("Token de verificación no encontrado.")

    use_case = VerifyEmail(event_bus=event_bus)
    await use_case.execute(verification_token=token)

    user = await user_repository.find_by_id(token.user_id)
    if user is None:
        raise ResourceNotFoundError(f"Usuario con ID {token.user_id} no encontrado.")

    user.verify_email()
    await user_repository.update(user)

    return MessageResponse(message="Email verificado correctamente.")


@router.post(
    "/resend-verification",
    status_code=status.HTTP_200_OK,
    summary="Reenviar email de verificación",
    description="Genera un nuevo token y reenvía el email de verificación al usuario.",
)
async def resend_verification(
    body: ResendVerificationRequest,
    user_repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
    verification_token_repository: Annotated[SQLAlchemyVerificationTokenRepository, Depends(get_verification_token_repository)],
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> MessageResponse:
    """Endpoint POST /api/v1/auth/resend-verification — T-36.

    Args:
        body: ResendVerificationRequest con el email del usuario.
        user_repository: Repositorio de usuarios (scoped al request).
        verification_token_repository: Repositorio de tokens (scoped al request).
        email_service: Servicio de email para reenviar el correo.

    Returns:
        MessageResponse con confirmación del reenvío.

    Raises:
        ResourceNotFoundError: 404 si el email no está registrado.
    """
    user = await user_repository.find_by_email(body.email)
    if user is None:
        raise ResourceNotFoundError("Usuario no encontrado.")

    now = datetime.now(timezone.utc)
    token = VerificationToken(
        id=str(uuid4()),
        user_id=user.id,
        token=str(uuid4()),
        token_type="email_verification",
        expires_at=now + timedelta(hours=24),
        created_at=now,
    )
    await verification_token_repository.save(token)
    await email_service.send_verification_email(user.email.value, token.token, user.name)

    return MessageResponse(message="Email de verificación reenviado correctamente.")


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="Login",
    description="Autentica al usuario con email y contraseña. Si tiene 2FA activo devuelve requires_2fa=true.",
)
async def login(
    body: LoginRequest,
    response: Response,
    user_repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
    refresh_token_repository: Annotated[SQLAlchemyRefreshTokenRepository, Depends(get_refresh_token_repository)],
    login_attempt_tracker: Annotated[LoginAttemptTracker, Depends(get_login_attempt_tracker)],
    jwt_provider: Annotated[JWTProvider, Depends(get_jwt_provider)],
) -> LoginResponse:
    """Endpoint POST /api/v1/auth/login — T-37.

    Args:
        body: LoginRequest con email y password.
        user_repository: Repositorio de usuarios (scoped al request).
        refresh_token_repository: Repositorio de refresh tokens (scoped al request).
        login_attempt_tracker: Servicio de rastreo de intentos fallidos (singleton).
        jwt_provider: Proveedor JWT para generar tokens (singleton).

    Returns:
        LoginResponse con access_token y refresh_token, o requires_2fa=True.

    Raises:
        HTTPException 401: si el email no está registrado o la contraseña es incorrecta.
        UserBlockedError: 429 si el usuario está bloqueado por intentos fallidos.
    """
    user = await user_repository.find_by_email(body.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas.",
        )

    if await login_attempt_tracker.is_blocked(body.email):
        raise UserBlockedError(
            "Cuenta bloqueada temporalmente por demasiados intentos fallidos.")

    verify_password = VerifyPassword()
    if not verify_password.execute(body.password, user.password_hash):
        await login_attempt_tracker.record_failed_attempt(body.email)
        logger.warning("login_failed", email=body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas.")

    await login_attempt_tracker.reset_attempts(body.email)
    logger.info("login_success", user_id=user.id, email=body.email)

    if user.is_2fa_required():
        temp_token = jwt_provider.create_access_token(user_id=user.id).token
        return LoginResponse(
            requires_2fa=True,
            temp_token=temp_token,
            access_token="",
            expires_in=0,
        )

    # Usar jwt_provider (inyectado con el secret del .env) en lugar de
    # CreateTokens que tiene el secret key hardcodeado
    access_token_obj = jwt_provider.create_access_token(
        user_id=user.id,
        additional_claims={"role": user.role},
    )
    refresh_token_value = str(uuid4())

    now = datetime.now(timezone.utc)
    refresh_token = RefreshToken(
        id=str(uuid4()),
        user_id=user.id,
        token=refresh_token_value,
        expires_at=now + timedelta(days=7),
        created_at=now,
    )
    await refresh_token_repository.save(refresh_token)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token_value,
        httponly=True,
        secure=False,  # True en producción (HTTPS)
        samesite="lax",
        max_age=7 * 24 * 60 * 60,  # 7 días en segundos
    )

    return LoginResponse(
        access_token=access_token_obj.token,
        refresh_token=refresh_token_value,
        token_type="Bearer",
        expires_in=CreateTokens.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/login/github",
    status_code=status.HTTP_200_OK,
    summary="Iniciar autenticación GitHub OAuth",
    description="Genera la URL de autorización de GitHub para iniciar el flujo OAuth.",
)
async def login_github(
    github_oauth: Annotated[GitHubOAuth, Depends(get_github_oauth)],
) -> GitHubAuthResponse:
    """Endpoint POST /api/v1/auth/login/github — T-38.

    Args:
        github_oauth: Proveedor OAuth de GitHub (singleton).

    Returns:
        GitHubAuthResponse con la authorization_url de GitHub.
    """
    state = str(uuid4())
    authorization_url = github_oauth.get_authorization_url(state)
    return GitHubAuthResponse(authorization_url=authorization_url)


@router.get(
    "/login/github/callback",
    status_code=status.HTTP_200_OK,
    summary="Callback GitHub OAuth",
    description="Intercambia el código de GitHub por tokens JWT y autentica al usuario.",
)
async def login_github_callback(
    code: str,
    state: str,
    response: Response,
    user_repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
    refresh_token_repository: Annotated[SQLAlchemyRefreshTokenRepository, Depends(get_refresh_token_repository)],
    github_oauth: Annotated[GitHubOAuth, Depends(get_github_oauth)],
    jwt_provider: Annotated[JWTProvider, Depends(get_jwt_provider)],
) -> LoginResponse:
    """Endpoint GET /api/v1/auth/login/github/callback — T-39.

    Args:
        code: Authorization code recibido de GitHub.
        state: CSRF state token (validación pendiente en T-51).
        response: Objeto Response de FastAPI para establecer cookies.
        user_repository: Repositorio de usuarios (scoped al request).
        refresh_token_repository: Repositorio de refresh tokens (scoped al request).
        github_oauth: Proveedor OAuth de GitHub (singleton).
        jwt_provider: Proveedor JWT para generar tokens (singleton).

    Returns:
        LoginResponse con access_token y refresh_token.

    Raises:
        InvalidTokenError: Si el código de GitHub es inválido o expirado.
    """
    use_case = AuthenticateWithGitHub(
        user_repository=user_repository,
        github_oauth=github_oauth,
        jwt_provider=jwt_provider,
    )
    result = await use_case.execute(code=code)

    now = datetime.now(timezone.utc)
    refresh_token = RefreshToken(
        id=str(uuid4()),
        user_id=result.user_id,
        token=result.refresh_token,
        expires_at=now + timedelta(days=7),
        created_at=now,
    )
    await refresh_token_repository.save(refresh_token)

    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=True,
        secure=False,  # True en producción (HTTPS)
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
    )

    return LoginResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type="Bearer",
        expires_in=CreateTokens.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/login/2fa",
    status_code=status.HTTP_200_OK,
    summary="Completar login con 2FA",
    description="Verifica el código TOTP y devuelve tokens si es correcto.",
)
async def login_2fa(
    body: Login2FARequest,
    response: Response,
    user_repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
    refresh_token_repository: Annotated[SQLAlchemyRefreshTokenRepository, Depends(get_refresh_token_repository)],
    totp_provider: Annotated[TOTPProvider, Depends(get_totp_provider)],
    jwt_provider: Annotated[JWTProvider, Depends(get_jwt_provider)],
) -> LoginResponse:
    """Endpoint POST /api/v1/auth/login/2fa — T-40.

    Args:
        body: Login2FARequest con temp_token y código TOTP de 6 dígitos.
        user_repository: Repositorio de usuarios (scoped al request).
        refresh_token_repository: Repositorio de refresh tokens (scoped al request).
        totp_provider: Proveedor TOTP para verificar el código (singleton).
        jwt_provider: Proveedor JWT para decodificar temp_token y generar tokens (singleton).

    Returns:
        LoginResponse con access_token y refresh_token.

    Raises:
        HTTPException 401: Si el código TOTP es incorrecto.
        ResourceNotFoundError: 404 si el usuario no existe.
    """
    payload = jwt_provider.decode_token(body.temp_token)
    user_id: str = payload.get("sub") or ""
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token temporal inválido.",
        )

    verify_2fa = Verify2FA(
        user_repository=user_repository,
        totp_provider=totp_provider,
    )
    is_valid = await verify_2fa.execute(user_id=user_id, code=body.code)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código 2FA incorrecto.",
        )

    user = await user_repository.find_by_id(user_id)
    if user is None:
        raise ResourceNotFoundError(f"Usuario con ID {user_id} no encontrado.")

    access_token_obj = jwt_provider.create_access_token(
        user_id=user_id,
        additional_claims={"role": user.role},
    )
    refresh_token_obj = jwt_provider.create_refresh_token(user_id=user_id)

    now = datetime.now(timezone.utc)
    refresh_token = RefreshToken(
        id=str(uuid4()),
        user_id=user_id,
        token=refresh_token_obj.token,
        expires_at=now + timedelta(days=7),
        created_at=now,
    )
    await refresh_token_repository.save(refresh_token)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token_obj.token,
        httponly=True,
        secure=False,  # True en producción (HTTPS)
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
    )

    return LoginResponse(
        access_token=access_token_obj.token,
        refresh_token=refresh_token_obj.token,
        token_type="Bearer",
        expires_in=CreateTokens.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    summary="Renovar access token",
    description="Genera un nuevo access token usando un refresh token válido.",
)
async def refresh(
    request: Request,
    response: Response,
    refresh_token_repository: Annotated[SQLAlchemyRefreshTokenRepository, Depends(get_refresh_token_repository)],
    jwt_provider: Annotated[JWTProvider, Depends(get_jwt_provider)],
) -> LoginResponse:
    """Endpoint POST /api/v1/auth/refresh — T-41.

    Args:
        request: Objeto Request de FastAPI para leer la cookie refresh_token.
        response: Objeto Response de FastAPI para establecer cookies.
        refresh_token_repository: Repositorio de refresh tokens (scoped al request).

    Returns:
        LoginResponse con nuevo access_token.

    Raises:
        HTTPException 401: Si el token no existe, ha expirado o la cookie no está presente.
    """
    refresh_token_value = request.cookies.get("refresh_token")
    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token no encontrado.",
        )
    stored = await refresh_token_repository.find_by_token(refresh_token_value)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token no encontrado.",
        )

    if stored.is_expired():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expirado.",
        )

    new_access_token = RefreshAccessToken(
        jwt_provider=jwt_provider).execute(stored)
    logger.info("token_refreshed", user_id=stored.user_id)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token_value,
        httponly=True,
        secure=False,  # True en producción (HTTPS)
        samesite="lax",
        max_age=7 * 24 * 60 * 60,  # 7 días en segundos
    )

    return LoginResponse(
        access_token=new_access_token,
        token_type="Bearer",
        expires_in=RefreshAccessToken.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Cerrar sesión",
    description="Revoca el refresh token e invalida la sesión del usuario.",
)
async def logout(
    request: Request,
    response: Response,
    refresh_token_repository: Annotated[SQLAlchemyRefreshTokenRepository, Depends(get_refresh_token_repository)],
) -> MessageResponse:
    """Endpoint POST /api/v1/auth/logout — T-42.

    Args:
        request: Objeto Request de FastAPI para leer la cookie refresh_token.
        response: Objeto Response de FastAPI para limpiar cookies.
        refresh_token_repository: Repositorio de refresh tokens (scoped al request).

    Returns:
        MessageResponse con confirmación de cierre de sesión.

    Raises:
        HTTPException 401: Si el refresh token no existe o la cookie no está presente.
    """
    refresh_token_value = request.cookies.get("refresh_token")
    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token no encontrado.",
        )
    stored = await refresh_token_repository.find_by_token(refresh_token_value)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token no encontrado.",
        )

    RevokeRefreshToken().execute(stored)
    await refresh_token_repository.delete(stored.id)

    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=False,  # True en producción (HTTPS)
        samesite="lax",
    )

    return MessageResponse(message="Sesión cerrada correctamente.")


@router.post(
    "/password/forgot",
    status_code=status.HTTP_200_OK,
    summary="Solicitar reset de contraseña",
    description="Envía un email con enlace de reset de contraseña. Siempre responde 200 por seguridad.",
)
async def forgot_password(
    body: ForgotPasswordRequest,
    user_repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
    verification_token_repository: Annotated[SQLAlchemyVerificationTokenRepository, Depends(get_verification_token_repository)],
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> MessageResponse:
    """Endpoint POST /api/v1/auth/password/forgot — T-43.

    Args:
        body: ForgotPasswordRequest con el email del usuario.
        user_repository: Repositorio de usuarios (scoped al request).
        verification_token_repository: Repositorio de tokens (scoped al request).
        email_service: Servicio de email para enviar el enlace de reset.

    Returns:
        MessageResponse genérico — siempre 200 para no revelar si el email existe.
    """
    _GENERIC_MESSAGE = "Si el email está registrado, recibirás un enlace para restablecer tu contraseña."

    user = await user_repository.find_by_email(body.email)
    if user is None:
        return MessageResponse(message=_GENERIC_MESSAGE)

    now = datetime.now(timezone.utc)
    token = VerificationToken(
        id=str(uuid4()),
        user_id=user.id,
        token=str(uuid4()),
        token_type="password_reset",
        expires_at=now + timedelta(hours=24),
        created_at=now,
    )
    await verification_token_repository.save(token)
    await email_service.send_password_reset_email(user.email.value, token.token, user.name)

    return MessageResponse(message=_GENERIC_MESSAGE)


@router.post(
    "/password/reset",
    status_code=status.HTTP_200_OK,
    summary="Confirmar reset de contraseña",
    description="Valida el token de reset y actualiza la contraseña del usuario.",
)
async def reset_password(
    body: ResetPasswordRequest,
    user_repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
    verification_token_repository: Annotated[SQLAlchemyVerificationTokenRepository, Depends(get_verification_token_repository)],
) -> MessageResponse:
    """Endpoint POST /api/v1/auth/password/reset — T-44.

    Args:
        body: ResetPasswordRequest con token y nueva contraseña.
        user_repository: Repositorio de usuarios (scoped al request).
        verification_token_repository: Repositorio de tokens (scoped al request).

    Returns:
        MessageResponse con confirmación del reset.

    Raises:
        ResourceNotFoundError: 404 si el token no existe.
        InvalidVerificationTokenError: 400 si el token ha expirado o es de tipo incorrecto.
    """
    token = await verification_token_repository.find_by_token(body.token)
    if token is None:
        raise ResourceNotFoundError("Token de reset no encontrado.")

    # Lanza InvalidVerificationTokenError (DomainException → 400) si expirado
    token.is_valid_for_password_reset()

    user = await user_repository.find_by_id(token.user_id)
    if user is None:
        raise ResourceNotFoundError("Usuario no encontrado.")

    ResetPassword(hash_password=HashPassword()).execute(
        user=user,
        reset_token=token,
        new_password=body.new_password,
    )
    await user_repository.update(user)
    await verification_token_repository.delete(token.id)

    return MessageResponse(message="Contraseña actualizada correctamente.")


@router.get(
    "/users/me",
    status_code=status.HTTP_200_OK,
    summary="Obtener perfil del usuario",
    description="Devuelve los datos del perfil del usuario autenticado.",
)
async def get_profile(
    user_id: Annotated[str, Depends(require_verified_email)],
    user_repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
) -> UserProfileResponse:
    """Endpoint GET /api/v1/auth/users/me — T-45.

    Args:
        user_id: ID del usuario autenticado, inyectado por el middleware.
        user_repository: Repositorio de usuarios (scoped al request).

    Returns:
        UserProfileResponse con los datos del perfil.

    Raises:
        ResourceNotFoundError: 404 si el usuario no existe.
    """
    use_case = GetUserProfile(user_repository=user_repository)
    profile = await use_case.execute(user_id=user_id)

    return UserProfileResponse(
        id=profile.id,
        name=profile.name,
        email=profile.email,
        is_verified=profile.is_verified,
        is_2fa_enabled=profile.is_2fa_enabled,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.put(
    "/users/me",
    status_code=status.HTTP_200_OK,
    summary="Actualizar perfil del usuario",
    description="Actualiza el nombre del usuario autenticado y devuelve el perfil actualizado.",
)
async def update_profile(
    body: UpdateProfileRequest,
    user_id: Annotated[str, Depends(require_verified_email)],
    user_repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
) -> UserProfileResponse:
    """Endpoint PUT /api/v1/auth/users/me — T-46.

    Args:
        body: Datos a actualizar (name).
        user_id: ID del usuario autenticado, inyectado por el middleware.
        user_repository: Repositorio de usuarios (scoped al request).

    Returns:
        UserProfileResponse con el perfil actualizado.

    Raises:
        ResourceNotFoundError: 404 si el usuario no existe.
    """
    await UpdateUserProfile(user_repository=user_repository).execute(
        user_id=user_id,
        new_name=body.name,
    )

    profile = await GetUserProfile(user_repository=user_repository).execute(
        user_id=user_id
    )

    return UserProfileResponse(
        id=profile.id,
        name=profile.name,
        email=profile.email,
        is_verified=profile.is_verified,
        is_2fa_enabled=profile.is_2fa_enabled,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.put(
    "/users/me/password",
    status_code=status.HTTP_200_OK,
    summary="Cambiar contraseña",
    description="Cambia la contraseña del usuario autenticado. Requiere la contraseña actual.",
)
async def change_password(
    body: ChangePasswordRequest,
    user_id: Annotated[str, Depends(require_verified_email)],
    user_repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
    password_history_repository: Annotated[
        SQLAlchemyPasswordHistoryRepository,
        Depends(get_password_history_repository),
    ],
) -> MessageResponse:
    """Endpoint PUT /api/v1/auth/users/me/password — T-47.

    Args:
        body: current_password y new_password.
        user_id: ID del usuario autenticado, inyectado por el middleware.
        user_repository: Repositorio de usuarios (scoped al request).
        password_history_repository: Repositorio de historial de contraseñas.

    Returns:
        MessageResponse de confirmación.

    Raises:
        ResourceNotFoundError: 404 si el usuario no existe.
        InvalidUserError: 400 si la contraseña actual es incorrecta.
        UnauthorizedOperationError: 403 si intenta reutilizar una de las últimas 3 contraseñas.
    """
    user = await user_repository.find_by_id(user_id)
    if user is None:
        raise ResourceNotFoundError(f"Usuario con ID {user_id} no encontrado")

    await ChangePassword(
        hash_password=HashPassword(),
        verify_password=VerifyPassword(),
        password_history_repository=password_history_repository,
    ).execute(
        user=user,
        current_password=body.current_password,
        new_password=body.new_password,
    )

    await user_repository.update(user)
    logger.info("password_changed", user_id=user_id)

    return MessageResponse(message="Contraseña cambiada correctamente.")


@router.post(
    "/users/me/2fa/enable",
    status_code=status.HTTP_200_OK,
    summary="Iniciar setup de 2FA",
    description="Genera un secret TOTP y QR code para configurar 2FA en el usuario autenticado.",
)
async def enable_2fa(
    user_id: Annotated[str, Depends(require_verified_email)],
    user_repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
    totp_provider: Annotated[TOTPProvider, Depends(get_totp_provider)],
) -> TOTPSetupResponse:
    """Endpoint POST /api/v1/auth/users/me/2fa/enable — T-48.

    Args:
        user_id: ID del usuario autenticado, inyectado por el middleware.
        user_repository: Repositorio de usuarios (scoped al request).
        totp_provider: Proveedor TOTP singleton.

    Returns:
        TOTPSetupResponse con secret y qr_code_uri para configurar la app 2FA.

    Raises:
        ResourceNotFoundError: 404 si el usuario no existe.
    """
    setup = await Enable2FA(
        user_repository=user_repository,
        totp_provider=totp_provider,
    ).execute(user_id=user_id)
    logger.info("2fa_enabled", user_id=user_id)

    return TOTPSetupResponse(
        secret=setup.secret,
        qr_code_uri=setup.qr_code_uri,
        provisioning_uri=setup.provisioning_uri,
        backup_codes=setup.backup_codes,
    )


@router.post(
    "/users/me/2fa/verify",
    status_code=status.HTTP_200_OK,
    summary="Verificar código TOTP",
    description="Verifica un código TOTP de 6 dígitos para confirmar el setup 2FA.",
)
async def verify_2fa(
    body: Enable2FAVerifyRequest,
    user_id: Annotated[str, Depends(require_verified_email)],
    user_repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
    totp_provider: Annotated[TOTPProvider, Depends(get_totp_provider)],
) -> MessageResponse:
    """Endpoint POST /api/v1/auth/users/me/2fa/verify — T-49.

    Args:
        body: Código TOTP de 6 dígitos.
        user_id: ID del usuario autenticado, inyectado por el middleware.
        user_repository: Repositorio de usuarios (scoped al request).
        totp_provider: Proveedor TOTP singleton.

    Returns:
        MessageResponse de confirmación.

    Raises:
        ResourceNotFoundError: 404 si el usuario no existe.
        UnauthorizedOperationError: 403 si 2FA no está habilitado.
        DomainException: 400 si el código TOTP es inválido.
    """
    is_valid = await Verify2FA(
        user_repository=user_repository,
        totp_provider=totp_provider,
    ).execute(user_id=user_id, code=body.code)

    if not is_valid:
        raise DomainException("Código TOTP inválido")

    return MessageResponse(message="Código TOTP verificado correctamente.")


@router.post(
    "/users/me/2fa/disable",
    status_code=status.HTTP_200_OK,
    summary="Deshabilitar 2FA",
    description="Deshabilita 2FA del usuario autenticado. Requiere código TOTP válido.",
)
async def disable_2fa(
    body: Disable2FARequest,
    user_id: Annotated[str, Depends(require_verified_email)],
    user_repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
    totp_provider: Annotated[TOTPProvider, Depends(get_totp_provider)],
) -> MessageResponse:
    """Endpoint POST /api/v1/auth/users/me/2fa/disable — T-50.

    Args:
        body: Código TOTP de confirmación.
        user_id: ID del usuario autenticado, inyectado por el middleware.
        user_repository: Repositorio de usuarios (scoped al request).
        totp_provider: Proveedor TOTP singleton.

    Returns:
        MessageResponse de confirmación.

    Raises:
        ResourceNotFoundError: 404 si el usuario no existe.
        UnauthorizedOperationError: 403 si 2FA no está habilitado.
        DomainException: 400 si el código TOTP es inválido.
    """
    is_valid = await Verify2FA(
        user_repository=user_repository,
        totp_provider=totp_provider,
    ).execute(user_id=user_id, code=body.code)

    if not is_valid:
        raise DomainException("Código TOTP inválido")

    await Disable2FA(user_repository=user_repository).execute(user_id=user_id)

    return MessageResponse(message="2FA deshabilitado correctamente.")


@router.delete(
    "/users/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar cuenta",
    description="Elimina permanentemente la cuenta del usuario autenticado (GDPR - derecho al olvido).",
)
async def delete_account(
    user_id: Annotated[str, Depends(require_verified_email)],
    user_repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
) -> None:
    """Endpoint DELETE /api/v1/auth/users/me — T-51.4.

    Args:
        user_id: ID del usuario autenticado, verificado por require_verified_email.
        user_repository: Repositorio de usuarios (scoped al request).

    Returns:
        None — 204 No Content.

    Raises:
        ResourceNotFoundError: 404 si el usuario no existe.
        UnauthorizedOperationError: 403 si el email no está verificado.
    """
    await user_repository.delete(user_id)


@router.get(
    "/users/me/data",
    status_code=status.HTTP_200_OK,
    summary="Exportar datos personales",
    description="Devuelve todos los datos personales del usuario autenticado (GDPR - derecho de acceso).",
)
async def export_user_data(
    user_id: Annotated[str, Depends(require_verified_email)],
    user_repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
) -> UserProfileResponse:
    """Endpoint GET /api/v1/auth/users/me/data — T-51.5.

    Args:
        user_id: ID del usuario autenticado, verificado por require_verified_email.
        user_repository: Repositorio de usuarios (scoped al request).

    Returns:
        UserProfileResponse con todos los datos personales del usuario.

    Raises:
        ResourceNotFoundError: 404 si el usuario no existe.
        UnauthorizedOperationError: 403 si el email no está verificado.
    """
    user = await user_repository.find_by_id(user_id)
    if user is None:
        raise ResourceNotFoundError(f"Usuario con ID {user_id} no encontrado")

    return UserProfileResponse(
        id=user.id,
        name=user.name,
        email=user.email.value,
        is_verified=user.is_email_verified,
        is_2fa_enabled=user.is_2fa_enabled,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
