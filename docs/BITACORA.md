# Bitácora de Avance — Proyecto ADE (Sprint 1)

## Información General
- **Proyecto:** Atlas de Datos Estadísticos (ADE)
- **Responsable:** jlcuenca@datalum.mx
- **Sprint:** 1
- **Objetivo del Sprint:** Establecer infraestructura base multi-ambiente (DESA/QA/PROD) con Docker y Terraform.

---

## 📅 24 de Marzo, 2026

### Análisis Inicial
- Se analizó el proyecto `atlas-datos-estadisticos-desa` en GCP.
- Se identificó que la cuenta `jlcuenca@solucionesarea.com` no tiene permisos para gestionar este proyecto.
- Se determinó la necesidad de migrar la gestión a la cuenta `jlcuenca@datalum.mx`.
- Se revisaron patrones de despliegue existentes del proyecto hermano `mag-sistema` (FastAPI + Next.js en Cloud Run con Cloud SQL).

### Decisiones Arquitectónicas
| Decisión | Justificación |
|:---------|:-------------|
| **3 proyectos GCP aislados** | Aislamiento de datos y billing independiente por ambiente |
| **Terraform para IaC** | Proyecto en crecimiento requiere infraestructura reproducible |
| **Docker multi-stage** | Imágenes ligeras (~150MB) y paridad entre ambientes |
| **Artifact Registry** | Reemplazo moderno de Container Registry, soporte regional |
| **Cloud Build triggers por rama** | Despliegue automático sin intervención manual |

### Documentación Generada
- ✅ `PLAN_AMBIENTES_ADE.md` — Plan estratégico de ambientes

---

## 📅 27 de Marzo, 2026

### Infraestructura Creada
- ✅ Estructura de directorio completa del proyecto (`ade/`)
- ✅ Módulos Terraform reutilizables:
  - `infra/modules/cloudrun/` — Servicio Cloud Run parametrizable
  - `infra/modules/cloudsql/` — Instancia PostgreSQL con backups
- ✅ Configuraciones por ambiente:
  - `infra/envs/desa/` — db-f1-micro, sin protección de borrado
  - `infra/envs/qa/` — db-g1-small, protección activa
  - `infra/envs/prod/` — db-custom-2-3840, protección activa, 2 vCPU

### Contenerización
- ✅ `Dockerfile` — Multi-stage build (builder + runtime), Python 3.11-slim, healthcheck integrado
- ✅ `docker-compose.yml` — PostgreSQL 15 + Backend FastAPI + pgAdmin (perfil tools)
- ✅ `.dockerignore` — Exclusiones para imagen limpia
- ✅ `scripts/init-db.sql` — Seed inicial con extensión uuid-ossp

### CI/CD
- ✅ `cloudbuild.yaml` — Pipeline parametrizado con sustituciones (`_ENV`, `_CPU`, `_MEMORY`, etc.)
- Pipeline usa Artifact Registry regional (`us-central1-docker.pkg.dev`)

### Aplicación
- ✅ `main.py` — FastAPI entry point con:
  - Endpoint `/health` para monitoreo
  - CORS dinámico según ambiente (local/desa/qa/prod)
- ✅ `requirements.txt` — FastAPI, SQLAlchemy, psycopg2-binary, pydantic

### GCP & Repositorios
- ✅ **Autenticación:** `gcloud auth login jlcuenca@datalum.mx` completada
- ✅ **Repositorio Principal:** [GitHub - jlcuenca-dl/ade](https://github.com/jlcuenca-dl/ade.git) vinculado como `origin`.
- ✅ **Artifact Registry creado:** `ade-repo` (Docker, us-central1)
- ✅ **Proyectos QA/PROD:** Creados en GCP.
- ⚠️ **Pendiente Billing:** Vinculación necesaria para activar APIs en QA/PROD.

### Documentación
- ✅ `README.md` — Quick start, estructura y stack
- ✅ `docs/BITACORA.md` — Registro cronológico (este archivo)
- ✅ `docs/TERRAFORM.md` — Guía de módulos y variables
- ✅ `docs/DOCKER.md` — Guía de contenedores y desarrollo local

### Próximos Pasos
- [ ] 🔴 **Vincular billing** a proyectos QA y PROD (requiere admin de organización)
- [ ] Habilitar APIs en QA y PROD (post-billing)
- [ ] Crear bucket `ade-terraform-state` para state remoto
- [ ] Ejecutar `terraform init` + `terraform plan` en cada ambiente
- [ ] Configurar triggers de Cloud Build por rama
- [ ] Implementar módulo de base de datos (`api/database.py`)
- [ ] Crear modelos SQLAlchemy para entidades estadísticas
- [ ] Preparar datos de seed para QA

---

## 📊 Métricas del Sprint

| Métrica | Valor |
|:--------|:------|
| Archivos creados | 21 |
| Módulos Terraform | 2 (cloudrun, cloudsql) |
| Ambientes configurados | 3 (desa, qa, prod) |
| Proyectos GCP creados | 2 (qa, prod) |
| APIs habilitadas (DESA) | 4 (Run, Build, SQL, Secrets) |
| Servicios en docker-compose | 3 (db, backend, pgadmin) |
| Documentos generados | 5 (README, Plan, Bitácora, Terraform, Docker) |

---
*Actualizado: 27 de marzo de 2026 06:57 CST — Sprint 1 en curso*
