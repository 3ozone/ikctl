# ADR-011: Estrategia de Cola de Tareas — BackgroundTasks (v1) → ARQ + Valkey (v2)

**Estado:** ✅ Aceptado  
**Fecha:** 2026-03-22  
**Decisores:** Equipo ikctl  

## Contexto

Las operaciones SSH en ikctl son **I/O bound y de larga duración** — una instalación puede tardar varios minutos. No pueden ejecutarse de forma síncrona en el ciclo request/response de FastAPI porque:

- El cliente HTTP haría timeout (30-60s por defecto)
- El proceso de la API quedaría bloqueado para otros requests
- No hay forma de consultar el estado o cancelar la operación

Se necesita un mecanismo para **despachar tareas en background** y permitir al cliente consultar el estado via polling.

**Opciones evaluadas:**

| Alternativa | Pros | Contras | Decisión |
|---|---|---|---|
| **FastAPI BackgroundTasks** | Sin dependencias extra, async nativo, simple | InMemory — se pierde si el proceso muere, no distribuible | ✅ v1 |
| **ARQ + Valkey** | Persistente, distribuible, retry automático, monitoreable | Requiere Valkey, más configuración | ✅ v2 |
| **Celery + Redis** | Maduro, amplio ecosistema | No async nativo, overhead de broker, worker separado | ❌ Descartado |
| **Dramatiq** | Más simple que Celery | No async nativo, menor adopción | ❌ Descartado |
| **Asyncio directo (fire & forget)** | Trivial | Sin persistencia, sin retry, sin visibilidad | ❌ Descartado |

## Decisión

### v1: FastAPI BackgroundTasks (InMemory)

Para el MVP, las operaciones SSH se despachan como `BackgroundTasks` de FastAPI. Son async nativas, sin overhead de broker y suficientes para un deployment de una sola instancia.

**Flujo v1:**

```
POST /operations
  → crea registro en DB (status: pending)
  → despacha background_tasks.add_task(execute_operation, operation_id)
  → devuelve 202 Accepted + { operation_id }

background task:
  → cambia status: in_progress
  → git clone + render + SFTP + SSH exec
  → cambia status: completed | failed

GET /operations/{id}   → cliente hace polling del estado
```

**Implementación v1:**

```python
# Port (application/interfaces/)
class TaskQueue(ABC):
    @abstractmethod
    async def enqueue(self, task_name: str, **kwargs) -> str:
        """Encola una tarea. Devuelve task_id."""
        ...

# Adaptador v1 (infrastructure/adapters/)
class FastAPITaskQueue(TaskQueue):
    def __init__(self, background_tasks: BackgroundTasks):
        self._bg = background_tasks

    async def enqueue(self, task_name: str, **kwargs) -> str:
        task_id = str(uuid4())
        self._bg.add_task(TASK_REGISTRY[task_name], task_id=task_id, **kwargs)
        return task_id

# Router
@router.post("/operations", status_code=202)
async def launch_operation(
    payload: LaunchOperationRequest,
    background_tasks: BackgroundTasks,
    use_case: LaunchOperation = Depends(get_launch_operation),
):
    task_queue = FastAPITaskQueue(background_tasks)
    result = await use_case.execute(payload, task_queue)
    return result  # { operation_id, status: "pending" }
```

**Limitaciones v1 aceptadas:**
- Si el proceso de la API muere, las operaciones `in_progress` quedan huérfanas — se marcan como `cancelled_unsafe` al reiniciar
- No distribuible: solo una instancia de la API puede ejecutar tareas
- Sin retry automático: el usuario debe relanzar manualmente si falla

### v2: ARQ + Valkey

Cuando se necesite escalar horizontalmente o mayor resiliencia, se migra a **ARQ** (async task queue sobre Valkey/Redis).

**Por qué ARQ sobre Celery:**
- ARQ es async nativo (asyncio) — Celery no lo es
- Menor overhead: no necesita un broker separado, usa Valkey directamente
- API simple: `await arq_redis.enqueue_job("execute_operation", operation_id=...)`
- Valkey ya está en la infraestructura (ADR-001)

**Adaptador v2:**

```python
# Adaptador v2 (infrastructure/adapters/)
class ARQTaskQueue(TaskQueue):
    def __init__(self, arq_redis: ArqRedis):
        self._arq = arq_redis

    async def enqueue(self, task_name: str, **kwargs) -> str:
        job = await self._arq.enqueue_job(task_name, **kwargs)
        return job.job_id
```

**El port `TaskQueue` ABC no cambia** — los use cases son idénticos en v1 y v2. Solo se intercambia el adaptador en `main.py`.

### Migración v1 → v2

El único cambio en la migración es en `main.py` (Composition Root):

```python
# v1
task_queue = FastAPITaskQueue(background_tasks)

# v2
arq_redis = await create_pool(RedisSettings.from_dsn(settings.VALKEY_URL))
task_queue = ARQTaskQueue(arq_redis)
```

Ningún use case ni entidad de dominio cambia.

## Operaciones que usan la cola de tareas

| Operación | Duración estimada | Timeout |
|---|---|---|
| `execute_operation` (kit en servidor) | 1-10 min | 10 min |
| `sync_kit` (git clone + validación) | 5-30s | 30s |
| `server_health_check` | < 5s | 35s |
| `execute_pipeline` (múltiples kits) | 1-60 min | 60 min |

`server_health_check` y `sync_kit` pueden ejecutarse síncronos en v1 dado su timeout corto, pero siguen el mismo patrón de registro en DB para consistencia.

## Consecuencias

### Positivas

✅ **v1 sin dependencias extra**: no hay Valkey ni worker separado para el MVP  
✅ **Port `TaskQueue`**: cambio de backend sin tocar use cases  
✅ **Async nativo end-to-end**: BackgroundTasks y ARQ son ambos async  
✅ **Valkey ya disponible**: la migración a v2 no añade nueva infraestructura (ADR-001)  
✅ **Operaciones trazables**: siempre se registra en DB antes de encolar  

### Negativas

⚠️ **v1 no es crash-safe**: operaciones `in_progress` quedan huérfanas si el proceso muere  
⚠️ **v1 no distribuible**: una sola instancia de API  
⚠️ **Polling en el cliente**: no hay push (SSE/WebSockets en v2)  

## Referencias

- [ARQ — Async Task Queue](https://arq-docs.helpmanual.io/)
- [FastAPI BackgroundTasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [ADR-001: Valkey como Cache Store](001-valkey-cache-store.md)
- [ADR-003: SSH Connection Pooling](003-ssh-connection-pooling.md)
