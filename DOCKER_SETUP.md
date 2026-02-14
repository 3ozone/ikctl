# Docker Setup - Referencia Rápida

📖 **Documentación completa en:** [docs/docker/SETUP.md](docs/docker/SETUP.md)

## Inicio Rápido

```bash
# 1. Configurar entorno
cp .env.example .env

# 2. Levantar servicios
docker-compose up -d

# 3. Verificar
docker-compose ps
```

**Acceso:**

- MariaDB: localhost:3306
- PhpMyAdmin: http://localhost:8080 (usuario: `ikctl_user`, contraseña: `ikctl_pass123`)

**Más detalles en:** [docs/docker/SETUP.md](docs/docker/SETUP.md)
