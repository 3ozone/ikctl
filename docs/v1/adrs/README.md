# Architecture Decision Records (ADRs) - ikctl v1

Este directorio contiene las **decisiones arquitectónicas globales** para ikctl v1 que afectan a todo el proyecto, no solo a módulos específicos.

## Índice de ADRs

| # | Título | Estado | Fecha |
|---|--------|--------|-------|
| [001](001-valkey-cache-store.md) | Valkey como Cache Store y Sesiones | ✅ Aceptado | 2026-02-21 |
| [002](002-mariadb-primary-database.md) | MariaDB como Base de Datos Principal | ✅ Aceptado | 2026-02-21 |
| [003](003-ssh-connection-pooling.md) | SSH Connection Pooling | ✅ Aceptado | 2026-02-21 |
| [004](004-observability-stack.md) | Stack de Observabilidad (Logs, Métricas, Trazas) | ✅ Aceptado | 2026-02-21 |
| [005](005-idempotency-resilience.md) | Idempotencia y Resiliencia en Operaciones SSH | ✅ Aceptado | 2026-02-21 |
| [006](006-error-handling-strategy.md) | Estrategia de Manejo de Errores | ✅ Aceptado | 2026-02-21 |
| [007](007-clean-architecture.md) | Clean Architecture (Domain, Application, Infrastructure) | ✅ Aceptado | 2026-02-21 |
| [008](008-event-driven-observability.md) | Event-Driven Architecture & Observability | ✅ Aceptado | 2026-02-21 |
| [009](009-git-as-kit-source.md) | Git como Fuente de Kits (GitOps) | ✅ Aceptado | 2026-03-22 |
| [010](010-credential-types.md) | Entidad Credential Unificada con Tipos (SSH y Git) | ✅ Aceptado | 2026-03-22 |
| [011](011-task-queue-strategy.md) | Estrategia de Cola de Tareas — BackgroundTasks (v1) → ARQ + Valkey (v2) | ✅ Aceptado | 2026-03-22 |
| [012](012-local-connection-adapter.md) | LocalConnectionAdapter para Ejecución Local | ✅ Aceptado | 2026-03-22 |
| [013](013-sftp-sha256-file-cache.md) | Caché de Ficheros por SHA-256 en Transferencia SFTP | ✅ Aceptado | 2026-03-22 |
| [014](014-soft-delete-kits.md) | Soft Delete para Kits | ✅ Aceptado | 2026-03-22 |

## Decisiones por Módulo

Las decisiones específicas de un módulo viven junto al módulo. Los ADRs globales (esta carpeta) afectan a múltiples módulos o a la arquitectura transversal.

- [auth/adrs/](../auth/adrs/) — Autenticación, JWT, OAuth2, 2FA
- `kits/adrs/` — (pendiente de crear cuando el módulo tenga decisiones propias)
- `servers/adrs/` — (pendiente)
- `operations/adrs/` — (pendiente)
- `pipelines/adrs/` — (pendiente)

## Formato de ADR

Cada ADR sigue el formato estándar:

```markdown
# ADR-XXX: Título Descriptivo

**Estado:** Aceptado | Rechazado | Deprecado | Superseded  
**Fecha:** YYYY-MM-DD  
**Decisores:** Equipo responsable  

## Contexto
¿Qué problema estamos resolviendo? ¿Por qué es importante?

## Decisión
¿Qué decidimos hacer? Especificaciones técnicas.

## Alternativas Consideradas
¿Qué otras opciones evaluamos? ¿Por qué las descartamos?

## Consecuencias
### Positivas
✅ Beneficios de esta decisión

### Negativas
⚠️ Costos, trade-offs, limitaciones

### Mitigación
Cómo minimizamos las consecuencias negativas

## Referencias
Enlaces a documentación, papers, ejemplos
```

## Estados de ADR

- **Aceptado**: Decisión activa, en uso
- **Rechazado**: Propuesta evaluada y descartada
- **Deprecado**: Ya no recomendado, pero aún en uso legacy
- **Superseded**: Reemplazado por otro ADR (indicar cuál)

## Cuándo Crear un ADR

Crea un ADR cuando:

- ✅ La decisión afecta a múltiples módulos
- ✅ Tiene impacto significativo en arquitectura, performance o seguridad
- ✅ Es costosa/difícil de revertir
- ✅ Requiere justificación para stakeholders futuros
- ✅ Hay múltiples alternativas viables

No crear ADR para:

- ❌ Decisiones triviales o de implementación local
- ❌ Elecciones obvias sin alternativas
- ❌ Cambios fácilmente reversibles

## Referencias

- [AGENTS.md](../../../AGENTS.md) - Resumen ejecutivo de decisiones
- [ADR Template](https://github.com/joelparkerhenderson/architecture-decision-record)
- [When to write ADRs](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
