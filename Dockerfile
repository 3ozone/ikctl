# ============================================================
# Stage 1: builder — instala dependencias con pip
# ============================================================
FROM python:3.13-slim-bookworm AS builder

# Evitar bytecode .pyc y forzar stdout/stderr sin buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Instalar dependencias del sistema necesarias para compilar paquetes nativos
# (cryptography, bcrypt, aiomysql, etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copiar solo requirements para aprovechar la caché de capas
COPY requirements.txt .

# Instalar en un directorio local para copiarlo a la imagen final
RUN pip install --prefix=/install -r requirements.txt

# ============================================================
# Stage 2: runtime — imagen final mínima
# ============================================================
FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Dependencias de sistema en runtime (sin compiladores)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libssl3 \
    libffi8 \
    && rm -rf /var/lib/apt/lists/*

# Copiar paquetes instalados desde el builder
COPY --from=builder /install /usr/local

# Crear usuario sin privilegios para ejecutar la app
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --no-create-home appuser

# Copiar el código de la aplicación
COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup alembic/ ./alembic/
COPY --chown=appuser:appgroup alembic.ini ./alembic.ini
COPY --chown=appuser:appgroup main.py ./main.py

USER appuser

EXPOSE 8089

# Usar sh -c para permitir variable de entorno FASTAPI_PORT
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8089"]
