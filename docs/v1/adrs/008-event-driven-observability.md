# ADR-008: Event-Driven Architecture & Observability

**Estado:** ✅ Aceptado  
**Fecha:** 2026-02-21  
**Decisores:** Equipo ikctl  

## Contexto

ikctl usa eventos de dominio para desacoplar módulos (auth, servers, operations). Necesitamos:

- **Observabilidad**: trazabilidad de eventos entre módulos
- **Resiliencia**: manejo de fallos, reintentos, DLQ
- **Escalabilidad**: migración futura de InMemory a Valkey Streams

**Problema**: Sin observabilidad en eventos, debugging es imposible. Sin idempotencia, reintentos causan duplicados.

## Decisión

### Fase 1: MVP con EventBus InMemory (Actual)

Eventos síncronos en el mismo proceso:

```python
@dataclass
class DomainEvent:
    event_id: str              # UUID único
    correlation_id: str        # Trazabilidad request completo
    event_type: str            # "UserRegistered"
    aggregate_id: str          # user_id
    aggregate_type: str        # "User"
    payload: dict              # Datos del evento
    version: int               # Schema version (v1, v2)
    occurred_at: datetime      # UTC timestamp
    metadata: dict             # user_id, ip, trace_id

class EventHandler(ABC):
    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """Debe ser idempotente (mismo evento múltiples veces = mismo resultado)."""
        pass
```

**Requisitos MVP:**

- ✅ **CorrelationId**: propagado desde API request hasta event handlers
- ✅ **Idempotencia handlers**: uso de event_id para deduplicación
- ✅ **Schemas versionados**: field `version` en eventos
- ✅ **Logs estructurados**: cada evento publicado/consumido loggeado con correlationId

### Fase 2: Migración a Valkey Streams (Futuro)

> **Nota**: Esta fase se implementa cuando escalemos a múltiples instancias o microservicios.

**Arquitectura:**

```python
# 1. Publisher
event_bus.publish(event)  # Interface no cambia

# 2. Outbox pattern (transaccional)
with db.transaction():
    db.save(user)
    db.outbox.save(event)  # Mismo commit

# 3. Worker publica a Valkey Streams
valkey.xadd("events:UserRegistered", {
    "event_id": event.event_id,
    "correlation_id": event.correlation_id,
    "payload": json.dumps(event.payload),
    "version": event.version
})

# 4. Consumer con idempotencia
consumer_group = valkey.xreadgroup("events", "email-service")
for message in consumer_group:
    if not processed_cache.exists(message.event_id):
        await handle_event(message)
        processed_cache.set(message.event_id, "1", ex=86400)  # 24h TTL
        valkey.xack("events:UserRegistered", "email-service", message.id)
```

**Observabilidad Valkey Streams:**

```python
# Métricas (Prometheus)
event_published_total{event_type}
event_consumed_total{event_type, consumer, status}
event_processing_duration_seconds{event_type, consumer}
event_lag_seconds{stream, consumer_group}     # Tiempo desde publicación
event_dlq_depth{stream}                       # Eventos en Dead Letter Queue
event_retry_total{event_type, attempt}

# Trazas distribuidas (OpenTelemetry)
span_start("event.publish", event_type="UserRegistered")
  └─ span_start("event.consume", consumer="email-service")
      └─ span_start("smtp.send", to=user.email)

# Dead Letter Queue
if retries >= 3:
    valkey.xadd("events:UserRegistered:dlq", message)
    alert("Event processing failed after 3 retries")
```

## Alternativas Consideradas

### 1. Sin Eventos (Acoplamiento Directo)

```python
# RegisterUser llama directamente a EmailService
user = create_user(email, password)
email_service.send_verification(user.email)  # ❌ Acoplado
```

**❌ Rechazado**: Acopla módulos, dificulta testing, no escala.

### 2. Eventos Solo en Infrastructure

```python
# Eventos publicados desde repositories/adapters
user_repo.save(user)
event_bus.publish("UserRegistered")  # ❌ Domain no controla
```

**❌ Rechazado**: Domain pierde control sobre cuándo publicar eventos críticos.

### 3. RabbitMQ desde MVP

**❌ Rechazado**: Over-engineering inicial, infraestructura compleja, Valkey Streams suficiente.

## Consecuencias

### Positivas

✅ **Desacoplamiento**: Módulos independientes, cambios aislados  
✅ **Observabilidad desde MVP**: CorrelationId en logs estructura debugging  
✅ **Migración gradual**: EventBus interface permite cambiar implementación sin tocar lógica  
✅ **Idempotencia**: Handlers seguros para reintentos  
✅ **Escalabilidad futura**: Valkey Streams listo para microservicios  
✅ **DLQ**: Eventos fallidos no se pierden, reprocesamiento manual  

### Negativas

⚠️ **Complejidad inicial**: EventBus InMemory + estructura de eventos  
⚠️ **Overhead observabilidad**: Logs/métricas por evento (~2-5ms)  
⚠️ **Eventual consistency**: Eventos asíncronos (Valkey Streams) no inmediatos  
⚠️ **Debugging distribuido**: Requiere correlationId y trazas end-to-end  

### Mitigaciones

- **Testing**: Unit tests para handlers (idempotencia), integration tests para flujo completo
- **Contract tests**: Validar schemas versionados entre publishers/consumers
- **Logs estructurados**: CorrelationId en TODOS los logs para trazabilidad
- **Alertas**: Métricas de lag y DLQ depth para detectar problemas proactivamente

## Referencias

- [ADR-001: Valkey Cache Store](001-valkey-cache-store.md) - Pub/Sub con Valkey Streams
- [ADR-004: Observability Stack](004-observability-stack.md) - Logs, métricas, trazas
- [ADR-005: Idempotency & Resilience](005-idempotency-resilience.md) - Patrones idempotencia
- [AGENTS.md](../../AGENTS.md) - EventBus InMemory para MVP

## Implementación

**MVP (Fase actual):**
```bash
shared/domain/
├── events.py              # DomainEvent base class
└── event_bus.py          # EventBus InMemory interface + impl

shared/infrastructure/
└── event_bus_valkey.py   # EventBus Valkey Streams (futuro)
```

**Roadmap:**

1. ✅ Documentar arquitectura (este ADR)
2. ⏳ Implementar DomainEvent + EventBus InMemory
3. ⏳ Eventos críticos: UserRegistered, OperationCompleted
4. ⏳ Contract tests entre módulos
5. 🔮 Migración a Valkey Streams (cuando múltiples instancias)
