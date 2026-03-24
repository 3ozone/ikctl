# ADR-014: Soft Delete para Kits

**Estado:** ✅ Aceptado  
**Fecha:** 2026-03-22  
**Decisores:** Equipo ikctl  

## Contexto

Cuando un usuario elimina un kit, existe una tensión entre dos necesidades:

1. **UX**: el kit desaparece de los listados — el usuario no lo ve más
2. **Integridad del historial**: las operaciones y pipelines pasados referencian el `kit_id`. Si el kit se borra físicamente, esos registros históricos quedan huérfanos y sin contexto

Además, con el modelo GitOps (ADR-009), los ficheros del kit **no están almacenados** en la API — viven en el repositorio Git. No hay nada que limpiar físicamente al eliminar un kit, a diferencia de un modelo con object storage.

## Decisión

Implementar **soft delete** para kits mediante el campo `is_deleted: bool` en la tabla `kits`.

Un kit eliminado:
- Se marca `is_deleted = true` en MariaDB
- Desaparece de todos los listados y búsquedas (`WHERE is_deleted = false`)
- No puede usarse en nuevas operaciones ni pipelines
- No puede modificarse
- Sus metadatos se conservan indefinidamente para mantener la integridad del historial
- No hay ficheros que eliminar (modelo GitOps)

### Implementación en la entidad

```python
@dataclass
class Kit:
    id: str
    user_id: str
    repo_url: str
    ref: str
    path_in_repo: str
    # ... resto de campos
    is_deleted: bool = False

    def delete(self) -> None:
        """Marca el kit como eliminado. Estado terminal."""
        if self.is_deleted:
            raise KitAlreadyDeletedError(f"Kit {self.id} ya está eliminado")
        self.is_deleted = True

    def ensure_not_deleted(self) -> None:
        """Lanza excepción si el kit está eliminado. Usar en use cases."""
        if self.is_deleted:
            raise KitDeletedError(f"Kit {self.id} está eliminado y no puede usarse")
```

### Implementación en repositorio

```python
class SQLAlchemyKitRepository(KitRepository):
    async def find_all_by_user(self, user_id: str, ...) -> list[Kit]:
        # Filtro automático — never returns deleted kits
        query = select(KitModel).where(
            KitModel.user_id == user_id,
            KitModel.is_deleted == False,
        )
        ...

    async def find_by_id(self, kit_id: str) -> Kit | None:
        # Devuelve el kit aunque esté deleted — los use cases deciden si es válido
        query = select(KitModel).where(KitModel.id == kit_id)
        ...
```

`find_all_by_user` filtra automáticamente los kits eliminados. `find_by_id` devuelve el kit incluso si está eliminado — la validación de si se puede usar se hace en el use case mediante `kit.ensure_not_deleted()`.

### Use cases afectados

```python
# DeleteKit — use case
class DeleteKit:
    async def execute(self, kit_id: str, user_id: str) -> None:
        kit = await self._repo.find_by_id(kit_id)
        if not kit:
            raise KitNotFoundError(kit_id)
        if kit.user_id != user_id:
            raise UnauthorizedError()
        kit.delete()
        await self._repo.save(kit)

# LaunchOperation — validación antes de encolar
class LaunchOperation:
    async def execute(self, payload: LaunchOperationRequest, ...) -> OperationResult:
        kit = await self._kit_repo.find_by_id(payload.kit_id)
        if not kit:
            raise KitNotFoundError(payload.kit_id)
        kit.ensure_not_deleted()              # ← bloquea kits eliminados
        kit.ensure_synced()                   # ← bloquea kits sin sincronizar
        ...
```

### Qué se conserva vs qué se limpia

| Dato | Al eliminar kit | Justificación |
|---|---|---|
| Metadatos del kit (`name`, `repo_url`, etc.) | ✅ Conservar | Integridad historial de operaciones |
| `server_kit_file_cache` para este kit | 🗑️ Limpiar | Ya no tiene utilidad, libera espacio |
| Registros de operaciones pasadas (`kit_id`) | ✅ Conservar | Auditoría — el `kit_id` sigue resolvible |
| Ficheros en servidor remoto (`/tmp/ikctl/kits/{kit_id}/`) | 🗑️ Limpiar (best effort) | No crítico — son en `/tmp/`, se limpian solos en reinicio |

La limpieza de `server_kit_file_cache` se hace en el use case `DeleteKit` de forma síncrona. La limpieza de ficheros en servidores remotos es **best effort** via background task (si falla, no bloquea el delete).

## Alternativas Consideradas

| Alternativa | Pros | Contras | Decisión |
|---|---|---|---|
| **Soft delete con `is_deleted`** | Integridad historial, simple | Tabla crece con el tiempo | ✅ **ELEGIDO** |
| **Hard delete** | Tabla limpia | Rompe integridad referencial del historial de operaciones | ❌ Descartado |
| **Archivado en tabla separada (`kits_deleted`)** | Tabla principal limpia | Complejidad innecesaria, dos tablas para una entidad | ❌ Descartado |
| **Soft delete con TTL (purge automático tras N días)** | Equilibrio espacio/integridad | Complejo, riesgo de perder contexto de operaciones antiguas | ❌ v2 si necesario |

## Consecuencias

### Positivas

✅ **Integridad referencial del historial**: operaciones pasadas siempre tienen contexto del kit  
✅ **Simple**: un campo booleano, sin tablas extra  
✅ **Reversible en emergencias**: un admin puede restaurar el kit a mano directamente en DB si es necesario (no expuesto en API v1)  
✅ **Sin ficheros que limpiar**: el modelo GitOps elimina el problema de orphaned files en object storage  

### Negativas

⚠️ **La tabla `kits` crece indefinidamente** — mitigable con índice en `is_deleted` y purge manual periódico si necesario  
⚠️ **Todas las queries de listado deben filtrar `is_deleted = false`** — encapsulado en el repositorio para evitar olvidos  

## Referencias

- [ADR-009: Git como Fuente de Kits](009-git-as-kit-source.md)
- [ADR-005: Idempotencia y Resiliencia](005-idempotency-resilience.md)
- [ADR-013: Caché de Ficheros por SHA-256](013-sftp-sha256-file-cache.md)
