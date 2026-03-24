# ADR-013: Caché de Ficheros por SHA-256 en Transferencia SFTP

**Estado:** ✅ Aceptado  
**Fecha:** 2026-03-22  
**Decisores:** Equipo ikctl  

## Contexto

Cada vez que se ejecuta una operación con un kit, ikctl necesita transferir los ficheros del kit (scripts, templates renderizados) al servidor remoto antes de ejecutarlos. Sin optimización, cada ejecución transferiría todos los ficheros del kit aunque no hayan cambiado.

**Problema**: En kits con muchos ficheros o ficheros pesados, re-transferir innecesariamente:

- Aumenta la latencia de la operación en segundos o minutos
- Genera tráfico de red redundante hacia los servidores
- Incrementa el tiempo hasta el primer comando ejecutado

**Contexto adicional**: Los ficheros `.j2` se renderizan con Jinja2 antes de transferirse — el mismo fichero de template puede producir contenidos distintos según los `values` usados. El hash debe calcularse **después del rendering**, no sobre el template original.

## Decisión

Implementar una **caché diferencial de ficheros por SHA-256** en la tabla `server_kit_file_cache`. Antes de cada transferencia, se compara el hash del contenido renderizado contra el último hash conocido para ese fichero en ese servidor. Solo se transfieren los ficheros nuevos o modificados.

### Schema de base de datos

```sql
CREATE TABLE server_kit_file_cache (
    server_id       VARCHAR(36)  NOT NULL,
    kit_id          VARCHAR(36)  NOT NULL,
    filename        VARCHAR(512) NOT NULL,
    content_hash    CHAR(64)     NOT NULL,  -- SHA-256 hex del contenido post-Jinja2
    uploaded_at     DATETIME     NOT NULL,
    PRIMARY KEY (server_id, kit_id, filename)
);
```

### Algoritmo de transferencia diferencial

```
Para cada operación con un kit en un servidor:

1. Git shallow clone del kit en commit pinado (last_commit_sha)
2. Para cada fichero en files.uploads[]:
   a. Si es .j2: renderizar con Jinja2 + values → contenido_final
   b. Si no: leer contenido tal cual → contenido_final
   c. Calcular SHA-256(contenido_final) → hash_actual

3. Consultar server_kit_file_cache para (server_id, kit_id, filename)
   → hash_previo = resultado de la consulta (None si no existe)

4. Si hash_actual == hash_previo:
   → SKIP — fichero no ha cambiado, no transferir
   Si hash_actual != hash_previo (o no existe):
   → UPLOAD — transferir via SFTP/copia local
   → UPDATE server_kit_file_cache SET content_hash=hash_actual, uploaded_at=NOW()

5. Ejecutar scripts según files.pipeline[]
```

### Auto-repair: invalidación de caché

Si los ficheros ya no están en el servidor (detección previa a ejecución), la caché para ese `(server_id, kit_id)` se invalida completamente y se hace re-transfer de todos los ficheros:

```python
async def verify_and_repair_cache(
    server_id: str,
    kit_id: str,
    connection: Connection,
    cache_repo: FileCache Repository,
) -> None:
    cached_files = await cache_repo.find_by_server_and_kit(server_id, kit_id)
    for cached in cached_files:
        if not await connection.file_exists(cached.remote_path):
            # Fichero desapareció — invalidar toda la caché del kit en este servidor
            await cache_repo.delete_by_server_and_kit(server_id, kit_id)
            return  # Re-transfer completo en el siguiente paso
```

### Implementación en el use case de ejecución

```python
class ExecuteOperation:
    async def execute(self, operation_id: str, ...) -> OperationResult:
        # 1. Obtener kit y servidor
        kit = await self._kit_repo.find_by_id(operation.kit_id)
        server = await self._server_repo.find_by_id(operation.server_id)
        connection = self._connection_factory.get(server)

        # 2. Clone + render
        kit_files = await self._git_repo.clone_shallow(kit.repo_url, kit.last_commit_sha)
        rendered = await self._renderer.render_all(kit_files, operation.values)

        # 3. Auto-repair cache
        await self._file_cache.verify_and_repair(server.id, kit.id, connection)

        # 4. Transferencia diferencial
        for filename, content in rendered.items():
            current_hash = sha256(content)
            cached = await self._file_cache.find(server.id, kit.id, filename)

            if cached and cached.content_hash == current_hash:
                continue  # Skip

            remote_path = f"/tmp/ikctl/kits/{kit.id}/{filename}"
            await connection.upload_file(content, remote_path)
            await self._file_cache.upsert(server.id, kit.id, filename, current_hash)

        # 5. Ejecutar pipeline
        for script in kit.manifest.pipeline:
            result = await connection.execute(
                f"bash /tmp/ikctl/kits/{kit.id}/{script}",
                timeout=600,
            )
            ...
```

### Directorio de trabajo en el servidor remoto

```
/tmp/ikctl/kits/{kit_id}/
├── install-haproxy.sh
├── haproxy.cfg          # resultado del render de haproxy.cfg.j2
└── check-status.sh
```

- `/tmp/` se usa para que los ficheros no persistan entre reinicios del servidor remoto
- Si los ficheros desaparecen (reinicio), el auto-repair los re-transfiere automáticamente
- La ruta es predecible y constante para que los scripts puedan referenciarse entre sí

## Alternativas Consideradas

| Alternativa | Pros | Contras | Decisión |
|---|---|---|---|
| **SHA-256 post-render (elegido)** | Detecta cambios reales incluyendo cambios en values | Hash calculado en runtime | ✅ **ELEGIDO** |
| **Siempre re-transferir** | Simple, sin estado | Lento para kits grandes, tráfico innecesario | ❌ Descartado |
| **Hash del fichero fuente (pre-render)** | Más simple de calcular | No detecta cambios por values distintos | ❌ Incompleto |
| **Timestamp last_modified del fichero en Git** | Sin hash | No refleja cambios de values ni versión del template | ❌ Descartado |
| **rsync** | Diferencial nativo | Requiere rsync en el servidor remoto | ❌ Dependencia externa |

## Consecuencias

### Positivas

✅ **Latencia reducida**: segunda ejecución del mismo kit es significativamente más rápida  
✅ **Tráfico de red mínimo**: solo se envían diferencias  
✅ **Auto-repair**: si el servidor remoto pierde los ficheros, se recuperan automáticamente  
✅ **Correctness**: el hash es del contenido post-render — cambiar `values` fuerza re-transfer  
✅ **Compatible con `LocalConnectionAdapter`**: mismo mecanismo, `upload_file` hace copia local  
✅ **Idempotente**: misma operación con mismos values y mismo commit → cero transferencias  

### Negativas

⚠️ **Tabla adicional** en `ikctl_operations` (o `ikctl_kits`): `server_kit_file_cache`  
⚠️ **Overhead de hashing**: calcular SHA-256 de todos los ficheros antes de cada operación (~ms para ficheros típicos de <1MB)  
⚠️ **Estado distribuido**: la caché en DB puede desincronizarse del estado real del servidor — mitigado por auto-repair  

## Referencias

- [ADR-005: Idempotencia y Resiliencia](005-idempotency-resilience.md)
- [ADR-009: Git como Fuente de Kits](009-git-as-kit-source.md)
- [ADR-012: LocalConnectionAdapter](012-local-connection-adapter.md)
- [Python hashlib — SHA-256](https://docs.python.org/3/library/hashlib.html)
