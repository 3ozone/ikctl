"""GitPythonClient — Implementación del GitClient usando subprocess async y PyYAML.

Realiza shallow clones (depth=1) invocando el CLI de git mediante
asyncio.create_subprocess_exec. Soporta repositorios públicos y privados
via credenciales git_https (user+PAT en URL) y git_ssh (clave privada temporal).

Timeout máximo de 30s por operación (RNF-12). Las claves privadas SSH se
escriben en un archivo temporal que se elimina siempre en el bloque finally
(RNF-15: nunca dejar secretos en disco de forma permanente).
"""
import asyncio
import os
import tempfile
from pathlib import Path
from typing import Optional

import yaml

from app.v1.kits.application.interfaces.git_client import GitClient
from app.v1.kits.infrastructure.exceptions import GitClientError
from app.v1.servers.domain.entities.credential import Credential

_CLONE_TIMEOUT = 30  # segundos (RNF-12)


class GitPythonClient(GitClient):
    """Implementación del GitClient usando subprocess async y PyYAML.

    No mantiene estado interno — puede usarse como singleton en el
    Composition Root (RNF-06).
    """

    # ------------------------------------------------------------------
    # Puerto — clone
    # ------------------------------------------------------------------

    async def clone_shallow(
        self,
        url: str,
        ref: str,
        dest_path: str,
        credential: Optional[Credential] = None,
    ) -> str:
        """Realiza un shallow clone (depth=1) del repositorio en dest_path.

        Args:
            url: URL del repositorio Git (https:// o git@)
            ref: Rama, tag o commit SHA a clonar
            dest_path: Ruta local donde clonar el repositorio
            credential: Credencial de tipo git_https/git_ssh, o None para público

        Returns:
            SHA del commit HEAD tras el clone

        Raises:
            GitClientError: Si el clone falla, hay timeout o credenciales inválidas
        """
        clone_url = self._build_clone_url(url, credential)
        env = {**os.environ}
        key_path: Optional[str] = None

        try:
            if credential is not None and credential.type.value == "git_ssh":
                key_path = self._write_ssh_key(credential.private_key or "")
                env["GIT_SSH_COMMAND"] = (
                    f"ssh -i {key_path} -o StrictHostKeyChecking=no -o BatchMode=yes"
                )

            cmd = [
                "git", "clone",
                "--depth", "1",
                "--branch", ref,
                "--", clone_url,
                dest_path,
            ]

            try:
                async with asyncio.timeout(_CLONE_TIMEOUT):
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env=env,
                    )
                    stdout, stderr = await proc.communicate()
            except TimeoutError as exc:
                raise GitClientError(
                    f"Git clone timed out after {_CLONE_TIMEOUT}s: {url}"
                ) from exc

            if proc.returncode != 0:
                raise GitClientError(
                    f"Git clone failed (exit {proc.returncode}): "
                    f"{stderr.decode(errors='replace').strip()}"
                )

            return await self._get_head_sha(dest_path)

        finally:
            if key_path is not None:
                try:
                    os.unlink(key_path)
                except OSError:
                    pass

    # ------------------------------------------------------------------
    # Puerto — lectura YAML
    # ------------------------------------------------------------------

    async def read_yaml_file(self, dest_path: str, relative_path: str) -> dict:
        """Lee y parsea un fichero YAML dentro del directorio clonado.

        Args:
            dest_path: Ruta local del repositorio clonado
            relative_path: Ruta relativa al fichero YAML dentro del repositorio

        Returns:
            Contenido del fichero parseado como dict (vacío si el YAML está vacío)

        Raises:
            GitClientError: Si el fichero no existe, no se puede leer o no es YAML válido
        """
        file_path = Path(dest_path) / relative_path

        if not file_path.exists():
            raise GitClientError(
                f"YAML file not found in repository: {relative_path}"
            )

        try:
            content = file_path.read_text(encoding="utf-8")
            parsed = yaml.safe_load(content)
            return parsed if isinstance(parsed, dict) else {}
        except yaml.YAMLError as exc:
            raise GitClientError(
                f"Invalid YAML in file {relative_path}: {exc}"
            ) from exc
        except OSError as exc:
            raise GitClientError(
                f"Cannot read file {relative_path}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _build_clone_url(self, url: str, credential: Optional[Credential]) -> str:
        """Construye la URL de clone con credenciales embebidas (git_https)."""
        if credential is None or credential.type.value != "git_https":
            return url

        username = credential.username or ""
        password = credential.password or ""

        if url.startswith("https://"):
            return url.replace(
                "https://",
                f"https://{username}:{password}@",
                1,
            )

        return url

    def _write_ssh_key(self, private_key: str) -> str:
        """Escribe la clave privada en un archivo temporal con permisos 600.

        Returns:
            Ruta del archivo temporal creado (debe borrarse en el finally del caller)
        """
        fd, path = tempfile.mkstemp(suffix=".pem")
        try:
            os.write(fd, private_key.encode())
        finally:
            os.close(fd)
        os.chmod(path, 0o600)
        return path

    async def _get_head_sha(self, dest_path: str) -> str:
        """Obtiene el SHA del commit HEAD del repositorio clonado."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "-C", dest_path, "rev-parse", "HEAD",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise GitClientError(
                    f"Cannot get HEAD SHA: {stderr.decode(errors='replace').strip()}"
                )
            return stdout.decode().strip()
        except GitClientError:
            raise
        except Exception as exc:
            raise GitClientError(f"Error getting HEAD SHA: {exc}") from exc
