# Requisitos del Módulo Pipelines

## Estructura del Manifiesto

```yaml
name: "Install Kubernetes Cluster"
description: "Full k8s cluster setup"
sudo: false          # default global — heredado por kits que no especifiquen sudo
debug_level: none    # none (default) | errors | full — heredado por kits que no especifiquen debug_level

targets:
  - server_id: srv_001
  - server_id: srv_002

kits:
  - kit_id: kit_check-ports
    sudo: false       # hereda global
  - kit_id: kit_install-crio
    sudo: true        # override explícito
  - kit_id: kit_install-kubernetes
    sudo: true
  - kit_id: kit_kubeadm-init
    sudo: true

values:
  kit_install-kubernetes:
    version: "1.29"
```

**Regla sudo:** el `sudo` por kit tiene prioridad sobre el global. Si no se especifica en el kit, hereda el global.

## Ciclo de Vida de un Pipeline

```
pending → in_progress → completed   (todos los kits completaron)
                      → failed      (todos los kits fallaron)
                      → partial     (algunos completaron, algunos fallaron)
```

El estado agregado se calcula a partir del estado de las operaciones individuales que genera.

## Requisitos Funcionales

1. **RF-20**: Crear un pipeline con `name`, `description`, `targets[]` (server_ids), `kits[]` (kit_ids con `sudo` y `debug_level` opcionales por kit), `values{}` por kit, `sudo` global y `debug_level` global como defaults. El `debug_level` por kit tiene prioridad sobre el global; si no se especifica en el kit, hereda el global
2. **RF-21**: Lanzar un pipeline. El sistema crea una operación por cada combinación kit+servidor y las ejecuta de forma asíncrona. El pipeline tiene su propio estado agregado
3. **RF-22**: Consultar estado de un pipeline por `id`. Devuelve el estado agregado y la lista de operaciones individuales con su estado, servidor y kit
4. **RF-23**: Listar pipelines del usuario autenticado con paginación
5. **RF-24**: Actualizar un pipeline (`name`, `description`, `targets[]`, `kits[]`, `values{}`, `sudo`). Solo pipelines propios
6. **RF-25**: Eliminar un pipeline. Solo si no tiene ejecuciones en curso. Solo pipelines propios
7. **RF-26**: Consultar historial de ejecuciones de un pipeline con paginación. Cada entrada muestra: fecha de lanzamiento, estado final (`completed`, `failed`, `partial`) y resumen de operaciones

## Requisitos No Funcionales

- **RNF-01**: Endpoints de consulta y listado de pipelines responden en < 200ms p99
- **RNF-02**: Ejecuciones de pipeline lanzadas de forma asíncrona via FastAPI BackgroundTasks (InMemory v1). En v2 se migra a ARQ + Valkey mediante el puerto `TaskQueue` sin tocar el dominio
- **RNF-03**: Conexiones SSH gestionadas con asyncssh con connection pooling desde v1. Pool por servidor, conexiones idle máximo 5 minutos. Timeout de conexión: 30 segundos
- **RNF-05**: Uptime 99.5% mensual
- **RNF-06**: El sistema soporta mínimo 50 operaciones SSH concurrentes (un pipeline con N kits × M servidores genera N×M operaciones en paralelo)
- **RNF-07**: Rate limiting por usuario — lanzar pipeline: máx 20/hora. Implementado en middleware FastAPI (InMemory v1, Valkey v2)
- **RNF-08**: Timeouts — step de kit: 10 minutos por defecto (configurable en manifest); pipeline completo: 30 minutos por defecto (sobreescribible al lanzar via `timeout_seconds`). Si se supera, las operaciones afectadas pasan a `cancelled_unsafe` y el pipeline a `partial` o `failed`
- **RNF-09**: Logs estructurados en JSON. Se loguea obligatoriamente: lanzamiento, finalización, fallo y timeout de cada pipeline y de cada operación individual que genera
- **RNF-10**: Cobertura mínima global 80%; dominio y casos de uso 95%; adaptadores 70%. Todo caso de uso con tests de éxito y error
- **RNF-13**: CORS configurado via `ALLOWED_ORIGINS`

## Reglas de Negocio

- **RN-01**: Un usuario solo puede ver, modificar, lanzar y eliminar sus propios pipelines. La validación de ownership se hace en el caso de uso, no en presentación
- **RN-14**: El `sudo` por kit tiene prioridad sobre el `sudo` global del pipeline. Si no se especifica en el kit, hereda el global
- **RN-15**: El `debug_level` por kit tiene prioridad sobre el `debug_level` global del pipeline. Si no se especifica en el kit, hereda el global; si el global tampoco se declara, el default es `none`
- **RN-16**: Un pipeline solo puede actualizarse si no tiene ejecuciones en estado `in_progress`. El intento lanza una excepción de dominio
- **RN-17**: El servidor `local` no puede usarse como target en pipelines. Solo es válido en operaciones individuales. El intento lanza una excepción de dominio
- **RN-20**: El estado agregado del pipeline se calcula así: `completed` si todas las operaciones llegaron a `completed`; `failed` si todas llegaron a estado terminal sin ninguna en `completed`; `partial` si al menos una llegó a `completed` y al menos una a `failed` o `cancelled_unsafe`
