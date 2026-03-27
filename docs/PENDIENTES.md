# Pendientes y Bloqueantes — Proyecto ADE

> [!WARNING]
> Este documento registra los pendientes críticos que requieren acción externa.

---

## 🔴 BLOQUEANTE: Vinculación de Billing a Proyectos QA y PROD

**Fecha de detección:** 27 de marzo de 2026  
**Prioridad:** CRÍTICA — bloquea habilitación de APIs y despliegue  
**Asignado a:** Administrador de Billing de la organización  

### Contexto
Los proyectos `atlas-datos-estadisticos-qa` y `atlas-datos-estadisticos-prod` fueron creados exitosamente, pero no tienen cuenta de facturación vinculada. Sin billing, no se pueden habilitar APIs (Cloud Run, Cloud SQL, etc.) ni desplegar servicios.

### Error Observado
```
ERROR: (gcloud.services.enable) FAILED_PRECONDITION: 
Billing account for project '423870440474' is not found.
Billing must be enabled for activation of service(s)
```

### Datos Requeridos
| Dato | Valor |
|:-----|:------|
| Cuenta de Billing | `01AF6B-5E9E1B-BA612F` |
| Proyecto QA | `atlas-datos-estadisticos-qa` (Project #423870440474) |
| Proyecto PROD | `atlas-datos-estadisticos-prod` |
| Organización | `827583717964` |
| Cuenta solicitante | `jlcuenca@datalum.mx` |
| Permiso faltante | `billing.resourceAssociations.create` |

### Acciones Requeridas del Admin de Billing

**Opción A — Vincular billing directamente (2 comandos):**
```bash
gcloud billing projects link atlas-datos-estadisticos-qa \
  --billing-account=01AF6B-5E9E1B-BA612F

gcloud billing projects link atlas-datos-estadisticos-prod \
  --billing-account=01AF6B-5E9E1B-BA612F
```

**Opción B — Otorgar rol de billing al usuario (permanente):**
```bash
gcloud organizations add-iam-policy-binding 827583717964 \
  --member="user:jlcuenca@datalum.mx" \
  --role="roles/billing.user"
```

**Opción C — Desde la consola web:**
1. Ir a https://console.cloud.google.com/billing
2. Seleccionar la cuenta de billing `01AF6B-5E9E1B-BA612F`
3. En "Mis proyectos" → vincular `atlas-datos-estadisticos-qa` y `atlas-datos-estadisticos-prod`

### Impacto del Bloqueo
Sin billing vinculado NO se puede:
- ❌ Habilitar APIs en QA/PROD (Cloud Run, Cloud SQL, Cloud Build, etc.)
- ❌ Crear instancias de Cloud SQL en QA/PROD
- ❌ Desplegar servicios en Cloud Run QA/PROD
- ❌ Ejecutar `terraform apply` en los ambientes QA/PROD

### Qué SÍ se puede avanzar mientras tanto
- ✅ Desarrollo local con Docker Compose
- ✅ Desarrollo de código backend (modelos, endpoints, lógica)
- ✅ Despliegue en ambiente DESA (ya tiene billing)
- ✅ Pruebas unitarias y de integración locales
- ✅ Configuración de repositorio Git

---
*Registrado: 27 de marzo de 2026 — jlcuenca@datalum.mx*
