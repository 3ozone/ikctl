# AGENTS.md - Guía de Desarrollo para ikctl

## 🧭 Filosofía de Desarrollo

En ikctl seguimos los principios de:

- **Clean Architecture**: Separación estricta en capas (dominio, aplicación, infraestructura, presentación)
- **SOLID**: 5 principios para código mantenible y extensible
- **DRY** (Don't Repeat Yourself): No repetir lógica ni estructuras
- **KISS** (Keep It Simple, Stupid): Soluciones simples, código claro
- **YAGNI** (You Aren't Gonna Need It): Solo implementamos lo necesario
- **TDD** (Test Driven Development): Primero los tests, luego el código

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

```
app/v1/
├── auth/
│   ├── domain/
│   ├── use_cases/
│   ├── infrastructure/
│   └── presentation/
├── users/
├── servers/
├── operations/
└── shared/

tests/v1/
├── auth/
│   ├── test_use_cases/
│   └── test_domain/
├── users/
├── servers/
└── operations/
```

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
