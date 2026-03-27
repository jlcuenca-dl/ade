# ══════════════════════════════════════════════════
# Dockerfile — ADE Backend (Multi-stage Build)
# Proyecto: Atlas de Datos Estadísticos
# Mantenido por: jlcuenca@datalum.mx
# ══════════════════════════════════════════════════

# ── Stage 1: Builder ──────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Instalar dependencias de compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear virtualenv aislado
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Runtime ──────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Solo instalar libpq runtime (no dev headers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copiar virtualenv del builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copiar código de la aplicación
COPY . .

# Puerto por defecto de Cloud Run
EXPOSE 8080

# Healthcheck interno
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Ejecutar con uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
