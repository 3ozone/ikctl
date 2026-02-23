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

## Decisiones por Módulo

Para decisiones específicas de módulos individuales, consulta:

- [auth/adrs/](../auth/adrs/) - Autenticación y autorización
- [servers/adrs/](../servers/adrs/) - Gestión de servidores
- [operations/adrs/](../operations/adrs/) - Ejecución de operaciones
- [users/adrs/](../users/adrs/) - Gestión de usuarios

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
