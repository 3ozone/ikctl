"""DTO para resultado del health check de un servidor."""
from dataclasses import dataclass


@dataclass(frozen=True)
class HealthCheckResult:
    """Resultado del health check SSH de un servidor."""

    server_id: str
    status: str  # "online" | "offline"
    latency_ms: float | None
    os_id: str | None
    os_version: str | None
    os_name: str | None
