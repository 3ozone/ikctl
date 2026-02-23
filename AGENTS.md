# AGENTS.md - Guía de Desarrollo para ikctl

## ⚠️ PROCESO OBLIGATORIO - NUNCA SALTARSE

**REGLA DE ORO**: Cada cambio debe hacerse **UNO POR UNO** con aprobación entre cada paso.

### Flujo Estricto para Cada Tarea

1. **Crear TEST** → ⛔ **PARAR** → Explicar qué test acabas de crear → Pedir permiso para continuar
2. **Crear EXCEPCIÓN** (si necesaria) → ⛔ **PARAR** → Explicar qué excepción creaste → Pedir permiso
3. **Crear IMPLEMENTACIÓN** → ⛔ **PARAR** → Explicar qué implementaste → Pedir permiso
4. **Ejecutar TESTS** → ⛔ **PARAR** → Mostrar resultado (GREEN/RED) → Pedir permiso
5. **Actualizar TASKS.md** → ⛔ **PARAR** → Confirmar cambio → Pedir permiso para siguiente tarea

### ❌ PROHIBIDO

- Hacer múltiples pasos sin aprobación entre ellos
- Crear test + implementación + actualizar TASKS.md en un solo turno
- Usar `multi_replace_string_in_file` para varios archivos diferentes sin aprobación previa
- Continuar a la siguiente tarea sin confirmación explícita del usuario

### ✅ Ejemplo CORRECTO

```
Agente: "He creado el test test_password_history.py con 6 tests para validar 
        la entity PasswordHistory. ¿Puedo continuar con la excepción?"
Usuario: "adelante"
Agente: "He añadido InvalidPasswordHistoryError en exceptions.py. 
        ¿Puedo continuar con la implementación de la entity?"
Usuario: "sí"
Agente: "He implementado PasswordHistory en entities.py con validaciones 
        en __post_init__. ¿Ejecuto los tests?"
```

### ❌ Ejemplo INCORRECTO

```
Agente: "He creado el test, la excepción y la entity PasswordHistory. 
        Los tests pasan. ¿Actualizo el TASKS.md?"
```

**RECUERDA**: Un paso a la vez, siempre pedir permiso antes de continuar.

---

## 🧭 Filosofía de Desarrollo

En ikctl seguimos los principios de:

