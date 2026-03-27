# Guía de Terraform — Proyecto ADE

## Arquitectura de Módulos

El proyecto utiliza módulos reutilizables de Terraform para mantener la consistencia entre ambientes.

```
infra/
├── modules/           # Bloques reutilizables
│   ├── cloudrun/      # Despliega un servicio en Cloud Run
│   └── cloudsql/      # Crea instancia PostgreSQL
└── envs/              # Configuración por ambiente
    ├── desa/          # → atlas-datos-estadisticos-desa
    ├── qa/            # → atlas-datos-estadisticos-qa
    └── prod/          # → atlas-datos-estadisticos-prod
```

## Uso Básico

### 1. Requisitos Previos
```bash
# Instalar Terraform
# https://developer.hashicorp.com/terraform/downloads

# Autenticar con GCP
gcloud auth application-default login --account=jlcuenca@datalum.mx
```

### 2. Inicializar un Ambiente
```bash
cd infra/envs/qa
terraform init
```

### 3. Planificar Cambios
```bash
terraform plan -var="db_password=TU_PASSWORD_SEGURO"
```

### 4. Aplicar Cambios
```bash
terraform apply -var="db_password=TU_PASSWORD_SEGURO"
```

### 5. Destruir (solo DESA)
```bash
# ⚠️ NUNCA en QA o PROD sin autorización
cd infra/envs/desa
terraform destroy -var="db_password=TU_PASSWORD"
```

## Variables Sensibles

**Nunca guardar passwords en texto plano.** Opciones seguras:

```bash
# Opción 1: Variable de entorno
export TF_VAR_db_password="mi_password_seguro"
terraform apply

# Opción 2: Archivo .tfvars (NO commitear)
echo 'db_password = "mi_password_seguro"' > terraform.tfvars
terraform apply

# Opción 3: Secret Manager (recomendado para CI/CD)
gcloud secrets create ade-db-password --data-file=- <<< "mi_password_seguro"
```

## Módulo: Cloud Run

### Inputs
| Variable | Tipo | Default | Descripción |
|:---------|:-----|:--------|:------------|
| `project_id` | string | — | ID del proyecto GCP |
| `region` | string | `us-central1` | Región de despliegue |
| `service_name` | string | — | Nombre del servicio |
| `image_uri` | string | — | URI de la imagen Docker |
| `cpu_limit` | string | `"1"` | Límite de CPU |
| `memory_limit` | string | `"512Mi"` | Límite de memoria |
| `env_vars` | map(string) | `{}` | Variables de entorno |
| `allow_unauthenticated` | bool | `false` | Acceso público |

## Módulo: Cloud SQL

### Inputs
| Variable | Tipo | Default | Descripción |
|:---------|:-----|:--------|:------------|
| `project_id` | string | — | ID del proyecto GCP |
| `instance_name` | string | — | Nombre de la instancia |
| `database_version` | string | `POSTGRES_15` | Versión de PostgreSQL |
| `tier` | string | `db-f1-micro` | Machine type |
| `db_name` | string | — | Nombre de la base de datos |
| `db_user` | string | — | Usuario de la BD |
| `db_password` | string | — | Password (sensitive) |
| `deletion_protection` | bool | `true` | Protección contra borrado |

## State Remoto

El estado de Terraform se almacena en un bucket GCS compartido:

```bash
# Crear el bucket (una sola vez)
gsutil mb -p atlas-datos-estadisticos-desa -l us-central1 gs://ade-terraform-state

# Habilitar versionamiento
gsutil versioning set on gs://ade-terraform-state
```

Cada ambiente usa un prefix diferente:
- `envs/desa` → DESA
- `envs/qa` → QA
- `envs/prod` → PROD

---
*Guía mantenida por: jlcuenca@datalum.mx*
