# Guía de Docker — Proyecto ADE

## Arquitectura de Contenedores

El proyecto ADE usa Docker para garantizar paridad entre el ambiente local y los ambientes cloud (DESA/QA/PROD).

```
┌─────────────────────────────────────────────┐
│              docker-compose.yml              │
├──────────┬──────────────┬───────────────────┤
│  db      │  backend     │  pgadmin          │
│  PG:15   │  FastAPI     │  (perfil: tools)  │
│  :5432   │  :8080       │  :5050            │
└──────────┴──────────────┴───────────────────┘
```

## Dockerfile (Multi-stage)

El `Dockerfile` usa dos etapas para minimizar el tamaño de la imagen final:

| Etapa | Base | Propósito | Tamaño aprox. |
|:------|:-----|:----------|:-------------|
| **builder** | python:3.11-slim | Compilar dependencias | ~400MB |
| **runtime** | python:3.11-slim | Solo ejecutar | ~150MB |

### ¿Por qué multi-stage?
- Las dependencias como `psycopg2` requieren `build-essential` y `libpq-dev` para compilar
- En la imagen final solo necesitamos `libpq5` (runtime)
- Reducción de ~60% en tamaño de imagen

## Comandos Frecuentes

### Desarrollo Local
```bash
# Levantar todo
docker-compose up --build

# Levantar en background
docker-compose up -d --build

# Ver logs en tiempo real
docker-compose logs -f backend

# Solo la base de datos
docker-compose up db

# Con pgAdmin para administración visual
docker-compose --profile tools up --build
```

### Depuración
```bash
# Entrar al contenedor del backend
docker-compose exec backend bash

# Conectarse a PostgreSQL desde la terminal
docker-compose exec db psql -U ade_user -d ade

# Ver estado de los contenedores
docker-compose ps

# Reiniciar un servicio
docker-compose restart backend
```

### Limpieza
```bash
# Detener todo
docker-compose down

# Detener y borrar volúmenes (⚠️ borra datos de la BD)
docker-compose down -v

# Rebuild forzado (sin cache)
docker-compose build --no-cache
```

## Variables de Entorno

El `docker-compose.yml` lee variables desde `.env`:

```bash
# Copiar template
cp .env.example .env

# Editar según necesidad
```

| Variable | Default | Descripción |
|:---------|:--------|:------------|
| `DB_PASSWORD` | `ade_local_2026` | Password de PostgreSQL |
| `PGADMIN_PASSWORD` | `admin2026` | Password de pgAdmin |
| `ENV` | `local` | Ambiente de ejecución |

## Hot Reload

El `docker-compose.yml` monta volúmenes locales:
- `./api` → `/app/api`
- `./main.py` → `/app/main.py`

Esto permite que los cambios en el código se reflejen automáticamente (uvicorn `--reload` en desarrollo).

## Build para Cloud

Para construir la imagen que se subirá a Artifact Registry:

```bash
# Build manual
docker build -t ade-backend:latest .

# Tag para Artifact Registry
docker tag ade-backend:latest \
  us-central1-docker.pkg.dev/atlas-datos-estadisticos-qa/ade-repo/ade-backend:qa

# Push
docker push us-central1-docker.pkg.dev/atlas-datos-estadisticos-qa/ade-repo/ade-backend:qa
```

> **Nota:** En producción, Cloud Build se encarga de esto automáticamente via `cloudbuild.yaml`.

---
*Guía mantenida por: jlcuenca@datalum.mx*
