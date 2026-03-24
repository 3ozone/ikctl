# ADR-010: Entidad Credential Unificada con Tipos (SSH y Git)

**Estado:** ✅ Aceptado  
**Fecha:** 2026-03-22  
**Decisores:** Equipo ikctl  

## Contexto

ikctl necesita gestionar dos categorías de credenciales con campos similares pero semántica distinta:

1. **Credenciales SSH**: para conectarse a servidores remotos (`username` + `password` y/o `private_key`)
2. **Credenciales Git**: para clonar repositorios privados de GitHub (`username` + PAT via `password`, o `private_key` para SSH Git)

**Problema de diseño**: ¿Entidades separadas (`SSHCredential`, `GitCredential`) o una entidad unificada con `type`?

## Decisión

Una **única entidad `Credential`** con campo `type` discriminador. Los campos `username`, `password` y `private_key` tienen semántica distinta según el tipo, pero la estructura de datos es idéntica.

### Tipos soportados

| `type` | `username` | `password` | `private_key` | Caso de uso |
|---|---|---|---|---|
| `ssh` | Usuario del sistema (ej: `ubuntu`) | Password SSH (opcional) | Clave ed25519 (opcional) | Conectar a servidor remoto |
| `git_https` | Usuario GitHub (ej: `octocat`) | Personal Access Token | — | Clonar repo privado via HTTPS |
| `git_ssh` | — | — | Clave ed25519 | Clonar repo privado via SSH |

### Reglas de validación por tipo

```python
@dataclass(frozen=True)
class CredentialType(Enum):
    SSH = "ssh"
    GIT_HTTPS = "git_https"
    GIT_SSH = "git_ssh"

@dataclass
class Credential:
    id: str
    user_id: str
    name: str
    type: CredentialType
    username: str | None
    password: str | None      # AES-256 en reposo
    private_key: str | None   # AES-256 en reposo

    def __post_init__(self):
        match self.type:
            case CredentialType.SSH:
                if not self.username:
                    raise InvalidCredentialError("ssh requiere username")
                if not self.password and not self.private_key:
                    raise InvalidCredentialError("ssh requiere password o private_key")
            case CredentialType.GIT_HTTPS:
                if not self.username:
                    raise InvalidCredentialError("git_https requiere username")
                if not self.password:
                    raise InvalidCredentialError("git_https requiere password (PAT)")
            case CredentialType.GIT_SSH:
                if not self.private_key:
                    raise InvalidCredentialError("git_ssh requiere private_key")
```

### Schema de base de datos

```sql
CREATE TABLE credentials (
    id           VARCHAR(36) NOT NULL,
    user_id      VARCHAR(36) NOT NULL,
    name         VARCHAR(255) NOT NULL,
    type         ENUM('ssh', 'git_https', 'git_ssh') NOT NULL,
    username     VARCHAR(255),
    password     TEXT,         -- AES-256 cifrado, NULL si no aplica
    private_key  TEXT,         -- AES-256 cifrado, NULL si no aplica
    created_at   DATETIME NOT NULL,
    updated_at   DATETIME NOT NULL,
    PRIMARY KEY (id),
    KEY idx_user_id (user_id)
);
```

### Uso en cada módulo

- **Módulo servers** (`SSHConnectionAdapter`): usa credenciales de tipo `ssh`
- **Módulo kits** (`GitPythonRepository`): usa credenciales de tipo `git_https` o `git_ssh`

La validación de que el tipo de credencial es compatible con el recurso que la referencia se hace **en el caso de uso**, no en la entidad:

```python
# Use case: RegisterKit
if kit.git_credential_id:
    credential = await self._credential_repo.find_by_id(kit.git_credential_id)
    if credential.type not in (CredentialType.GIT_HTTPS, CredentialType.GIT_SSH):
        raise InvalidCredentialTypeError(
            f"Kit requiere credencial git_https o git_ssh, recibido: {credential.type}"
        )

# Use case: RegisterServer
if server.credential_id:
    credential = await self._credential_repo.find_by_id(server.credential_id)
    if credential.type != CredentialType.SSH:
        raise InvalidCredentialTypeError(
            f"Server requiere credencial ssh, recibido: {credential.type}"
        )
```

## Alternativas Consideradas

| Alternativa | Pros | Contras | Decisión |
|---|---|---|---|
| **Entidad unificada con `type`** | Un solo CRUD, una tabla, reutilización | Semántica diferente por tipo | ✅ **ELEGIDO** |
| **Entidades separadas (`SSHCredential`, `GitCredential`)** | Tipos explícitos, sin ambigüedad | Duplicación de código, dos CRUDs, dos tablas | ❌ Descartado |
| **Polimorfismo con herencia** | Tipos explícitos en código | SQLAlchemy herencia compleja, overkill para 3 tipos | ❌ Descartado |

## Consecuencias

### Positivas

✅ **Un solo CRUD** (`/api/v1/credentials`) para todos los tipos  
✅ **Una sola tabla** en MariaDB — sin JOINs cross-tabla  
✅ **Reutilización**: los módulos servers y kits comparten la misma entidad  
✅ **Extensible**: añadir `type: winrm` en v2 sin nuevas tablas  
✅ **Seguridad uniforme**: cifrado AES-256 centralizado para `password` y `private_key`  
✅ **Write-only consistente**: `password` y `private_key` nunca se devuelven en ninguna respuesta de API, independientemente del tipo  

### Negativas

⚠️ Semántica del campo `password` varía por tipo (password SSH vs Personal Access Token)  
⚠️ El frontend debe ajustar el formulario según el `type` seleccionado  

### Mitigación

El campo `name` libre permite al usuario dar un alias descriptivo (`"GitHub PAT - org/infra-kits"`) que clarifica el propósito sin depender del nombre del campo técnico.

## Referencias

- [GitHub Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [ADR-009: Git como Fuente de Kits](009-git-as-kit-source.md)
- [ADR-005: Idempotencia y Resiliencia](005-idempotency-resilience.md)
