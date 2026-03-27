# ADE — Atlas de Datos Estadísticos

> Sistema de análisis y visualización de datos estadísticos.

## 🏗️ Stack Tecnológico

| Componente | Tecnología |
|:-----------|:-----------|
| **Backend** | Python 3.11 · FastAPI · SQLAlchemy |
| **Repositorio** | [GitHub - jlcuenca-dl/ade](https://github.com/jlcuenca-dl/ade.git) |
| **Base de Datos** | PostgreSQL 15 (Cloud SQL) |
| **Contenedores** | Docker · Multi-stage builds |
| **IaC** | Terraform (módulos reutilizables) |
| **CI/CD** | Cloud Build + GitHub Triggers |
| **Cloud** | Google Cloud Platform (Cloud Run) |

## 🚀 Quick Start (Local)

```bash
# 1. Clonar y configurar
cp .env.example .env

# 2. Levantar servicios
docker-compose up --build

# 3. Verificar
curl http://localhost:8080/health
# → {"status":"ok","env":"local","version":"0.1.0"}
```

### URLs Locales
| Servicio | URL |
|:---------|:----|
| API Backend | http://localhost:8080 |
| Swagger Docs | http://localhost:8080/docs |
| PostgreSQL | localhost:5432 |
| pgAdmin (opcional) | http://localhost:5050 |

Para levantar pgAdmin:
```bash
docker-compose --profile tools up --build
```

## 📁 Estructura del Proyecto

```
ade/
├── main.py                    # FastAPI entry point
├── requirements.txt           # Dependencias Python
├── Dockerfile                 # Multi-stage build
├── docker-compose.yml         # Dev local
├── cloudbuild.yaml            # CI/CD pipeline
├── .dockerignore / .gitignore
├── .env.example               # Template de variables
│
├── api/                       # Módulo backend
│   └── __init__.py
│
├── scripts/
│   └── init-db.sql            # Seed PostgreSQL
│
└── infra/                     # Terraform IaC
    ├── modules/
    │   ├── cloudrun/          # Módulo Cloud Run
    │   └── cloudsql/          # Módulo Cloud SQL
    └── envs/
        ├── desa/              # Ambiente desarrollo
        ├── qa/                # Ambiente pruebas
        └── prod/              # Ambiente producción
```

## 🌍 Ambientes

| Ambiente | Proyecto GCP | Cloud SQL | Cloud Run |
|:---------|:-------------|:----------|:----------|
| **DESA** | `atlas-datos-estadisticos-desa` | db-f1-micro | 1 vCPU / 512Mi |
| **QA** | `atlas-datos-estadisticos-qa` | db-g1-small | 1 vCPU / 1024Mi |
| **PROD** | `atlas-datos-estadisticos-prod` | db-custom-2-3840 | 2 vCPU / 2048Mi |

## 🔄 CI/CD (Cloud Build)

| Rama Git | Ambiente | Trigger |
|:---------|:---------|:--------|
| `develop` | DESA | Auto |
| `release/*` | QA | Auto |
| `main` | PROD | Auto |

## 📝 Documentación

- [Plan de Ambientes](./PLAN_AMBIENTES_ADE.md) — Estrategia multi-entorno
- [Bitácora de Avance](./docs/BITACORA.md) — Registro cronológico del Sprint 1
- [Guía de Terraform](./docs/TERRAFORM.md) — Uso de módulos IaC
- [Guía de Docker](./docs/DOCKER.md) — Contenedores y desarrollo local

## 👤 Contacto

**Mantenido por:** jlcuenca@datalum.mx — Datalum Analytics
