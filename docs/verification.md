# Verificación — Cómo demostrar que el trabajo funciona

> Regla de oro: **el agente no dice "funciona", lo demuestra**.
> Toda feature termina con evidencia ejecutable, no con afirmaciones.

## Niveles de verificación

### Nivel 1 — Tests unitarios (obligatorio)

Toda función pública en `app/` tiene al menos un test en `tests/` que:

1. Cubre el camino feliz.
2. Cubre al menos un camino de error si la función puede fallar.

Los tests replican la estructura del módulo:

```
tests/v1/{module}/
├── test_domain/             ← Entidades, VOs, excepciones, eventos
├── test_use_cases/          ← Commands y queries (con mocks)
├── test_infrastructure/    ← Repositories (con SQLite in-memory)
└── test_presentation/      ← Endpoints HTTP (con httpx.AsyncClient)
```

Comando:

```bash
pytest tests/ -v
```

### Nivel 2 — Tests de integración HTTP (obligatorio para endpoints)

Las features que añaden o modifican endpoints se verifican con
`httpx.AsyncClient` contra la app FastAPI real, con dependencias
overrideadas por fakes:

```python
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.v1.servers.infrastructure.presentation.deps import get_register_server

async def test_create_server_returns_201():
    app.dependency_overrides[get_register_server] = lambda: FakeRegisterServerOk()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/servers", json={...}, headers=auth_headers)
    assert response.status_code == 201
    app.dependency_overrides.clear()
```

### Nivel 3 — Tests de infraestructura con DB real (obligatorio para repositorios)

Los repositorios se testean con SQLite in-memory para aislar de MariaDB:

```python
@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine)() as session:
        yield session
    await engine.dispose()
```

### Nivel 4 — Trazabilidad de requirements (obligatorio para features con `"sdd": true`)

Cada `R<n>` de `specs/<name>/requirements.md` debe poder mapearse a al
menos un test concreto en `tests/`. El reviewer rechaza si falta cobertura.

El implementer documenta el mapa en `progress/impl_<name>.md`:

```markdown
## Trazabilidad
- R1 → `test_create_pipeline_valid`
- R2 → `test_create_pipeline_local_server_rejected`
- R3 → `test_update_pipeline_with_active_executions_rejected`
```

### Nivel 5 — Contrato OpenAPI (obligatorio si la feature toca presentation)

Si la feature añade o modifica endpoints (`routes.py` o `schemas.py`), el
archivo `openapi.yaml` en la raíz del repo debe actualizarse:

```bash
python scripts/export_openapi.py
```

El reviewer verifica esto en el checkpoint **C24**. Si `openapi.yaml` no
existe o está desactualizado, el veredicto es `CHANGES_REQUESTED`.

## Anti-patrones (no hacer)

- ❌ "He añadido el comando, debería funcionar." → falta test ejecutable.
- ❌ Test que solo verifica que la función no lanza excepción. → tiene que
  comprobar el resultado concreto.
- ❌ `monkeypatch` o `mock` del filesystem. → usa `tempfile.TemporaryDirectory()` real.
- ❌ Marcar la feature como `done` sin pasar `pytest` y `./init.sh`.
- ❌ Tests de dominio que dependen de infraestructura. → los tests de dominio
  solo importan de `domain/`, nunca de `infrastructure/` ni `application/interfaces/`.

## Verificación final antes de cerrar

```bash
./init.sh           # debe terminar con [OK] Entorno listo
```

Si `./init.sh` está roto, **no** marques nada como `done`. Anota el bloqueo
en `progress/current.md` con estado `blocked` en `feature_list.json`.

## Configuración de pytest

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```
