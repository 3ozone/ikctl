# ADR-001: Valkey como Cache Store y Sesiones

**Estado:** Aceptado  
**Fecha:** 2026-02-21  
**Decisores:** Equipo ikctl  

## Contexto

ikctl requiere un sistema de almacenamiento en memoria para:

- Cache de tokens JWT (blacklist de tokens revocados)
- Rate limiting por usuario y operación
- Sesiones activas de usuarios
- Cache de consultas frecuentes (servidores, operaciones)

Necesitamos alta velocidad (<10ms latencia), soporte TTL automático, y persistencia opcional.

## Decisión

Adoptamos **Valkey** como cache store principal.

### Configuración

- **Tokens JWT blacklist**: TTL dinámico según expiración del token
- **Sesiones**: access tokens 15min, refresh tokens 7 días
- **Rate limiting**: contadores con TTL de 1 min/15min/1h según tipo
- **Cache queries**: TTL 5min para listados, 1h para datos estáticos
- **Pub/Sub (Valkey Streams)**: eventos de dominio para desacoplamiento entre módulos

## Alternativas Consideradas

| Alternativa | Pros | Contras | Razón de descarte |
|-------------|------|---------|-------------------|
| **Redis**   | Maduro, gran ecosistema | Licencia propietaria desde 2024 | Filosofía open source |
| **Memcached** | Simple, rápido | Sin persistencia, sin TTL por key | Funcionalidad limitada |
| **DragonflyDB** | Compatible Redis, más rápido | Comunidad pequeña, joven | Riesgo de madurez |

## Consecuencias

### Positivas

✅ 100% open source (BSD-3-Clause)  
✅ Compatible con redis-py (drop-in replacement)  
✅ TTL por key para gestión automática de expiración  
✅ Persistencia opcional para recuperación tras reinicio  
✅ Soporte estructuras avanzadas (sets, sorted sets) para rate limiting  

### Negativas

⚠️ Ecosistema más nuevo que Redis (tutoriales, SO answers)  
⚠️ Librerías Python usan nomenclatura "redis" (confusión)  

### Mitigación

- Abstracción en capa de infraestructura (adapter pattern)
- Si Valkey falla en 2 años, volver a Redis es cambio de 1 línea
- Documentar configuración en `DOCKER_SETUP.md`

## Pub/Sub con Valkey Streams

> **Nota**: Para MVP/monolito modular usamos **EventBus InMemory** (eventos síncronos en el mismo proceso). Esta sección documenta la arquitectura futura para cuando escalemos a microservicios. El diseño con abstracciones permite migrar sin cambiar lógica de negocio.

### Casos de Uso

ikctl usa **Valkey Streams** para publicar eventos de dominio:

**Eventos típicos:**

- `OperationCompleted` → email notificación, audit log, trigger siguiente operación
- `ServerHealthCheckFailed` → alertas, circuit breaker, notificaciones admin
- `UserRegistered` → email verificación, setup inicial, analytics
- `SSHConnectionPoolExhausted` → alertas monitoring, escalado automático

### Arquitectura Outbox + Pub/Sub

```python
# 1. Operación guarda evento en Outbox (transaccional)
with db.transaction():
    operation.status = "completed"
    db.save(operation)
    
    event = DomainEvent(
        type="OperationCompleted",
        aggregate_id=operation.id,
        payload={"server_id": operation.server_id, "kit": operation.kit}
    )
    db.outbox.save(event)  # Mismo commit

# 2. Worker lee Outbox y publica a Valkey Streams
while True:
    events = db.outbox.get_pending()
    for event in events:
        valkey.xadd(f"events:{event.type}", event.to_dict())
        db.outbox.mark_published(event.id)

# 3. Consumers suscritos procesan eventos
for message in valkey.xread({"events:OperationCompleted": ">"}:
    event = DomainEvent.from_dict(message)
    # Procesar: enviar email, audit log, etc.
```

### Ventajas Valkey Streams vs Alternativas

| Característica | Valkey Streams | RabbitMQ | Kafka |
|----------------|----------------|----------|-------|
| **Latencia** | <10ms | ~50ms | ~100ms |
| **Persistencia** | Opcional | Sí | Sí |
| **Consumer groups** | ✅ | ✅ | ✅ |
| **Orden garantizado** | Por stream | Por queue | Por partition |
| **Complejidad setup** | Baja (ya tenemos Valkey) | Media | Alta |
| **Overhead infra** | Ninguno | Broker dedicado | Cluster 3+ nodos |
| **Throughput** | 100k+ msg/s | 50k msg/s | 1M+ msg/s |
| **Ideal para** | MVP, eventos internos | Workflows complejos | Event sourcing |

**Decisión:** Valkey Streams es suficiente para MVP. Si necesitamos features avanzadas (routing complejo, DLQ), migrar a RabbitMQ.

### Ejemplo Implementación

```python
# Publisher (en use case)
class CompleteOperation:
    def execute(self, operation_id: str):
        with self.db.transaction():
            operation = self.repo.find(operation_id)
            operation.complete()
            self.repo.save(operation)
            
            # Evento en Outbox (atómico con operación)
            event = OperationCompletedEvent(
                operation_id=operation.id,
                server_id=operation.server_id,
                kit=operation.kit,
                occurred_at=datetime.utcnow()
            )
            self.event_store.save(event)

# Outbox worker (background)
class OutboxPublisher:
    async def run(self):
        while True:
            events = await self.event_store.get_unpublished(limit=100)
            for event in events:
                # Publicar a Valkey Stream
                await self.valkey.xadd(
                    f"domain_events:{event.type}",
                    {"payload": event.to_json()}
                )
                await self.event_store.mark_published(event.id)
            
            await asyncio.sleep(0.1)  # Poll cada 100ms

# Consumer (notification service)
class EmailNotificationConsumer:
    async def consume(self):
        while True:
            messages = await self.valkey.xread(
                {"domain_events:OperationCompleted": "$"},
                block=1000,  # Block 1s si no hay mensajes
                count=10
            )
            
            for stream, msgs in messages:
                for msg_id, data in msgs:
                    event = OperationCompletedEvent.from_json(data["payload"])
                    await self.send_email(event)
                    await self.valkey.xack(stream, "email-group", msg_id)
```

### Garantías

✅ **Exactamente una vez** (outbox pattern): evento guardado en DB transaccionalmente  
✅ **Al menos una vez** (pub/sub): Valkey Streams con consumer groups  
✅ **Orden por stream**: eventos del mismo tipo procesados en orden  
✅ **Resiliencia**: si consumer falla, mensaje permanece en stream hasta ACK  

## Referencias

- [Valkey Project](https://valkey.io/)
- [Valkey vs Redis comparación](https://github.com/valkey-io/valkey)
- AGENTS.md - Arquitectura & Decisiones Técnicas
