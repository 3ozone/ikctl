"""Contract tests — port Connection (T-68).

Verifica que SSHConnectionAdapter y LocalConnectionAdapter implementan
correctamente el contrato definido en Connection (ABC):
1. Ambos son instancias de Connection (satisfacen el contrato)
2. SSHConnectionAdapter implementa los 4 métodos del port
3. LocalConnectionAdapter implementa los 4 métodos del port
4. LocalConnectionAdapter.execute devuelve la tupla (rc, stdout, stderr) esperada
"""
import inspect

import pytest

from app.v1.servers.application.interfaces.connection import Connection
from app.v1.servers.infrastructure.adapters.local_connection import LocalConnectionAdapter
from app.v1.servers.infrastructure.adapters.ssh_connection import SSHConnectionAdapter

# ---------------------------------------------------------------------------
# Constantes con los métodos obligatorios del contrato
# ---------------------------------------------------------------------------

_CONTRACT_METHODS = ("execute", "upload_file", "file_exists", "close")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ssh_connection_adapter_satisfies_connection_contract() -> None:
    """SSHConnectionAdapter es subclase de Connection (satisface el port)."""
    assert issubclass(SSHConnectionAdapter, Connection)


def test_local_connection_adapter_satisfies_connection_contract() -> None:
    """LocalConnectionAdapter es subclase de Connection (satisface el port)."""
    assert issubclass(LocalConnectionAdapter, Connection)


@pytest.mark.parametrize("method_name", _CONTRACT_METHODS)
def test_ssh_connection_adapter_implements_all_contract_methods(method_name: str) -> None:
    """SSHConnectionAdapter implementa todos los métodos del port Connection."""
    assert hasattr(SSHConnectionAdapter, method_name), (
        f"SSHConnectionAdapter no implementa el método '{method_name}' del contrato"
    )
    method = getattr(SSHConnectionAdapter, method_name)
    assert callable(
        method), f"'{method_name}' no es callable en SSHConnectionAdapter"
    assert inspect.iscoroutinefunction(method), (
        f"'{method_name}' debe ser async en SSHConnectionAdapter"
    )


@pytest.mark.parametrize("method_name", _CONTRACT_METHODS)
def test_local_connection_adapter_implements_all_contract_methods(method_name: str) -> None:
    """LocalConnectionAdapter implementa todos los métodos del port Connection."""
    assert hasattr(LocalConnectionAdapter, method_name), (
        f"LocalConnectionAdapter no implementa el método '{method_name}' del contrato"
    )
    method = getattr(LocalConnectionAdapter, method_name)
    assert callable(
        method), f"'{method_name}' no es callable en LocalConnectionAdapter"
    assert inspect.iscoroutinefunction(method), (
        f"'{method_name}' debe ser async en LocalConnectionAdapter"
    )


@pytest.mark.asyncio
async def test_local_connection_adapter_execute_returns_contract_tuple() -> None:
    """LocalConnectionAdapter.execute devuelve (int, str, str) según el contrato."""
    adapter = LocalConnectionAdapter()
    rc, stdout, stderr = await adapter.execute("echo hello")
    assert isinstance(rc, int)
    assert isinstance(stdout, str)
    assert isinstance(stderr, str)
    assert rc == 0
    assert "hello" in stdout