- **Clean Architecture**: Separación estricta en capas (dominio, aplicación, infraestructura, presentación)
- **SOLID**: 5 principios para código mantenible y extensible
- **DRY** (Don't Repeat Yourself): No repetir lógica ni estructuras
- **KISS** (Keep It Simple, Stupid): Soluciones simples, código claro
- **YAGNI** (You Aren't Gonna Need It): Solo implementamos lo necesario
- **TDD** (Test Driven Development): Primero los tests, luego el código

## 🏛️ Arquitectura & Decisiones Técnicas

### Rendimiento & Escalabilidad

- Valkey para: tokens JWT blacklist, rate limiting, sesiones (TTL: access 15min, refresh 7d)
- API async nativa (FastAPI + asyncio) + Celery workers async para operaciones SSH largas
- Índices DB: user_id, email, server_id, created_at. Paginación obligatoria (limit=50)
- Latencias objetivo: CRUD <200ms, auth <100ms, operaciones SSH async (timeout 5min)
- Rate limiting: 100 req/min por usuario, 20 SSH/hora, 5 intentos login/15min
- SSH connection pooling: asyncssh con pool async, idle 5min, 500+ concurrent (5-10x throughput vs sync)
- Resiliencia: retry 3x con backoff + circuit breaker tras 5 fallos consecutivos

### Resiliencia & Tolerancia a Fallos

- Idempotencia: operaciones SSH con operation_id único (evitar reinstalaciones duplicadas)
- Timeouts configurables: conexión SSH 30s, ejecución comando según tipo (install 10min, backup 30min)
- EventBus InMemory para monolito modular: eventos de dominio desacoplando módulos (migración a Valkey Streams cuando microservicios)
- Transacciones compensatorias: rollback de instalaciones fallidas (desinstalar, limpiar archivos)
- Health checks: endpoints /healthz (liveness) y /readyz (readiness) para k8s

### Seguridad por Diseño

- Autenticación: OAuth2 + JWT (access 15min, refresh 7d), soporte GitHub OAuth
- Autorización: RBAC por defecto, principio de mínimo privilegio (user/admin)
- Secretos: claves SSH y passwords en vault (Vault/AWS Secrets), nunca en código ni logs
- Validación: entrada en presentación (Pydantic), salida sanitizada (prevenir XSS)
- Cifrado: contraseñas bcrypt cost=12, conexiones SSH con ed25519, TLS en tránsito
- Auditoría: logs estructurados de acciones críticas (login, SSH exec, cambios perfil)

### Observabilidad

- Logs estructurados: JSON con context (user_id, request_id, operation_type, timestamp)
- Métricas: latencia p50/p95/p99, tasa errores, conexiones SSH activas, memoria/CPU
- Trazas distribuidas: correlación request → queue → SSH execution (OpenTelemetry)
- SLI: latencia endpoints auth, tasa éxito operaciones SSH, disponibilidad API
- SLO: auth 99% <100ms, API 99.5% uptime, operaciones SSH 95% éxito en <5min

### Evolución Segura

- Versionado API: /api/v1/, /api/v2/ coexistentes, deprecación gradual (6 meses)
- Feature flags: toggles en config para activar/desactivar funcionalidades en runtime
- Compatibilidad: campos nuevos opcionales, nunca eliminar campos sin deprecación
- Tests de contrato: validar schemas OpenAPI contra implementación real
- Rollback rápido: despliegues blue/green, posibilidad de volver a versión anterior en <5min

### Datos & Almacenamiento

- DB principal: MariaDB (transaccional, ACID), Valkey para cache/sesiones
- Ownership: cada módulo gestiona sus propias tablas (auth, servers, operations)
- Lecturas optimizadas: vistas materializadas para dashboards, cache en Valkey para consultas frecuentes
- Migraciones versionadas: Alembic con scripts up/down, nunca modificar migraciones aplicadas
- Rollback DB: cada migración debe tener su reversa funcional, backup antes de cambios

### Buenas Prácticas Clean Architecture

- **Interfaces como Puertos (Dependency Inversion)**: Repositorios y servicios externos se definen como ABC en `domain/interfaces/`, implementaciones concretas en `infrastructure/`. Casos de uso dependen de abstracciones, no de implementaciones.
- **Nombres de Dominio, No Tecnología**: `UserRepository` ✅, `MariaDBUserRepository` ❌ en domain/. La tecnología se revela solo en infrastructure/ con nombres como `MariaDBUserRepositoryImpl`.
- **Adaptadores Separados**: Lógica de conversión de datos externos (API responses, DB rows) vive en adaptadores (infrastructure/adapters/), nunca mezclada con casos de uso.
- **Wiring/Composición Manual**: En `main.py` para MVP. Cuando tengamos 10+ módulos, evaluaremos DI container (dependency-injector). Principio: simplicidad primero, herramientas cuando escale.
- **Tests de Contrato**: Verificar compatibilidad entre abstracciones y adaptadores (ver "Estrategia de Testing" → Contract Tests). Crítico para EventBus y repositories.

### Manejo de Errores

- **Excepciones Pythonic**: Usamos `raise`/`try-except` tradicionales, NO Result/Either patterns (ver ADR-006)
- **Jerarquía de Excepciones**: `DomainException` (ej: `InvalidEmailError`), `InfrastructureException` (ej: `DatabaseConnectionError`), `UseCaseException` (ej: `UnauthorizedOperationError`)
- **Nomenclatura Específica**: Una excepción por error (`InvalidEmailError`, NO `ValidationError("email")`)
- **Propagación Limpia**: Dominio raise → Casos de uso propagan/transforman → Presentación captura con exception handlers
- **Exception Handlers FastAPI**: Registrados centralmente para convertir excepciones a HTTP responses (DomainException → 400, UseCaseException → 422)
- **Logging Estructurado**: Middleware captura todas las excepciones con contexto (user_id, path, error_type)
- **Documentación**: Todos los métodos públicos documentan `Raises:` en docstrings
- **Testing**: Cada caso de uso debe tener tests de error con `pytest.raises(SpecificError)`

## 🚦 Proceso para Crear un Nuevo Módulo

1. **Documentación Inicial**
   - Crear documento de requisitos en `docs/v1/<modulo>/` (funcionales, no funcionales, negocio)
   - Escribir ADRs relevantes en `docs/v1/<modulo>/adrs/`
   - Definir el contrato de API en `openapi.yaml`

2. **Diseño**
   - Definir entidades, value objects, interfaces y eventos de dominio
   - Esquematizar la arquitectura del módulo siguiendo Clean Architecture

3. **TDD: Test First**
   - Escribir los tests de los casos de uso y validadores de dominio
   - No escribir código de implementación hasta que el test esté definido (RED)

4. **Implementación Iterativa**
   - Implementar solo lo necesario para pasar el test (GREEN)
   - Refactorizar si es necesario (REFACTOR)
   - Documentar el avance en el documento de feature
   - Repetir función a función, pidiendo permiso antes de cada nueva función

5. **Revisión y Documentación**
   - Actualizar documentación técnica y de usuario
   - Revisar ADRs y requisitos
   - Validar cobertura de tests

## 🏗️ Estructura de Carpetas

```bash
app/v1/
├── auth/
│   ├── domain/                  # Entities, Value Objects, Exceptions
│   ├── application/             # Use Cases, DTOs, Interfaces (Ports)
│   └── infrastructure/          # Persistence, Adapters, Presentation
│       ├── persistence/         # Repositories (DB)
│       ├── adapters/            # Servicios externos (SMTP, JWT, OAuth)
│       └── presentation/        # FastAPI (routers, schemas, middlewares)
├── users/
├── servers/
├── operations/
├── shared/                      # Código compartido (events, logger, db, cache)
│   ├── domain/                  # DomainEvent, abstracciones genéricas
│   └── infrastructure/          # EventBus, logger, database factory
└── cli/

tests/v1/
├── auth/
│   ├── test_domain/
│   ├── test_use_cases/
│   ├── test_persistence/
│   └── test_presentation/
├── users/
├── servers/
└── operations/
```

**Detalle completo en:** [docs/v1/FOLDER_STRUCTURE.md](docs/v1/FOLDER_STRUCTURE.md)

## 🧩 Principios SOLID

- **S**: Una clase, una responsabilidad
- **O**: Abierto a extensión, cerrado a modificación
- **L**: Sustituible por subtipos
- **I**: Interfaces pequeñas y específicas
- **D**: Depender de abstracciones, no implementaciones

## 🧪 TDD: Patrón de trabajo

1. Escribe un test que falle (RED)
2. Implementa lo mínimo para que pase (GREEN)
3. Refactoriza el código y los tests (REFACTOR)
4. Documenta el avance

## 🧪 Estrategia de Testing

### Unit Tests (Dominio)

- **Entities**: validaciones, comportamiento, invariantes
- **Value Objects**: validaciones, igualdad, inmutabilidad
- **Use Cases**: lógica de negocio, casos de éxito y error
- **Eventos**: creación, serialización, métodos
- **Aislamiento total**: sin dependencias externas (DB, HTTP, etc.)

### Integration Tests (Adaptadores)

- **Repositories**: operaciones CRUD con DB real (test containers)
- **SSH Clients**: conexiones y comandos reales (mock servers)
- **HTTP Clients**: llamadas a APIs externas (mocks/stubs)
- **Cache**: operaciones con Valkey (test containers)
- **Dependencias reales**: verificar contratos con infraestructura

### Contract Tests (Entre Módulos)

- **Eventos**: esquemas versionados entre publishers/consumers
- **Módulo A publica** → **Módulo B consume**: verificar compatibilidad
- **Ejemplo**: `UserRegistered` (auth) → EmailService (notifications)
- **Schemas JSON/Pydantic**: validar estructura de eventos
- **Versionado**: eventos v1, v2 coexisten (backward compatibility)

### E2E Tests (API Completa)

- **Flujos completos**: registro → login → operación SSH
- **Base de datos**: limpiar entre tests
- **Endpoints protegidos**: autenticación real
- **Casos de usuario**: historias end-to-end

### Pirámide de Testing

```bash
        /\
       /E2E\        (pocos, lentos, caros)
      /------\
     /Contract\     (medianos, rápidos)
    /----------\
   /Integration\   (algunos, moderados)
  /--------------\
 /   Unit Tests  \ (muchos, rápidos, baratos)
/------------------\
```

**Proporción recomendada**: 70% unit, 20% integration, 8% contract, 2% E2E

## 📚 Reglas de oro

- No mezclar lógica de negocio con infraestructura
- No escribir código sin test
- Cada función debe ser pequeña y tener un propósito claro
- Validaciones y lógica de negocio en el dominio
- Infraestructura solo para persistencia y adaptadores externos

## 📝 Ejemplo de flujo para un nuevo módulo

1. **Documentar requisitos y ADRs**
2. **Definir openapi.yaml**
3. **Escribir tests de casos de uso**
4. **Implementar función a función (pidiendo permiso antes de cada una)**
5. **Refactorizar y documentar**

---

**¿Dudas? Consulta este documento antes de empezar cualquier feature.**
