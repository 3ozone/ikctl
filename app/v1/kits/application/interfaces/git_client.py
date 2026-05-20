"""
Interface para el cliente Git.

Define el contrato que será implementado por GitPythonClient en infrastructure/adapters/.
"""
from abc import ABC, abstractmethod
from typing import Optional

from app.v1.servers.domain.entities.credential import Credential


class GitClient(ABC):
    """Contrato para operaciones de clonado y lectura de repositorios Git.

    El cliente realiza shallow clones (depth=1) para minimizar transferencia
    de datos (RNF-14). Soporta repositorios públicos y privados via credenciales
    de tipo git_https o git_ssh.

    Timeout máximo de 30s por operación (RNF-12). Nunca persiste credenciales
    en disco de forma permanente (RNF-09, RNF-15).
    """

    @abstractmethod
    async def clone_shallow(
        self,
        url: str,
        ref: str,
        dest_path: str,
        credential: Optional[Credential] = None,
    ) -> str:
        """
        Realiza un shallow clone (depth=1) del repositorio en dest_path.

        Soporta tres modos según credential:
        - None: repositorio público, sin autenticación
        - credential.type == 'git_https': usuario + PAT embebidos en la URL
        - credential.type == 'git_ssh': clave privada en archivo temporal

        El directorio dest_path debe ser limpiado por el llamador o por
        este método tras su uso (RNF-15).

        Args:
            url: URL del repositorio Git (https:// o git@)
            ref: Rama, tag o commit SHA a clonar
            dest_path: Ruta local donde clonar el repositorio
            credential: Credencial de tipo git_https o git_ssh, o None para público

        Returns:
            commit_sha: SHA del commit HEAD tras el clone

        Raises:
            InfrastructureException: Si el clone falla, timeout, credenciales
                inválidas o repositorio no accesible (RN-31)
        """

    @abstractmethod
    async def read_yaml_file(self, dest_path: str, relative_path: str) -> dict:
        """
        Lee y parsea un fichero YAML dentro del directorio clonado.

        El parsing YAML ocurre en infraestructura para evitar dependencias
        de terceros (PyYAML) en la capa de aplicación.

        Args:
            dest_path: Ruta local del repositorio clonado
            relative_path: Ruta relativa al fichero YAML dentro del repositorio

        Returns:
            Contenido del fichero parseado como dict

        Raises:
            InfrastructureException: Si el fichero no existe, no se puede leer
                o no es YAML válido
        """
