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

Adoptamos **MariaDB** como base de datos principal.

### Esquema de ownership

- `auth`: tablas de usuarios, tokens, verificaciones
- `servers`: inventario de servidores, credenciales
- `operations`: historial de ejecuciones SSH, logs
- `shared`: eventos de dominio, outbox pattern

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
