# ADR-003: SSH Connection Pooling

**Estado:** Aceptado  
**Fecha:** 2026-02-21  
**Decisores:** Equipo ikctl  

## Contexto

ikctl ejecuta operaciones SSH frecuentes:

- Verificación de conectividad (health checks)
- Instalación de aplicaciones remotas
- Backups y recuperación
- Monitoreo de servicios

Problema: Cada conexión SSH tiene overhead significativo:

- Handshake inicial: ~500ms
- Autenticación: ~200ms
- Total por operación: ~700ms + tiempo de ejecución

Para 100 servidores con checks cada 30s, sin pooling:

- 100 conexiones/30s = 3.3 conn/s
- Overhead total: ~2.3s/30s solo en handshakes

## Decisión

Implementar **SSH Connection Pool** reutilizable:

### Especificaciones

- **Pool por servidor**: 1 pool dedicado por servidor remoto (async)
- **Conexiones idle**: mantener 5min antes de cerrar
- **Max concurrent**: 500+ conexiones SSH simultáneas (async permite mucho más)
- **Reuso**: misma conexión para múltiples comandos del mismo servidor
- **Timeout conexión**: 30s para establecer conexión
- **Timeout comando**: configurable por tipo (install 10min, backup 30min)

### Librería

- **Principal**: `asyncssh` con asyncio pool manager (async nativo)
- Alternativa: `paramiko` solo si se requiere sync por legacy

### Estrategia Híbrida

- **Operaciones rápidas** (health checks, queries): async directo en API endpoints
- **Operaciones largas** (installs, backups): FastAPI BackgroundTasks (v1) / ARQ workers + Valkey (v2) con asyncssh (mejor throughput)

## Alternativas Consideradas

| Alternativa | Pros | Contras | Decisión |
|------------|------|---------|----------|
| **asyncssh + async pool** | I/O eficiente, 500+ concurrent, FastAPI native | Curva aprendizaje async | ✅ **ELEGIDO** |
| **paramiko + sync pool** | Simple, maduro | Max 50-100 concurrent, bloquea threads | Fallback legacy |
| **Sin pooling** | Simple implementación | Overhead 700ms/operación | ❌ Ineficiente |
| **SSH multiplexing nativo** | Nativo SSH | Complejo gestionar sockets | ❌ Innecesario |

## Consecuencias

### Positivas

✅ Reducción 90% latencia en operaciones repetidas (700ms → 70ms)  
✅ **5-10x más throughput** con async vs sync (500+ vs 50 concurrent)  
✅ Menos carga en servidores remotos (menos handshakes)  
✅ Mejor UX: operaciones más rápidas  
✅ **FastAPI aprovechado al máximo**: async end-to-end  
✅ Escalabilidad sin aumentar infra (1 proceso = 1000+ conexiones)  

### Negativas

⚠️ Curva aprendizaje async/await (equipo debe conocer asyncio)  
⚠️ Debugging más complejo (coroutines, event loops)  
⚠️ Gestión de estado en memoria (conexiones activas)  

### Implementación

```python
import asyncio
import asyncssh
from datetime import datetime, timedelta

class AsyncSSHConnectionPool:
    def __init__(self, server_id: str, host: str, port: int = 22):
        self.server_id = server_id
        self.host = host
        self.port = port
        self.pool: asyncio.Queue = asyncio.Queue(maxsize=5)
        self.active_connections = 0
        self.idle_timeout = timedelta(minutes=5)
        self.last_used = {}
    
    async def get_connection(self) -> asyncssh.SSHClientConnection:
        """Obtener conexión del pool o crear nueva."""
        try:
            # Intentar obtener conexión existente
            conn = self.pool.get_nowait()
            
            # Verificar si sigue viva
            if not conn.is_closed():
                self.last_used[id(conn)] = datetime.utcnow()
                return conn
            
            # Si está cerrada, crear nueva
            await conn.wait_closed()
        except asyncio.QueueEmpty:
            pass
        
        # Crear nueva conexión
        conn = await asyncio.wait_for(
            asyncssh.connect(
                self.host,
                port=self.port,
                known_hosts=None,  # Configurar apropiadamente
            ),
            timeout=30.0
        )
        self.active_connections += 1
        self.last_used[id(conn)] = datetime.utcnow()
        return conn
    
    async def release_connection(self, conn: asyncssh.SSHClientConnection):
        """Devolver conexión al pool."""
        if conn.is_closed():
            self.active_connections -= 1
            return
        
        try:
            self.pool.put_nowait(conn)
        except asyncio.QueueFull:
            # Pool lleno, cerrar conexión
            conn.close()
            await conn.wait_closed()
            self.active_connections -= 1
    
    async def cleanup_idle(self):
        """Cerrar conexiones idle > 5min."""
        now = datetime.utcnow()
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                last_use = self.last_used.get(id(conn))
                
                if last_use and (now - last_use) > self.idle_timeout:
                    conn.close()
                    await conn.wait_closed()
                    self.active_connections -= 1
                else:
                    await self.pool.put(conn)
                    break
            except asyncio.QueueEmpty:
                break

# Uso en API endpoint
@app.get("/api/v1/servers/{server_id}/health")
async def check_server_health(server_id: str, pool: AsyncSSHConnectionPool):
    """Health check rápido con async."""
    async with pool.get_connection() as conn:
        result = await conn.run("uptime", check=True, timeout=10)
        return {"status": "healthy", "uptime": result.stdout}

# Uso en FastAPI BackgroundTasks (v1) / ARQ worker (v2)
async def install_application(server_id: str, app_name: str):
    """Operación larga en background task."""
    pool = get_pool_for_server(server_id)
    async with pool.get_connection() as conn:
        result = await conn.run(
            f"apt install -y {app_name}",
            check=True,
            timeout=600  # 10min
        )
        return {"status": "installed", "output": result.stdout}
```

### Monitoring

- Métrica: `ssh_pool_active_connections`
- Métrica: `ssh_pool_reuse_rate` (% operaciones que reusan conexión)
- Alert: `ssh_pool_exhausted` si llegamos a límite concurrent

## Riesgos y Mitigación

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Conexión muerta en pool | Fallo al ejecutar comando | Health check antes de devolver conexión |
| Memory leak (conexiones no cerradas) | Agotamiento recursos | Timeout idle automático 5min |
| Límite concurrent alcanzado | Bloqueo operaciones | Queue con timeout, alert si >80% capacity |

## Justificación Async vs Sync

### Por qué async es mejor para ikctl

1. **FastAPI es async nativo**: aprovechamos su potencial completo
2. **SSH es I/O bound**: 700ms handshake = CPU idle esperando red
3. **Throughput 5-10x mayor**: 500+ operaciones vs 50-100 con threads
4. **Escalabilidad sin infra**: 1 proceso maneja 1000+ conexiones
5. **FastAPI BackgroundTasks (v1) / ARQ workers (v2)**: async nativo, sin overhead de broker para v1

### Estrategia de Adopción

**Fase 1** (MVP): Async directo en health checks y queries rápidas  
**Fase 2**: FastAPI BackgroundTasks para operaciones largas (v1) → migrar a ARQ + Valkey en v2  
**Fase 3**: Full async end-to-end con monitoring optimizado  

## Referencias

- [AsyncSSH Documentation](https://asyncssh.readthedocs.io/)
- [FastAPI Async/Await](https://fastapi.tiangolo.com/async/)
- [Python Asyncio Pools](https://docs.python.org/3/library/asyncio-queue.html)
- AGENTS.md - Rendimiento & Escalabilidad
