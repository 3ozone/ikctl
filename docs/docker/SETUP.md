# Entorno de Desarrollo Local - ikctl

## Requisitos

- Docker Desktop (o Docker + Docker Compose en Linux)
- Git
- Python 3.10+

## Quickstart

### 1. Clonar el repositorio

```bash
git clone https://github.com/3ozone/ikctl.git
cd ikctl
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

### 3. Levantar los servicios

```bash
docker-compose up -d
```

Esto inicia:

- **MariaDB** en `localhost:3306`
- **PhpMyAdmin** en `http://localhost:8080`

### 4. Verificar que todo está funcionando

```bash
docker-compose ps
```

Deberías ver 2 servicios activos: `mariadb` y `phpmyadmin`.

### 5. Conectarse a la base de datos

**PhpMyAdmin:**

- URL: http://localhost:8080
- Usuario: `ikctl_user`
- Contraseña: `ikctl_pass123`

**Terminal (MySQL client):**

```bash
mysql -h localhost -u ikctl_user -p ikctl_db
# Password: ikctl_pass123
```

## Gestion del Entorno

### Detener servicios

```bash
docker-compose down
```

### Detener y limpiar datos (⚠️ borra la BD)

```bash
docker-compose down -v
```

### Ver logs

```bash
docker-compose logs -f mariadb
docker-compose logs -f phpmyadmin
```

### Reiniciar
```bash
docker-compose restart
```

## Configuración del Backend FastAPI

### 1. Crear entorno virtual
```bash
python3 -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno del backend
Crear `.env` en la raíz:
```
DATABASE_URL=mysql+aiomysql://ikctl_user:ikctl_pass123@localhost/ikctl_db
SECRET_KEY=tu-clave-secreta-super-larga
DEBUG=True
```

### 4. Ejecutar migraciones (cuando estén disponibles)
```bash
alembic upgrade head
```

### 5. Iniciar el servidor FastAPI
```bash
uvicorn app.main:app --reload
```

El servidor estará en: http://localhost:8000

## Estructura de Base de Datos

Las siguientes tablas se crean automáticamente en el init:
- `users` - Usuarios registrados
- `refresh_tokens` - Tokens de refresco (JWT)
- `verification_tokens` - Tokens de verificación de email y reset
- `totp_secrets` - Secretos para 2FA
- `login_attempts` - Registro de intentos de login
- `github_accounts` - Integración OAuth GitHub
- `audit_logs` - Auditoría de eventos

## Troubleshooting

### "Cannot connect to MariaDB"
```bash
docker-compose logs mariadb
docker-compose restart mariadb
```

### "Port 3306 already in use"
Cambiar el puerto en `.env`:
```
DB_PORT=3307
```

### "PhpMyAdmin no responde"
```bash
docker-compose restart phpmyadmin
```

## Siguientes Pasos

1. Una vez funcionando con llena, empezar con los tests TDD
2. Implementar las use cases de auth
3. Crear los endpoints FastAPI
4. Validar con Postman o Swagger UI

¡Listo para desarrollar! 🚀
