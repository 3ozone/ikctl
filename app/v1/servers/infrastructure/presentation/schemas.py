"""Schemas Pydantic para requests y responses del módulo servers.

Solo responsabilidad HTTP: validar entrada y serializar salida.
No contienen lógica de negocio — delegan a use cases.
"""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# CREDENTIAL — Requests
# ---------------------------------------------------------------------------


class CreateCredentialRequest(BaseModel):
    """Body para POST /api/v1/credentials."""

    name: str = Field(..., min_length=1, max_length=255,
                      examples=["my-ssh-key"])
    type: str = Field(..., examples=["ssh"],
                      description="ssh | git_https | git_ssh")
    username: str | None = Field(None, max_length=255, examples=["root"])
    password: str | None = Field(None, max_length=1024, examples=["s3cr3t"])
    private_key: str | None = Field(
        None, description="Clave privada SSH en formato PEM"
    )


class UpdateCredentialRequest(BaseModel):
    """Body para PUT /api/v1/credentials/{id}."""

    name: str = Field(min_length=1, max_length=255)
    username: str | None = Field(None, max_length=255)
    password: str | None = Field(None, max_length=1024)
    private_key: str | None = Field(None)

    @field_validator("private_key", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: str | None) -> str | None:
        """Normaliza cadena vacía a None para borrar la clave privada existente."""
        if v == "":
            return None
        return v


# ---------------------------------------------------------------------------
# CREDENTIAL — Response
# ---------------------------------------------------------------------------


class CredentialResponse(BaseModel):
    """Response para operaciones sobre credenciales. Nunca expone password ni private_key."""

    credential_id: str
    user_id: str
    name: str
    credential_type: str
    username: str | None
    has_private_key: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CredentialListResponse(BaseModel):
    """Response paginada para listado de credenciales."""

    items: list[CredentialResponse]
    total: int
    page: int
    per_page: int


# ---------------------------------------------------------------------------
# SERVER — Requests
# ---------------------------------------------------------------------------


class RegisterServerRequest(BaseModel):
    """Body para POST /api/v1/servers — registrar servidor remoto."""

    name: str = Field(..., min_length=1, max_length=255, examples=["web-01"])
    host: str = Field(..., min_length=1, max_length=255,
                      examples=["192.168.1.10"])
    port: int = Field(22, ge=1, le=65535, examples=[22])
    credential_id: str | None = Field(None, examples=["cred-uuid"])
    description: str | None = Field(None, max_length=1024)


class RegisterLocalServerRequest(BaseModel):
    """Body para POST /api/v1/servers/local — registrar servidor local."""

    name: str = Field(..., min_length=1, max_length=255,
                      examples=["localhost"])
    description: str | None = Field(None, max_length=1024)


class UpdateServerRequest(BaseModel):
    """Body para PUT /api/v1/servers/{id}."""

    name: str = Field(min_length=1, max_length=255)
    host: str | None = Field(None, max_length=255)
    port: int | None = Field(None, ge=1, le=65535)
    credential_id: str | None = Field(None)
    description: str | None = Field(None, max_length=1024)


class ToggleServerStatusRequest(BaseModel):
    """Body para POST /api/v1/servers/{id}/toggle."""

    active: bool


# ---------------------------------------------------------------------------
# SERVER — Response
# ---------------------------------------------------------------------------


class ServerResponse(BaseModel):
    """Response para operaciones sobre servidores."""

    server_id: str
    user_id: str
    name: str
    server_type: str
    status: str
    host: str | None
    port: int | None
    credential_id: str | None
    description: str | None
    os_id: str | None
    os_version: str | None
    os_name: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ServerListResponse(BaseModel):
    """Response paginada para listado de servidores."""

    items: list[ServerResponse]
    total: int
    page: int
    per_page: int


class HealthCheckResponse(BaseModel):
    """Response del health check SSH de un servidor."""

    server_id: str
    status: str
    latency_ms: float | None
    os_id: str | None
    os_version: str | None
    os_name: str | None


# ---------------------------------------------------------------------------
# AD-HOC COMMAND — Request / Response
# ---------------------------------------------------------------------------


class AdHocCommandRequest(BaseModel):
    """Body para POST /api/v1/servers/{id}/exec."""

    command: str = Field(..., min_length=1,
                         max_length=2048, examples=["df -h"])
    sudo: bool = Field(False)
    timeout: int = Field(30, ge=1, le=600)


class AdHocCommandResponse(BaseModel):
    """Response de ejecutar un comando ad-hoc."""

    server_id: str
    command: str
    stdout: str
    stderr: str
    exit_code: int


# ---------------------------------------------------------------------------
# GROUP — Requests
# ---------------------------------------------------------------------------


class CreateGroupRequest(BaseModel):
    """Body para POST /api/v1/groups."""

    name: str = Field(..., min_length=1, max_length=255,
                      examples=["k8s-nodes"])
    description: str | None = Field(None, max_length=1024)
    server_ids: list[str] = Field(default_factory=list)


class UpdateGroupRequest(BaseModel):
    """Body para PUT /api/v1/groups/{id}."""

    name: str = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1024)
    server_ids: list[str] | None = Field(None)


# ---------------------------------------------------------------------------
# GROUP — Response
# ---------------------------------------------------------------------------


class GroupResponse(BaseModel):
    """Response para operaciones sobre grupos de servidores."""

    group_id: str
    user_id: str
    name: str
    description: str | None
    server_ids: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GroupListResponse(BaseModel):
    """Response paginada para listado de grupos."""

    items: list[GroupResponse]
    total: int
    page: int
    per_page: int
