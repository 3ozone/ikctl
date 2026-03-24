# ADR-005: Idempotencia y Resiliencia en Operaciones SSH

**Estado:** Aceptado  
**Fecha:** 2026-02-21  
**Decisores:** Equipo ikctl  

## Contexto

Operaciones SSH son inherentemente frágiles:

- Conexiones pueden fallar mid-execution
- Comandos pueden tardar minutos (instalar, compilar)
- Network glitches pueden causar retries
- Usuario puede reintentar operación manualmente

**Problema**: Sin idempotencia, un retry puede causar:

- Reinstalación duplicada de software
- Datos duplicados en sistemas remotos
- Estado inconsistente (mitad instalado, mitad no)

**Ejemplo real**:

```python
User: "Instalar Nginx"
  → Request 1: timeout tras 4min (pero instaló en servidor)
  → Request 2 (retry): instala de nuevo → error (ya existe)
```

## Decisión

Implementar **idempotencia obligatoria** en todas las operaciones SSH:

### 1. Operation ID Único

Cada operación tiene `operation_id` único (UUID):

```python
operation_id = "op_1a2b3c4d"  # Generado una sola vez
```

### 2. Registro en DB ANTES de ejecutar

```sql
INSERT INTO operations (id, user_id, server_id, type, status, created_at)
VALUES ('op_1a2b3c4d', 'usr_123', 'srv_456', 'install_nginx', 'pending', NOW())
ON CONFLICT (id) DO NOTHING;  -- Si ya existe, no reintentar
```

### 3. Estado de Ejecución

```bash
pending → in_progress → completed | failed
```

Si retry llega con mismo `operation_id`:

- **pending/in_progress**: devolver estado actual (operación en curso)
- **completed**: devolver resultado previo (no reejecutar)
- **failed**: permitir retry (cambiar a pending de nuevo)

### 4. Comandos SSH Idempotentes

```bash
# ❌ NO idempotente
apt install nginx

# ✅ Idempotente
dpkg -l nginx >/dev/null 2>&1 || apt install -y nginx
```

### 5. Circuit Breaker

Si servidor falla 5 veces consecutivas:

- Marcar servidor como `unhealthy`
- Rechazar nuevas operaciones por 5min
- Attempt recovery automático tras cooldown

### 6. File Cache por SHA-256 (transferencia SFTP)

Antes de transferir ficheros del kit al servidor remoto, se compara el hash SHA-256 del fichero renderizado (post-Jinja2) contra el último hash almacenado en DB. Solo se transfieren ficheros nuevos o modificados.

```sql
-- Tabla de caché de ficheros por servidor y kit
CREATE TABLE server_kit_file_cache (
    server_id   VARCHAR(36) NOT NULL,
    kit_id      VARCHAR(36) NOT NULL,
    filename    VARCHAR(512) NOT NULL,
    content_hash CHAR(64) NOT NULL,  -- SHA-256 hex
    uploaded_at DATETIME NOT NULL,
    PRIMARY KEY (server_id, kit_id, filename)
);
```

Flujo de transferencia idempotente:

1. Renderizar ficheros del kit con Jinja2 → calcular SHA-256 de cada uno
2. Consultar `server_kit_file_cache` para ese `(server_id, kit_id)`
3. Transferir solo los ficheros cuyo hash difiere o no existen en caché
4. Actualizar caché con nuevos hashes tras transferencia exitosa
5. **Auto-repair**: si SFTP detecta que ficheros ya no existen en el servidor, invalidar caché completa del kit y re-transferir todo

## Alternativas Consideradas

| Alternativa | Pros | Contras | Decisión |
|------------|------|---------|----------|
| **Sin idempotencia** | Simple | Estados inconsistentes | ❌ Inaceptable |
| **Lock optimista (version)** | Previene race conditions | No previene duplicados | Insuficiente |
| **Deduplication window** | Simple (5min cache) | No funciona para retries tardíos | Complementario |
| **SHA-256 file cache** | Evita re-transfer de ficheros sin cambios | Solo aplica a SFTP, no a comandos SSH | ✅ Implementado |

## Consecuencias

### Positivas

✅ **Retries seguros**: usuario puede reintentar sin miedo  
✅ **Consistencia garantizada**: mismo operation_id = mismo resultado  
✅ **Auditoría completa**: historial de todas las ejecuciones  
✅ **Recovery automático**: circuit breaker evita cascading failures  
✅ **Sin re-transfer de ficheros**: SHA-256 cache evita reenviar ficheros idénticos al servidor remoto  

### Negativas

⚠️ Complejidad: cada operación necesita gestión de estado  
⚠️ Storage: tabla `operations` crece con cada ejecución  
⚠️ Latencia: check de duplicados añade ~10ms por request  

### Implementación

```python
# Use Case: InstallApplication
class InstallApplication:
    def execute(self, operation_id: str, server_id: str, app: str):
        # 1. Check si operation_id ya existe
        existing = self.repo.find_operation(operation_id)
        if existing:
            if existing.status == "completed":
                return existing.result  # Devolver resultado previo
            elif existing.status == "in_progress":
                return {"status": "pending", "message": "Operation in progress"}
            elif existing.status == "failed" and not self.should_retry(existing):
                raise OperationFailedError("Max retries exceeded")
        
        # 2. Crear registro ANTES de ejecutar
        operation = Operation(
            id=operation_id,
            server_id=server_id,
            type="install_app",
            status="pending"
        )
        self.repo.save(operation)
        
        # 3. Ejecutar (con retries internos)
        try:
            operation.status = "in_progress"
            self.repo.save(operation)
            
            result = self.ssh_client.execute_idempotent(
                server_id,
                f"check_or_install.sh {app}"
            )
            
            operation.status = "completed"
            operation.result = result
            self.repo.save(operation)
            return result
            
        except SSHError as e:
            operation.status = "failed"
            operation.error = str(e)
            self.repo.save(operation)
            
            # Circuit breaker
            if self.failure_tracker.consecutive_failures(server_id) >= 5:
                self.circuit_breaker.open(server_id, cooldown=300)  # 5min
            
            raise
```

### Retries con Backoff Exponencial

```python
# 3 intentos: 0s, 2s, 4s
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(TemporarySSHError)
)
def execute_ssh_command(server, cmd):
    ...
```

## Timeouts Configurables por Tipo

| Operación | Timeout | Justificación |
|-----------|---------|---------------|
| Health check | 30s | Debe ser rápido |
| Install app | 10min | Descargas + compilación |
| Backup | 30min | Puede ser GB de datos |
| Custom script | Configurable | Usuario define |

## Monitoring

**Métricas clave**:

- `operations_duplicate_attempts_total`: retries evitados por idempotencia
- `circuit_breaker_open{server_id}`: servidores en cooldown
- `operations_failed_total{reason}`: tipos de fallos

**Alerts**:

- `CircuitBreakerOpen`: servidor con >5 fallos consecutivos
- `HighOperationFailureRate`: >10% operaciones fallando

## Referencias

- [Idempotency Keys API Design](https://stripe.com/docs/api/idempotent_requests)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- AGENTS.md - Resiliencia & Tolerancia a Fallos
