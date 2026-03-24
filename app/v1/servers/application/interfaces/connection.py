"""
Interface para la conexión SSH a servidores remotos.

Define el contrato que será implementado por los adaptadores concretos
(asyncssh, paramiko, etc.) en infrastructure/adapters/.
"""
from abc import ABC, abstractmethod


class Connection(ABC):
    """Contrato para ejecutar comandos y transferir archivos en servidores remotos."""

    @abstractmethod
    async def execute(self, command: str, sudo: bool = False, timeout: int = 30) -> tuple[int, str, str]:
        """
        Ejecuta un comando en el servidor remoto.

        Args:
            command: Comando a ejecutar
            sudo: Si True, ejecuta con sudo
            timeout: Tiempo máximo de espera en segundos (default 30)

        Returns:
            Tupla (return_code, stdout, stderr)

        Raises:
            ConnectionError: Si la conexión falla o se pierde
            TimeoutError: Si el comando supera el timeout
        """

    @abstractmethod
    async def upload_file(self, local_path: str, remote_path: str) -> None:
        """
        Transfiere un archivo local al servidor remoto vía SFTP.

        Args:
            local_path: Ruta absoluta del archivo local
            remote_path: Ruta destino en el servidor remoto

        Raises:
            ConnectionError: Si la transferencia falla
            FileNotFoundError: Si el archivo local no existe
        """

    @abstractmethod
    async def file_exists(self, remote_path: str) -> bool:
        """
        Comprueba si un archivo o directorio existe en el servidor remoto.

        Args:
            remote_path: Ruta a comprobar en el servidor remoto

        Returns:
            True si existe, False si no

        Raises:
            ConnectionError: Si la comprobación falla
        """

    @abstractmethod
    async def close(self) -> None:
        """
        Cierra la conexión SSH y libera los recursos del pool.

        Debe llamarse siempre al finalizar, preferiblemente en un bloque
        try/finally o usando la conexión como context manager.
        """
