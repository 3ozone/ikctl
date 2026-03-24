# ADR-009: Git como Fuente de Kits (GitOps)

**Estado:** ✅ Aceptado  
**Fecha:** 2026-03-22  
**Decisores:** Equipo ikctl  

## Contexto

ikctl necesita almacenar y distribuir los ficheros que componen un kit (scripts `.sh`, `.py`, templates `.j2` y manifiestos `ikctl.yaml`). Inicialmente se consideró MinIO como object storage, pero los usuarios de ikctl son perfiles técnicos (DevOps, sysadmins) que ya trabajan con Git para gestionar infraestructura.

**Requisitos clave:**

- Los kits deben poder versionarse con precisión (branch, tag, commit)
- El equipo debe poder colaborar en los kits (PR, review, historial)
- Los kits deben poder reutilizarse fácilmente entre proyectos
- La herramienta debe funcionar como ArgoCD o Flux: declarar el estado deseado en Git y sincronizar

**Alternativas evaluadas:**

| Alternativa | Pros | Contras | Decisión |
|---|---|---|---|
| **Git (GitOps)** | Versionado, colaboración, branching, rollback gratis | Requiere clonar en runtime | ✅ **ELEGIDO** |
| **MinIO / S3** | Upload directo, pre-signed URLs | Sin historial, sin colaboración, infraestructura extra | ❌ Descartado |
| **Filesystem local** | Sin infraestructura extra | No escala horizontalmente, sin versioning | ❌ Descartado |
| **MariaDB LONGBLOB** | Sin infraestructura extra | Lento para ficheros >1MB, backups pesados | ❌ Descartado |

## Decisión

Los kits se registran en ikctl apuntando a un **repositorio Git** (monorepo o repo individual). El API server descarga los ficheros en runtime mediante **shallow clone** (`depth=1`) al sincronizar o ejecutar una operación. Los ficheros **nunca se almacenan** en la API — solo los metadatos se persisten en MariaDB.

### Modelo de datos

```
Kit
├── repo_url        → https://github.com/org/monorepo
├── ref             → "main" | "v1.0.0"  (branch o tag)
├── path_in_repo    → "haproxy/"         (carpeta del kit en el monorepo)
├── git_credential_id → NULL (público) | credential_id (privado)
├── sync_status     → never_synced | synced | sync_error
└── last_commit_sha → SHA del último commit sincronizado
```

### Estructura monorepo recomendada

```
org/infra-kits/
├── haproxy/
│   ├── ikctl.yaml
│   ├── install-haproxy.sh
│   └── haproxy.cfg.j2
├── nginx/
│   ├── ikctl.yaml
│   └── install-nginx.sh
└── kubernetes/
    ├── ikctl.yaml
    └── install-k8s.sh
```

### Flujo de sincronización

```
POST /kits/{id}/sync
  → shallow clone depth=1 del repo en ref
  → leer ikctl.yaml en path_in_repo
  → validar manifest (files.uploads[], files.pipeline[], values{})
  → extraer metadatos (name, description, version, tags, values)
  → actualizar sync_status: synced, last_commit_sha, last_synced_at
  → si falla: sync_status: sync_error + sync_error_message
```

### Flujo de ejecución (runtime)

Cuando se lanza una operación con un kit ya sincronizado:

```
1. Shallow clone depth=1 del repo en last_commit_sha (pin exacto al commit)
2. Renderizar ficheros .j2 con Jinja2 + values
3. Calcular SHA-256 de cada fichero renderizado
4. Comparar contra server_kit_file_cache (ver ADR-005)
5. Transferir via SFTP solo ficheros nuevos o modificados
6. Ejecutar scripts según files.pipeline[]
```

### Repos privados

Se usa la entidad `Credential` del módulo servers con `type: git_https` o `git_ssh`:

- `git_https`: `username` = usuario GitHub, `password` = Personal Access Token (PAT). Cifrado AES-256
- `git_ssh`: `private_key` = clave ed25519. Cifrada AES-256

El GitHub OAuth login **no** se usa para acceder a repos privados (v1). Esta integración queda como Feature Futura (FF-06 en kits/requirements.md).

### Proveedores soportados

- **v1**: GitHub únicamente
- **v2**: GitLab, Gitea (self-hosted) — misma abstracción, nuevo adaptador

## Consecuencias

### Positivas

✅ **Versionado gratuito**: tags, branches, historial de commits  
✅ **Colaboración**: PRs, code review, CI en el mismo repo  
✅ **Rollback trivial**: cambiar `ref` a un tag anterior + sync  
✅ **Sin infraestructura extra**: no hay MinIO ni object storage  
✅ **Familiar para el usuario**: mismo flujo que ArgoCD, Flux, Helm  
✅ **SHA-256 cache sigue válido**: la fuente de los ficheros cambia, el mecanismo de cache no  
✅ **Port `GitRepository` ABC**: intercambiable vía adaptadores (GitHub → GitLab en v2 sin cambiar use cases)  

### Negativas

⚠️ **Dependencia de red en runtime**: si GitHub no está disponible, no se puede sincronizar ni ejecutar kits no cacheados  
⚠️ **Latencia en sync**: shallow clone añade ~1-3s dependiendo del tamaño del repo  
⚠️ **Repos privados requieren credencial manual**: el usuario debe crear un PAT y registrarlo  

### Mitigación de riesgos

- **GitHub no disponible**: los ficheros ya transferidos al servidor remoto siguen en `/tmp/ikctl/kits/{kit_id}/` y el `server_kit_file_cache` permite re-ejecutar sin nuevo clone si no hay cambios
- **Latencia sync**: shallow clone `depth=1` minimiza datos descargados — solo el último commit

## Implementación

```python
# Port (application/interfaces/)
class GitRepository(ABC):
    @abstractmethod
    async def clone_shallow(
        self,
        repo_url: str,
        ref: str,
        dest_path: str,
        credential: Credential | None = None,
        timeout: float = 30.0,
    ) -> str:
        """Clona el repo en dest_path. Devuelve el commit SHA."""
        ...

# Adaptador (infrastructure/adapters/)
class GitPythonRepository(GitRepository):
    """Implementación con gitpython para v1."""
    async def clone_shallow(self, ...):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._do_clone,
            repo_url, ref, dest_path, credential
        )
```

## Referencias

- [ArgoCD — GitOps](https://argo-cd.readthedocs.io/en/stable/user-guide/gitops/)
- [Flux — GitOps Toolkit](https://fluxcd.io/flux/)
- [gitpython](https://gitpython.readthedocs.io/)
