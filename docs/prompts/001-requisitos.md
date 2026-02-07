# Requisitos

Quiero crear una api REST con fastapi para poder instalar aplicaciones en servidores remotos mediante ssh y de forma asíncrona.

## Casos de uso

1. Registro de usuarios
2. Login de usuarios
3. Añadir servidores: Credenciales o ssh key, ips o nombres
4. Probar conectividad
5. Actualizar configuración de servidores (IP, credenciales, puerto)
6. Actualizar perfil de usuario (nombre, contraseña)

## Stack Tecnológico

- **Backend**: FastAPI con asyncssh para conexiones SSH asíncronas
- **Frontend**: Next.js
- **Base de datos**: MariaDB

## Instrucciones para el documento de diseño

Crea un documento de diseño en la carpeta docs/ que incluya:

1. **Arquitectura**: Stack tecnológico del proyecto
2. **Casos de Uso**: Divididos en Funcionales, No Funcionales y de Negocio
3. **Endpoints API**: Organizados por categorías (Usuarios, Servidores, Operaciones)
4. **Modelo de Datos**: Esquema de tablas de MariaDB con sus campos

### Requisitos de formato

- Sé conciso y directo
- Usa formato Markdown válido según markdownlint
- Incluye líneas en blanco alrededor de headings y listas
- Limítate a resolver las necesidades descritas
