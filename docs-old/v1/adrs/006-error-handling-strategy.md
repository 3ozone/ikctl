# ADR-006: Estrategia de Manejo de Errores

**Estado:** ✅ Aceptado  
**Fecha:** 2026-02-21  
**Decisores:** Equipo ikctl  

## Contexto

En una aplicación con Clean Architecture necesitamos una estrategia consistente para manejar errores a través de todas las capas (dominio, casos de uso, infraestructura, presentación).

**Problemas a resolver:**

- ¿Cómo propagamos errores del dominio a la presentación?
- ¿Usamos excepciones tradicionales o patrones funcionales (Result/Either)?
- ¿Cómo mantenemos la separación de concerns y Clean Architecture?
- ¿Cómo evitamos acoplar el dominio con detalles de HTTP?

**Requisitos:**

- Pythonic: idiomático en Python
- Integración con FastAPI (API REST)
- Separación de capas clara
- Testing simple
- Logging estructurado de errores
- Código legible y mantenible

## Decisión

**Usaremos excepciones tradicionales de Python** (`raise`/`try-except`) en todas las capas.

### Jerarquía de Excepciones

```python
# Capa de Dominio (domain/exceptions.py)
class DomainException(Exception):
    """Base para todas las excepciones de dominio."""
    pass

class InvalidEmailError(DomainException):
    """Email con formato inválido."""
    pass

class UserNotFoundError(DomainException):
    """Usuario no existe."""
    pass

# Capa de Infraestructura (infrastructure/exceptions.py)
class InfrastructureException(Exception):
    """Base para excepciones de infraestructura."""
    pass

class DatabaseConnectionError(InfrastructureException):
    """Error de conexión a base de datos."""
    pass

class SSHConnectionError(InfrastructureException):
    """Error de conexión SSH."""
    pass

class EmailServiceError(InfrastructureException):
    """Error al enviar email."""
    pass

# Capa de Aplicación (application/exceptions.py)
class UseCaseException(Exception):
    """Base para excepciones de casos de uso."""
    pass

class UnauthorizedOperationError(UseCaseException):
    """Usuario no autorizado para esta operación."""
    pass

class ResourceNotAvailableError(UseCaseException):
    """Recurso no disponible temporalmente."""
    pass
```

### Propagación de Errores

```python
# Dominio: raise excepciones de validación
class Email:
    def __init__(self, value: str):
        if not self._is_valid(value):
            raise InvalidEmailError(f"Email inválido: {value}")
        self._value = value

# Caso de Uso: propagar o transformar excepciones
class RegisterUser:
    async def execute(self, email: str, password: str) -> User:
        try:
            email_vo = Email(email)  # Puede raise InvalidEmailError
            # ... lógica de negocio
        except UserAlreadyExistsError:
            # Propagar excepciones de dominio tal cual
            raise
        except SomeInfraError as e:
            # Transformar excepciones técnicas si es necesario
            raise UseCaseException("Error al registrar usuario") from e

# Presentación FastAPI: exception handlers
@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    return JSONResponse(
        status_code=400,
        content={"error": exc.__class__.__name__, "message": str(exc)}
    )

@app.exception_handler(UseCaseException)
async def use_case_exception_handler(request: Request, exc: UseCaseException):
    return JSONResponse(
        status_code=422,
        content={"error": exc.__class__.__name__, "message": str(exc)}
    )
```

### Logging de Errores

```python
# Middleware para logging centralizado
@app.middleware("http")
async def log_errors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(
            "Unhandled exception",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "path": request.url.path,
                "method": request.method,
                "user_id": getattr(request.state, "user_id", None)
            },
            exc_info=True
        )
        raise
```

## Alternativas Consideradas

### 1. Result Pattern (con librerías como `returns`)

```python
from returns.result import Result, Success, Failure

def register_user(email: str) -> Result[User, str]:
    if not is_valid_email(email):
        return Failure("Email inválido")
    return Success(User(email))
```

**❌ Rechazado por:**

- No es idiomático en Python (más común en Rust, Haskell, TypeScript)
- Requiere librerías externas (`returns`, `result`)
- Código más verboso: `match`, `unwrap`, `map`
- Equipos Python no familiarizados con el patrón
- FastAPI diseñado para excepciones, no Result
- Complica testing (mock de Success/Failure vs mock de raise)

### 2. Either Pattern (con `pymonad`)

```python
from pymonad.either import Either, Left, Right

def validate_email(email: str) -> Either[str, Email]:
    if not is_valid(email):
        return Left("Email inválido")
    return Right(Email(email))
```

**❌ Rechazado por:**

- Mismas razones que Result Pattern
- pymonad poco mantenido (última release 2019)
- Curva de aprendizaje alta para equipos no funcionales

### 3. Excepciones + Códigos de Error (errno-style)

```python
class DomainError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        super().__init__(message)
```

**❌ Rechazado por:**

- Acoplamiento con códigos numéricos arbitrarios
- Dificulta testing (comparar códigos en vez de tipos)
- Menos explícito que nombres de excepciones

## Consecuencias

### Positivas

✅ **Pythonic**: Idiomático en Python, respeta PEP 8 y convenciones  
✅ **Simplicidad**: No requiere librerías externas ni conceptos funcionales avanzados  
✅ **Integración con FastAPI**: Exception handlers nativos, conversión a HTTP sin boilerplate  
✅ **Testing simple**: `pytest.raises(InvalidEmailError)` es directo y claro  
✅ **Legibilidad**: Código limpio sin `match`, `unwrap`, o `map`  
✅ **Stack traces**: Python proporciona stack traces completos para debugging  
✅ **Jerarquía clara**: Herencia permite capturar grupos de excepciones (`except DomainException`)  
✅ **Ya implementado**: 12 excepciones de dominio en `auth` funcionan sin cambios  

### Negativas

⚠️ **No es type-safe**: Excepciones no se reflejan en los tipos (vs Result que fuerza manejo explícito)  
⚠️ **Posible "happy path bias"**: Fácil olvidar `try-except` (mitigado con linters, tests de casos de error)  
⚠️ **Performance**: `raise` tiene overhead vs `return` (insignificante en operaciones I/O bound)  

### Mitigaciones

- **Linters**: ruff, pylint para detectar excepciones no capturadas
- **Tests exhaustivos**: cada caso de uso debe tener tests de error
- **Documentación**: docstrings con sección `Raises:` en todos los métodos públicos
- **Exception handlers**: registrados centralmente en FastAPI para cobertura completa

## Referencias

- [PEP 3134: Exception Chaining](https://peps.python.org/pep-3134/)
- [FastAPI Exception Handlers](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [Python Exceptions Best Practices](https://docs.python.org/3/tutorial/errors.html)
- ADR-004: Stack de Observabilidad (logging de errores)

## Notas de Implementación

1. **Una excepción por error específico**: `InvalidEmailError`, no `ValidationError("email")`
2. **Mensajes descriptivos**: incluir contexto (valor inválido, razón)
3. **Exception chaining**: usar `raise ... from e` para preservar causas
4. **No capturar Exception genérico**: catch específico o dejar propagar
5. **Logging antes de re-raise**: registrar contexto antes de propagar
