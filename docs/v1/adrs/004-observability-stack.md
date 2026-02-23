# ADR-004: Stack de Observabilidad (Logs, Métricas, Trazas)

**Estado:** Aceptado  
**Fecha:** 2026-02-21  
**Decisores:** Equipo ikctl  

## Contexto

ikctl ejecuta operaciones críticas remotas que pueden fallar por múltiples razones:

- Problemas de red
- Fallos en servidores remotos
- Errores de autenticación
- Timeouts en operaciones largas

Necesitamos:

- **Debugging rápido**: identificar causa raíz en <5min
- **Proactividad**: detectar problemas antes que usuarios
- **SLOs medibles**: validar cumplimiento 99% uptime

## Decisión

Implementar **observabilidad completa** con tres pilares:

### 1. Logs Estructurados (JSON)

```json
{
  "timestamp": "2026-02-21T10:30:45Z",
  "level": "INFO",
  "user_id": "usr_123",
  "request_id": "req_abc",
  "operation_type": "ssh_install",
  "server_id": "srv_456",
  "duration_ms": 2340,
  "status": "success",
  "message": "Nginx installed successfully"
}
```

**Librería**: `structlog` (Python)  
**Campos obligatorios**: timestamp, level, user_id, request_id, operation_type  
**Eventos críticos**: login, SSH exec, cambios perfil, errores  

### 2. Métricas (Prometheus format)

- **Latencia**: `api_request_duration_seconds{endpoint, method}` (p50/p95/p99)
- **Errores**: `api_errors_total{endpoint, error_type}`
- **SSH**: `ssh_connections_active`, `ssh_operations_duration_seconds`
- **Sistema**: `process_cpu_percent`, `process_memory_bytes`

**Librería**: `prometheus_client` (Python)  
**Scraping**: endpoint `/metrics` para Prometheus  

### 3. Trazas Distribuidas (OpenTelemetry)

Correlación request → queue → SSH execution:

```bash
[API Request] req_abc
  └─ [Queue Task] task_xyz
      └─ [SSH Connection] conn_789
          └─ [Command Execution] cmd_install_nginx
```

**Librería**: `opentelemetry-api`, `opentelemetry-sdk`  
**Exporter**: OTLP (compatible Jaeger, Tempo, Zipkin)

## SLIs & SLOs Definidos

| Indicador (SLI) | Objetivo (SLO) | Medición |
|-----------------|----------------|----------|
| Latencia auth endpoints | 99% < 100ms | `api_request_duration_seconds{endpoint="/api/v1/login"}` |
| Uptime API | 99.5% disponible | `up{job="ikctl-api"}` |
| Éxito operaciones SSH | 95% success en <5min | `ssh_operations_total{status="success"} / ssh_operations_total` |
| Tasa de errores | <1% req/min | `api_errors_total / api_requests_total` |

## Alternativas Consideradas

| Componente | Alternativas | Decisión |
|------------|--------------|----------|
| **Logs** | structlog vs python-json-logger | structlog (más flexible) |
| **Métricas** | Prometheus vs StatsD vs DataDog | Prometheus (open source, estándar) |
| **Trazas** | OpenTelemetry vs Jaeger nativo | OpenTelemetry (vendor-neutral) |

## Consecuencias

### Positivas

✅ **Debugging 10x más rápido**: logs con request_id correlacionan todo el flujo  
✅ **Alertas proactivas**: detectar degradación antes de fallo total  
✅ **SLOs medibles**: datos objetivos para mejora continua  
✅ **Vendor-neutral**: no dependemos de un proveedor específico  

### Negativas

⚠️ Overhead performance: ~5-10ms por request (logging + métricas)  
⚠️ Volumen de datos: logs pueden crecer rápido (rotación diaria)  
⚠️ Complejidad inicial: setup de colectores y dashboards  

### Implementación

```python
# Ejemplo logging estructurado
import structlog

logger = structlog.get_logger()
logger.info(
    "ssh_operation_started",
    user_id=user.id,
    request_id=context.request_id,
    server_id=server.id,
    operation="install_nginx"
)

# Ejemplo métrica
from prometheus_client import Histogram

ssh_duration = Histogram(
    'ssh_operations_duration_seconds',
    'Duration of SSH operations',
    ['operation_type', 'server_id']
)

with ssh_duration.labels(operation_type='install', server_id=server.id).time():
    execute_ssh_command(server, "apt install nginx")
```

## Stack de Deploy Recomendado

- **Logs**: Loki + Grafana (query logs estructurados)
- **Métricas**: Prometheus + Grafana (dashboards, alertas)
- **Trazas**: Tempo + Grafana (visualización distribuida)
- **Todo-en-uno**: Grafana Cloud free tier o self-hosted stack

## Referencias

- [Structlog Documentation](https://www.structlog.org/)
- [Prometheus Python Client](https://github.com/prometheus/client_python)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- AGENTS.md - Observabilidad
