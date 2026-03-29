"""SSHConnectionAdapter — Implementación asyncssh del port Connection.

Mantiene una única conexión SSH por instancia (connection pooling simple).
La conexión se abre lazy en el primer uso y se reutiliza en las llamadas
sucesivas. Llamar a close() cuando ya no se necesite la conexión.

Timeouts configurables por operación (RNF-03):
- Conexión: connect_timeout (default 30s)
- Ejecución de comando: timeout por llamada a execute() (default 30s)
"""
import asyncssh

from app.v1.servers.application.interfaces.connection import Connection
from app.v1.servers.infrastructure.exceptions import SSHConnectionError


class SSHConnectionAdapter(Connection):
    """Adaptador SSH basado en asyncssh.

    Reutiliza la conexión abierta (connection pool de 1 conexión por instancia).
    """

    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str = "root",
        private_key: str | None = None,
        password: str | None = None,
        connect_timeout: int = 30,
    ) -> None:
        """Inicializa el adaptador SSH.

        Args:
            host: Hostname o IP del servidor remoto.
            port: Puerto SSH (default 22).
            username: Usuario para autenticación.
            private_key: Clave privada SSH en formato PEM (opcional).
            password: Contraseña o PAT (opcional, alternativa a private_key).
            connect_timeout: Timeout de conexión en segundos (default 30).
        """
        self._host = host
        self._port = port
        self._username = username
        self._private_key = private_key
        self._password = password
        self._connect_timeout = connect_timeout
        self._conn: asyncssh.SSHClientConnection | None = None

    async def _get_connection(self) -> asyncssh.SSHClientConnection:
        """Devuelve la conexión activa, abriéndola si no existe todavía.

        Raises:
            SSHConnectionError: Si no se puede establecer la conexión.
        """
        if self._conn is not None:
            return self._conn

        try:
            connect_kwargs: dict = {
                "host": self._host,
                "port": self._port,
                "username": self._username,
                "connect_timeout": self._connect_timeout,
                # No verificar host keys en v1 (ver ADR-003)
                "known_hosts": None,
            }

            if self._private_key is not None:
                connect_kwargs["client_keys"] = [self._private_key]
            if self._password is not None:
                connect_kwargs["password"] = self._password

            self._conn = await asyncssh.connect(**connect_kwargs)
            return self._conn

        except Exception as exc:
            raise SSHConnectionError(
                f"No se pudo conectar a {self._host}:{self._port} — {exc}"
            ) from exc

    async def execute(
        self, command: str, sudo: bool = False, timeout: int = 30
    ) -> tuple[int, str, str]:
        """Ejecuta un comando en el servidor remoto.

        Args:
            command: Comando a ejecutar.
            sudo: Si True, antepone 'sudo' al comando.
            timeout: Timeout de ejecución en segundos (default 30).

        Returns:
            Tupla (return_code, stdout, stderr).

        Raises:
            SSHConnectionError: Si la conexión falla o se pierde.
        """
        try:
            conn = await self._get_connection()
            full_command = f"sudo {command}" if sudo else command
            result = await conn.run(full_command, timeout=timeout)
            rc = result.returncode if result.returncode is not None else -1
            stdout = result.stdout if isinstance(
                result.stdout, str) else bytes(result.stdout or b"").decode()
            stderr = result.stderr if isinstance(
                result.stderr, str) else bytes(result.stderr or b"").decode()
            return rc, stdout, stderr
        except SSHConnectionError:
            raise
        except Exception as exc:
            raise SSHConnectionError(
                f"Error ejecutando comando en {self._host}: {exc}"
            ) from exc

    async def upload_file(self, local_path: str, remote_path: str) -> None:
        """Transfiere un archivo local al servidor remoto vía SFTP.

        Args:
            local_path: Ruta absoluta del archivo local.
            remote_path: Ruta destino en el servidor remoto.

        Raises:
            SSHConnectionError: Si la transferencia falla.
        """
        try:
            conn = await self._get_connection()
            sftp = await conn.start_sftp_client()
            async with sftp:
                await sftp.put(local_path, remote_path)
        except SSHConnectionError:
            raise
        except Exception as exc:
            raise SSHConnectionError(
                f"Error subiendo archivo a {self._host}: {exc}"
            ) from exc

    async def file_exists(self, remote_path: str) -> bool:
        """Comprueba si un archivo o directorio existe en el servidor remoto.

        Args:
            remote_path: Ruta a comprobar en el servidor remoto.

        Returns:
            True si existe, False si no.

        Raises:
            SSHConnectionError: Si la comprobación falla.
        """
        try:
            rc, _, _ = await self.execute(f"test -e {remote_path}")
            return rc == 0
        except SSHConnectionError:
            raise

    async def close(self) -> None:
        """Cierra la conexión SSH y libera los recursos."""
        if self._conn is not None:
            self._conn.close()
            await self._conn.wait_closed()
            self._conn = None
