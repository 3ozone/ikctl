# ADR-002: MariaDB como Base de Datos Principal

**Estado:** Aceptado  
**Fecha:** 2026-02-21  
**Decisores:** Equipo ikctl  

## Contexto

ikctl necesita una base de datos relacional para:

- Gestión de usuarios, autenticación, perfiles
- Inventario de servidores remotos (SSH credentials, metadata)
- Historial de operaciones y deployments
- Auditoría y logs estructurados

Requisitos:

- ACID para transacciones críticas (auth, operaciones)
- Índices eficientes para búsquedas
- Soporte JSON para metadata flexible
- Migraciones versionadas
- Open source

## Decisión

Adoptamos **MariaDB** como base de datos principal con una estrategia de **una base de datos por módulo** dentro de un único servidor MariaDB. Esta estrategia permite evolucionar hacia microservicios en el futuro moviendo cada base de datos a su propio servidor sin cambiar el código de dominio.

### Bases de datos por módulo

| Base de datos | Módulo | Tablas principales |
|--------------|--------|--------------------|
| `ikctl_auth` | Auth | `users`, `refresh_tokens`, `verification_tokens`, `password_history` |
| `ikctl_servers` | Servers | `servers`, `credentials`, `server_groups`, `server_kit_file_cache` |
| `ikctl_kits` | Kits | `kits`, `kit_files` |
| `ikctl_operations` | Operations | `operations` |
| `ikctl_pipelines` | Pipelines | `pipelines`, `pipeline_executions` |

### Reglas entre módulos

- **Sin Foreign Keys cross-DB**: las referencias entre módulos son IDs simples (strings/UUIDs), no FK reales
- **Sin JOINs cross-DB**: la capa de aplicación (use cases) resuelve las referencias consultando cada repositorio por separado
- **Migraciones independientes**: cada módulo tiene su propio directorio Alembic y sus propias versiones
- **Atomicidad**: dentro de un módulo las transacciones son ACID. Entre módulos se usa lógica de compensación en el use case si es necesario

### Evolución a microservicios (v3+)

Cada base de datos puede moverse a su propio servidor MariaDB cambiando únicamente la `DATABASE_URL` de ese módulo. El código de dominio no cambia.

### Migración desde `ikctl_db`

La base de datos original `ikctl_db` del módulo auth se renombra a `ikctl_auth` para consistencia. Impacta solo a archivos de configuración: `settings.py`, `alembic.ini`, `docker-compose.yml`, `docker/init.sql`.

## Alternativas Consideradas

| Alternativa | Pros | Contras | Razón de descarte |
|------------|------|---------|-------------------|
| **PostgreSQL** | JSON avanzado, extensiones | Más complejo, overhead | YAGNI (no necesitamos JSONB avanzado) |
| **MySQL** | Popular, compatible | Oracle ownership, dudas licencia | MariaDB es fork community-driven |
| **SQLite** | Simple, embebido | No escalable, sin concurrencia | Necesitamos multi-usuario |

## Consecuencias

### Positivas

✅ 100% open source (GPL v2)  
✅ Compatible con MySQL (fácil migración si necesario)  
✅ Soporte nativo JSON para metadata flexible  
✅ Performance excelente con índices (InnoDB)  
✅ Python: SQLAlchemy/Alembic tienen soporte completo  

### Negativas

⚠️ JSON menos avanzado que PostgreSQL (no JSONB indexable)  
⚠️ Menos extensiones que PostgreSQL  

### Decisiones de Diseño

- **Índices obligatorios**: user_id, email, server_id, operation_id, created_at
- **Paginación**: limit=50 por defecto, max=100
- **Migraciones**: Alembic con scripts up/down versionados
- **Backup**: cada migración requiere plan de rollback

## Impacto en Desarrollo

```python
# Ejemplo configuración SQLAlchemy
DATABASE_URL = "mysql+pymysql://user:pass@localhost:3306/ikctl"

# Índices en modelos
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True)  # Índice
    created_at = Column(DateTime, index=True)  # Índice
```

## Referencias

- [MariaDB vs MySQL](https://mariadb.com/kb/en/mariadb-vs-mysql-compatibility/)
- [SQLAlchemy MariaDB Dialect](https://docs.sqlalchemy.org/en/20/dialects/mysql.html)
- AGENTS.md - Datos & Almacenamiento
