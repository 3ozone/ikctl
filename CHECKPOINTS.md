# Checkpoints — Criterios objetivos de "estado final correcto"

> El reviewer recorre esta lista antes de aprobar una feature.
> Marca `[x]` los que se cumplen, `[ ]` los que no.

## Código

- [ ] **C1.** Todos los tests pasan (`pytest tests/ -v` sin fallos).
- [ ] **C2.** `./init.sh` termina sin errores.
- [ ] **C3.** No hay `print()` de debug en el código.
- [ ] **C4.** No hay TODOs sin contexto (solo TODOs con issue reference).
- [ ] **C5.** No hay archivos temporales sin borrar.

## Arquitectura

- [ ] **C6.** El dominio no importa de `infrastructure/` ni de `application/`.
- [ ] **C7.** La capa de aplicación no importa de `infrastructure/` directamente (solo vía ports).
- [ ] **C8.** Los módulos se comunican entre sí mediante puertos locales (`application/interfaces/`) + adaptadores (`infrastructure/adapters/`), no por importación directa de `application/` o `infrastructure/` de otro módulo.
- [ ] **C9.** Las entidades de dominio son `@dataclass` (o `@dataclass(frozen=True)` para VOs).
- [ ] **C10.** Las excepciones de dominio heredan de `DomainException` (del shared kernel).
- [ ] **C11.** Los DTOs son `@dataclass(frozen=True)` con solo datos primitivos.
- [ ] **C12.** Los commands son `async def execute(...) -> ResultType`, las queries no publican eventos.
- [ ] **C13.** Los repositorios implementan el port ABC correspondiente.

## Convenciones

- [ ] **C14.** Nombres siguen `conventions.md` (commands: verbo imperativo, queries: verbo interrogativo, repos: `SQLAlchemy*`, adapters: `*Adapter`).
- [ ] **C15.** Los nuevos DTOs llevan sufijo `DTO` (existentes pueden mantener `Result`).
- [ ] **C16.** Los nuevos handlers de eventos llevan sufijo `Handler`.
- [ ] **C17.** Logging usa `get_logger(__name__)` de `shared.infrastructure.logger`, no `logging.getLogger()` ni `structlog.get_logger()` directamente.
- [ ] **C18.** No se importa `structlog` ni `logging` en `domain/` ni `application/`.

## Trazabilidad

- [ ] **C19.** Cada `R<n>` de `requirements.md` tiene al menos un test concreto que lo verifica.
- [ ] **C20.** Todas las tasks de `tasks.md` están marcadas `[x]`.
- [ ] **C21.** El mapa `R<n> → test` está documentado en `progress/impl_<name>.md`.

## Migraciones

- [ ] **C22.** Si se añadieron modelos o columnas, la migración Alembic existe y funciona.
- [ ] **C23.** `alembic upgrade head` se ejecuta sin errores.

## Contrato OpenAPI

- [ ] **C24.** Si la feature añade o modifica endpoints (`routes.py` / `schemas.py`),
      `openapi.yaml` en la raíz está actualizado (`python scripts/export_openapi.py` se ejecutó).