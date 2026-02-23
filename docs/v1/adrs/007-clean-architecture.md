# ADR-007: Clean Architecture (Domain, Application, Infrastructure)

**Estado:** ✅ Aceptado  
**Fecha:** 2026-02-21  
**Decisores:** Equipo ikctl  

## Contexto

Necesitamos una arquitectura de software que permita:

- Código **testeable** sin dependencias externas (DB, APIs)
- **Separación de concerns** clara entre capas
- **Independencia de frameworks** (FastAPI, MariaDB intercambiables)
- **Mantenibilidad** a largo plazo (cambios aislados por capa)
- **Escalabilidad** hacia microservicios si es necesario

**Problema**: Arquitecturas tradicionales (MVC, Layered) acoplan lógica de negocio con frameworks y DB, dificultando testing y evolución.

## Decisión

Aplicamos **Clean Architecture** con estructura de 3 capas:

```bash
domain/          → Lógica de negocio pura (entities, value objects, exceptions)
application/     → Casos de uso, DTOs, Interfaces (ports)
infrastructure/  → Implementaciones (persistence, adapters, presentation)
```

### Principios Aplicados

1. **Dependency Inversion**: Infrastructure depende de Application (interfaces), no al revés
2. **Separation of Concerns**: Cada capa tiene responsabilidad única
3. **Testability**: Domain y Application testeables sin DB/HTTP
4. **Framework Independence**: Domain no conoce FastAPI/MariaDB

### Estructura Detallada

```python
domain/
├── entities.py        # User, RefreshToken
├── value_objects.py   # Email, Password
└── exceptions.py      # DomainException, InvalidEmailError

application/
├── exceptions.py      # UseCaseException, UnauthorizedOperationError
├── dtos/              # DTOs agnósticos (dataclasses)
├── interfaces/        # Ports (ABC): IUserRepository, IEmailService
└── use_cases/         # Orquestación de lógica

infrastructure/
├── exceptions.py      # InfrastructureException, DatabaseConnectionError
├── persistence/       # Repositories (MariaDB, Valkey)
├── adapters/          # Servicios externos (SMTP, OAuth, JWT)
└── presentation/      # FastAPI (routers, schemas Pydantic)
```

**Detalle completo**: Ver [docs/v1/FOLDER_STRUCTURE.md](../FOLDER_STRUCTURE.md)

### Módulo Shared (Excepción)

El módulo `shared/` NO sigue la estructura completa de capas. Contiene:

- `domain/`: Abstracciones genéricas (DomainEvent base, exceptions base)
- `infrastructure/`: Herramientas reutilizables (EventBus, logger, DB/cache clients)

**Regla**: Sin lógica de negocio específica. Solo código genérico compartible entre módulos.

## Alternativas Consideradas

### 1. Layered Architecture (Tradicional)

```bash
presentation/ → business_logic/ → data_access/
```

**❌ Rechazado por:**

- Data Access depende de detalles de DB (dificulta testing)
- Business Logic puede acceder directamente a presentation
- Acoplamiento con frameworks (FastAPI, SQLAlchemy)
- Difícil migrar a microservicios

### 2. MVC/MTV (Django/Flask)

```bash
models.py → views.py → templates/
```

**❌ Rechazado por:**

- Acopla lógica de negocio con ORM (models = DB tables)
- Controllers/Views conocen detalles HTTP
- No testeable sin framework activo
- Dificulta reutilización de lógica (CLI + API REST)

### 3. Modular Monolith Simple

```bash
auth/ → user.py, handlers.py, db.py
servers/ → server.py, handlers.py, db.py
```

**❌ Rechazado por:**

- Sin separación domain/infrastructure
- Lógica de negocio mezclada con persistencia
- Dificulta testing unitario (necesita DB siempre)
- Escala mal con complejidad creciente

### 4. Microservicios desde inicio

**❌ Rechazado por:**

- Over-engineering para MVP
- Complejidad operacional (múltiples deploys, comunicación)
- Clean Architecture permite migración gradual cuando sea necesario

## Consecuencias

### Positivas

✅ **Testabilidad**: Domain/Application testeables sin DB/HTTP (unit tests rápidos)  
✅ **Independencia de frameworks**: Cambiar FastAPI → Flask sin tocar domain  
✅ **Evolución segura**: Cambios en DB no afectan lógica de negocio  
✅ **Reutilización**: Use cases compartidos entre API REST y CLI  
✅ **Onboarding**: Estructura clara facilita incorporación de nuevos devs  
✅ **Microservicios futuros**: Migración incremental (domain/application intactos)  
✅ **Mantenibilidad**: Bugs aislados por capa, código predecible  

### Negativas

⚠️ **Complejidad inicial**: Más carpetas y archivos que MVC simple  
⚠️ **Curva de aprendizaje**: Requiere entender Dependency Inversion  
⚠️ **Boilerplate**: Interfaces + implementaciones (vs acceso directo a DB)  
⚠️ **Over-engineering inicial**: Para proyectos muy simples puede ser excesivo  

### Mitigaciones

- **Documentación exhaustiva**: FOLDER_STRUCTURE.md + AGENTS.md + ejemplos
- **TDD desde inicio**: Tests guían la implementación correcta
- **Composition root simple**: Wiring manual en main.py (sin DI container complejo)
- **Aplicación gradual**: Empezar con 1 módulo (auth), replicar patrón

## Referencias

- [The Clean Architecture (Uncle Bob)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Hexagonal Architecture (Alistair Cockburn)](https://alistair.cockburn.us/hexagonal-architecture/)
- [docs/v1/FOLDER_STRUCTURE.md](../FOLDER_STRUCTURE.md) - Implementación en ikctl
- [AGENTS.md](../../AGENTS.md) - Buenas prácticas

## Impacto en el Proyecto

- **Módulos actuales**: Migrar `auth/` de estructura plana a domain/application/infrastructure
- **Futuro**: Todos los módulos (servers, operations, users) seguirán esta estructura
- **Testing**: Separar tests por capa (test_domain, test_use_cases, test_persistence)
- **CI/CD**: Tests unitarios rápidos (domain/application) vs integration (infrastructure)
