# ADR-012: LocalConnectionAdapter para Ejecución Local

**Estado:** ✅ Aceptado  
**Fecha:** 2026-03-22  
**Decisores:** Equipo ikctl  

## Contexto

ikctl necesita soportar ejecución de kits en la **propia máquina donde corre la API** — no solo en servidores remotos via SSH. Casos de uso:

- Instalar dependencias en el servidor donde vive ikctl
- Pruebas locales de kits antes de desplegarlos en servidores remotos
- Entornos donde la máquina local es también el servidor target

**Problema de diseño**: Si el sistema tiene dos rutas de ejecución distintas (SSH y local), los manifiestos `ikctl.yaml` necesitarían saber en qué tipo de servidor se van a ejecutar, rompiendo la abstracción.

## Decisión

Implementar un **port `Connection` único** con dos adaptadores intercambiables:

- `SSHConnectionAdapter`: ejecución remota via asyncssh (ver ADR-003)
- `LocalConnectionAdapter`: ejecución local via `asyncio.subprocess`

El manifest `ikctl.yaml` y los use cases de operaciones **no saben** si están ejecutando local o remoto — el sistema selecciona el adaptador correcto en función del `type` del servidor registrado.

### Port `Connection`

```python
# application/interfaces/connection.py
class Connection(ABC):
    @abstractmethod
    async def execute(
        self,
        command: str,
        timeout: float = 300.0,
    ) -> CommandResult:
        """Ejecuta un comando. Devuelve stdout, stderr y exit_code."""
        ...

    @abstractmethod
    async def upload_file(
        self,
        local_path: str,
        remote_path: str,
    ) -> None:
        """Transfiere un fichero al destino."""
        ...

    @abstractmethod
    async def file_exists(self, path: str) -> bool:
        """Comprueba si un fichero existe en el destino."""
        ...

@dataclass(frozen=True)
class CommandResult:
    stdout: str
    stderr: str
    exit_code: int

    @property
    def success(self) -> bool:
        return self.exit_code == 0
```

### SSHConnectionAdapter

```python
# infrastructure/adapters/ssh_connection_adapter.py
class SSHConnectionAdapter(Connection):
    """Ejecución remota via asyncssh con connection pooling (ADR-003)."""

    async def execute(self, command: str, timeout: float = 300.0) -> CommandResult:
        async with self._pool.get_connection() as conn:
            result = await conn.run(command, timeout=timeout)
            return CommandResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.exit_status,
            )

    async def upload_file(self, local_path: str, remote_path: str) -> None:
        async with self._pool.get_connection() as conn:
            async with conn.start_sftp_client() as sftp:
                await sftp.put(local_path, remote_path)

    async def file_exists(self, path: str) -> bool:
        async with self._pool.get_connection() as conn:
            result = await conn.run(f"test -f {path}", check=False)
            return result.exit_status == 0
```

### LocalConnectionAdapter

```python
# infrastructure/adapters/local_connection_adapter.py
class LocalConnectionAdapter(Connection):
    """Ejecución local via asyncio.subprocess. Solo para servidor tipo local."""

    async def execute(self, command: str, timeout: float = 300.0) -> CommandResult:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            raise OperationTimeoutError(f"Comando excedió timeout de {timeout}s")

        return CommandResult(
            stdout=stdout.decode(),
            stderr=stderr.decode(),
            exit_code=process.returncode,
        )

    async def upload_file(self, local_path: str, remote_path: str) -> None:
        """En local, copia el fichero directamente al path destino."""
        await asyncio.to_thread(shutil.copy2, local_path, remote_path)

    async def file_exists(self, path: str) -> bool:
        return await asyncio.to_thread(os.path.isfile, path)
```

### Selección del adaptador (Composition Root)

```python
# main.py — ConnectionFactory
def get_connection(server: Server, credential: Credential | None) -> Connection:
    match server.type:
        case ServerType.REMOTE:
            pool = ssh_pool_manager.get_pool(server.id, server.host, server.port)
            return SSHConnectionAdapter(pool=pool, credential=credential)
        case ServerType.LOCAL:
            return LocalConnectionAdapter()
```

### Restricciones de seguridad del servidor `local`

- **Solo rol `admin`** puede registrar y usar un servidor `local` (RF-34, RNF-16)
- Los comandos se ejecutan con el **usuario del proceso de la API** — nunca se eleva a `root`
- El flag `sudo: true` en el manifest se **ignora** para servidor `local` y genera un `WARNING` en logs
- El servidor `local` **no puede añadirse a grupos** ni usarse en pipelines (RNF-16)
- Solo puede existir **un servidor `local` por usuario** (RN-07)

## Alternativas Consideradas

| Alternativa | Pros | Contras | Decisión |
|---|---|---|---|
| **Port `Connection` único con dos adaptadores** | Transparente para kits y use cases | Requiere factory en Composition Root | ✅ **ELEGIDO** |
| **Endpoint separado `/local/execute`** | Simple | Duplica lógica, kits necesitarían saber el tipo | ❌ Descartado |
| **subprocess directo en use case** | Trivial | Viola Clean Architecture, no testeable, no intercambiable | ❌ Descartado |
| **SSH a localhost** | Reutiliza SSHConnectionAdapter | Requiere SSH server en la máquina, inseguro | ❌ Descartado |

## Consecuencias

### Positivas

✅ **Transparencia total**: manifiestos `ikctl.yaml` son idénticos para local y remoto  
✅ **Testeabilidad**: `LocalConnectionAdapter` es fácil de mockear en tests unitarios  
✅ **Extensible**: añadir `WinRMConnectionAdapter` en v2 sin cambiar use cases  
✅ **Sin dependencias extra**: `asyncio.subprocess` es stdlib  
✅ **Seguridad bien delimitada**: restricciones en entidad y use case, no ad-hoc  

### Negativas

⚠️ Los ficheros en servidor `local` no se transfieren via SFTP — `upload_file` hace copia local. El `server_kit_file_cache` sigue siendo válido (SHA-256 del contenido no cambia)  
⚠️ `asyncio.subprocess` no tiene el mismo aislamiento que SSH — un script mal escrito puede afectar el proceso de la API  

## Referencias

- [Python asyncio.subprocess](https://docs.python.org/3/library/asyncio-subprocess.html)
- [ADR-003: SSH Connection Pooling](003-ssh-connection-pooling.md)
- [ADR-005: Idempotencia y Resiliencia](005-idempotency-resilience.md)
