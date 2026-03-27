#!/bin/bash
# =============================================================================
# Script: configurar_cloud_scheduler.sh
# Proyecto: ADE - Atlas de Datos Estadisticos
# Descripcion: Configura Cloud Scheduler y Cloud Run Jobs en GCP para
#              automatizar la ejecucion mensual del proceso de cifras control.
#
# Arquitectura de automatizacion:
#   Cloud Scheduler (ultimo dia del mes, 23:00 CST)
#       --> Publica mensaje en Pub/Sub
#           --> Cloud Run Job: preparar_entorno (crea esquema insumos_aaaamm)
#           --> Cloud Run Job: pipeline_cifras_control (Dataflow)
#           --> Cloud Run Job: notificar_discrepancias (Gmail API)
#
# Prerequisitos:
#   - gcloud CLI instalado y autenticado
#   - APIs habilitadas: Cloud Scheduler, Cloud Run, Dataflow, Pub/Sub
#   - Service Account con roles necesarios
#
# Uso:
#   chmod +x configurar_cloud_scheduler.sh
#   ./configurar_cloud_scheduler.sh
#
# Autor: Equipo ADE / Exelixi
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# VARIABLES DE CONFIGURACION - Ajustar segun el proyecto GCP
# ---------------------------------------------------------------------------
PROJECT_ID="${GCP_PROJECT_ID:-mi-proyecto-ade}"
REGION="${GCP_REGION:-us-central1}"
TIMEZONE="America/Mexico_City"

# Cloud Run Job - Preparar Entorno
JOB_PREPARAR="ade-preparar-entorno-mensual"
IMAGE_PREPARAR="gcr.io/${PROJECT_ID}/ade-preparar-entorno:latest"

# Cloud Run Job - Pipeline Dataflow
JOB_PIPELINE="ade-pipeline-cifras-control"
IMAGE_PIPELINE="gcr.io/${PROJECT_ID}/ade-pipeline-cifras:latest"

# Cloud Run Job - Notificaciones Gmail
JOB_NOTIFICAR="ade-notificar-discrepancias"
IMAGE_NOTIFICAR="gcr.io/${PROJECT_ID}/ade-notificaciones:latest"

# Service Account para los jobs
SA_EMAIL="ade-dataflow-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Bucket GCS donde Elias deposita el CSV de control
GCS_BUCKET="gs://ade-cifras-control-bucket"

# Nombre del job de Cloud Scheduler
SCHEDULER_JOB_PREPARAR="ade-preparar-entorno-fin-de-mes"
SCHEDULER_JOB_PIPELINE="ade-ejecutar-cifras-control"

# ---------------------------------------------------------------------------
# COLORES PARA OUTPUT
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ---------------------------------------------------------------------------
# PASO 1: Verificar autenticacion y proyecto activo
# ---------------------------------------------------------------------------
log_info "Verificando configuracion de gcloud..."
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ "${CURRENT_PROJECT}" != "${PROJECT_ID}" ]; then
    log_warning "Proyecto activo: '${CURRENT_PROJECT}'. Cambiando a '${PROJECT_ID}'..."
    gcloud config set project "${PROJECT_ID}"
fi
log_success "Proyecto configurado: ${PROJECT_ID}"

# ---------------------------------------------------------------------------
# PASO 2: Habilitar APIs necesarias
# ---------------------------------------------------------------------------
log_info "Habilitando APIs de GCP necesarias..."
gcloud services enable \
    cloudscheduler.googleapis.com \
    run.googleapis.com \
    dataflow.googleapis.com \
    pubsub.googleapis.com \
    secretmanager.googleapis.com \
    sqladmin.googleapis.com \
    --project="${PROJECT_ID}" \
    --quiet

log_success "APIs habilitadas correctamente."

# ---------------------------------------------------------------------------
# PASO 3: Crear Service Account si no existe
# ---------------------------------------------------------------------------
log_info "Verificando Service Account: ${SA_EMAIL}..."
if ! gcloud iam service-accounts describe "${SA_EMAIL}" \
    --project="${PROJECT_ID}" &>/dev/null; then

    log_info "Creando Service Account..."
    gcloud iam service-accounts create "ade-dataflow-sa" \
        --display-name="ADE Dataflow Service Account" \
        --description="SA para pipelines de Dataflow y Cloud Run del proyecto ADE" \
        --project="${PROJECT_ID}"

    log_success "Service Account creado: ${SA_EMAIL}"
else
    log_success "Service Account ya existe: ${SA_EMAIL}"
fi

# Asignar roles necesarios al Service Account
log_info "Asignando roles IAM al Service Account..."
ROLES=(
    "roles/dataflow.worker"
    "roles/dataflow.developer"
    "roles/storage.objectAdmin"
    "roles/cloudsql.client"
    "roles/secretmanager.secretAccessor"
    "roles/run.invoker"
    "roles/logging.logWriter"
    "roles/monitoring.metricWriter"
)

for ROLE in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="${ROLE}" \
        --quiet 2>/dev/null || log_warning "No se pudo asignar ${ROLE} (puede ya existir)"
done
log_success "Roles IAM asignados."

# ---------------------------------------------------------------------------
# PASO 4: Crear bucket GCS para el CSV de control
# ---------------------------------------------------------------------------
log_info "Verificando bucket GCS: ${GCS_BUCKET}..."
if ! gsutil ls "${GCS_BUCKET}" &>/dev/null; then
    gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "${GCS_BUCKET}"
    log_success "Bucket creado: ${GCS_BUCKET}"
else
    log_success "Bucket ya existe: ${GCS_BUCKET}"
fi

# Crear carpetas de trabajo en el bucket
gsutil -q cp /dev/null "${GCS_BUCKET}/cifras_control/.keep" 2>/dev/null || true
gsutil -q cp /dev/null "${GCS_BUCKET}/tmp/.keep" 2>/dev/null || true
gsutil -q cp /dev/null "${GCS_BUCKET}/staging/.keep" 2>/dev/null || true
log_success "Estructura de carpetas en GCS lista."

# ---------------------------------------------------------------------------
# PASO 5: Crear Cloud Run Job - Preparar Entorno
# El job ejecuta 02_preparar_entorno.py para crear el esquema insumos_aaaamm
# ---------------------------------------------------------------------------
log_info "Creando/actualizando Cloud Run Job: ${JOB_PREPARAR}..."

gcloud run jobs create "${JOB_PREPARAR}" \
    --image="${IMAGE_PREPARAR}" \
    --region="${REGION}" \
    --service-account="${SA_EMAIL}" \
    --set-env-vars="DB_HOST=127.0.0.1,DB_PORT=5432,DB_NAME=ade_bd,DB_USER=ade_user,DB_SSLMODE=require" \
    --set-secrets="DB_PASSWORD=ade-db-password:latest" \
    --max-retries=3 \
    --task-timeout=300 \
    --memory=512Mi \
    --cpu=1 \
    --project="${PROJECT_ID}" \
    --quiet 2>/dev/null || \
gcloud run jobs update "${JOB_PREPARAR}" \
    --image="${IMAGE_PREPARAR}" \
    --region="${REGION}" \
    --service-account="${SA_EMAIL}" \
    --set-env-vars="DB_HOST=127.0.0.1,DB_PORT=5432,DB_NAME=ade_bd,DB_USER=ade_user,DB_SSLMODE=require" \
    --set-secrets="DB_PASSWORD=ade-db-password:latest" \
    --max-retries=3 \
    --task-timeout=300 \
    --memory=512Mi \
    --cpu=1 \
    --project="${PROJECT_ID}" \
    --quiet

log_success "Cloud Run Job '${JOB_PREPARAR}' configurado."

# ---------------------------------------------------------------------------
# PASO 6: Crear Cloud Run Job - Pipeline Cifras Control (Dataflow)
# ---------------------------------------------------------------------------
log_info "Creando/actualizando Cloud Run Job: ${JOB_PIPELINE}..."

# El CSV se busca con el patron cifras_AAAAMM.csv en GCS
# La fecha se inyecta dinamicamente en el entrypoint del contenedor
gcloud run jobs create "${JOB_PIPELINE}" \
    --image="${IMAGE_PIPELINE}" \
    --region="${REGION}" \
    --service-account="${SA_EMAIL}" \
    --set-env-vars="\
GCP_PROJECT=${PROJECT_ID},\
GCP_REGION=${REGION},\
GCS_BUCKET=${GCS_BUCKET},\
DB_HOST=127.0.0.1,\
DB_PORT=5432,\
DB_NAME=ade_bd,\
DB_USER=ade_user,\
DB_SSLMODE=require,\
DATAFLOW_RUNNER=DataflowRunner" \
    --set-secrets="DB_PASSWORD=ade-db-password:latest" \
    --max-retries=2 \
    --task-timeout=3600 \
    --memory=1Gi \
    --cpu=2 \
    --project="${PROJECT_ID}" \
    --quiet 2>/dev/null || \
gcloud run jobs update "${JOB_PIPELINE}" \
    --image="${IMAGE_PIPELINE}" \
    --region="${REGION}" \
    --service-account="${SA_EMAIL}" \
    --set-env-vars="\
GCP_PROJECT=${PROJECT_ID},\
GCP_REGION=${REGION},\
GCS_BUCKET=${GCS_BUCKET},\
DB_HOST=127.0.0.1,\
DB_PORT=5432,\
DB_NAME=ade_bd,\
DB_USER=ade_user,\
DB_SSLMODE=require,\
DATAFLOW_RUNNER=DataflowRunner" \
    --set-secrets="DB_PASSWORD=ade-db-password:latest" \
    --max-retries=2 \
    --task-timeout=3600 \
    --memory=1Gi \
    --cpu=2 \
    --project="${PROJECT_ID}" \
    --quiet

log_success "Cloud Run Job '${JOB_PIPELINE}' configurado."

# ---------------------------------------------------------------------------
# PASO 7: Crear Cloud Run Job - Notificaciones Gmail
# ---------------------------------------------------------------------------
log_info "Creando/actualizando Cloud Run Job: ${JOB_NOTIFICAR}..."

gcloud run jobs create "${JOB_NOTIFICAR}" \
    --image="${IMAGE_NOTIFICAR}" \
    --region="${REGION}" \
    --service-account="${SA_EMAIL}" \
    --set-env-vars="\
DB_HOST=127.0.0.1,\
DB_PORT=5432,\
DB_NAME=ade_bd,\
DB_USER=ade_user,\
DB_SSLMODE=require,\
GMAIL_DESTINATARIO=elias.marcelo@segurosatlas.com.mx,\
GMAIL_REMITENTE=ade-notificaciones@segurosatlas.com.mx" \
    --set-secrets="\
DB_PASSWORD=ade-db-password:latest,\
GMAIL_CREDENTIALS=ade-gmail-credentials:latest" \
    --max-retries=2 \
    --task-timeout=300 \
    --memory=512Mi \
    --cpu=1 \
    --project="${PROJECT_ID}" \
    --quiet 2>/dev/null || \
gcloud run jobs update "${JOB_NOTIFICAR}" \
    --image="${IMAGE_NOTIFICAR}" \
    --region="${REGION}" \
    --service-account="${SA_EMAIL}" \
    --set-env-vars="\
DB_HOST=127.0.0.1,\
DB_PORT=5432,\
DB_NAME=ade_bd,\
DB_USER=ade_user,\
DB_SSLMODE=require,\
GMAIL_DESTINATARIO=elias.marcelo@segurosatlas.com.mx,\
GMAIL_REMITENTE=ade-notificaciones@segurosatlas.com.mx" \
    --set-secrets="\
DB_PASSWORD=ade-db-password:latest,\
GMAIL_CREDENTIALS=ade-gmail-credentials:latest" \
    --max-retries=2 \
    --task-timeout=300 \
    --memory=512Mi \
    --cpu=1 \
    --project="${PROJECT_ID}" \
    --quiet

log_success "Cloud Run Job '${JOB_NOTIFICAR}' configurado."

# ---------------------------------------------------------------------------
# PASO 8: Crear jobs de Cloud Scheduler
#
# PROGRAMACION:
#   - Preparar entorno: Ultimo dia del mes a las 23:00 CST
#     Expresion cron: "0 23 28-31 * *"
#     Nota: Cloud Scheduler no tiene soporte nativo para "ultimo dia del mes".
#     La solucion estandar es usar "28-31 * *" y validar en el script
#     si es el ultimo dia del mes. El Cloud Run Job hace esta validacion.
#
#   - Pipeline cifras control: Primer dia del mes siguiente a las 08:00 CST
#     (despues de que Elias deposita el CSV con los datos de SIISA)
#     Expresion cron: "0 8 1 * *"
# ---------------------------------------------------------------------------

log_info "Configurando Cloud Scheduler - Preparar Entorno..."

# Job 1: Preparar entorno (ultimo dia del mes a las 23:00 CST)
gcloud scheduler jobs create http "${SCHEDULER_JOB_PREPARAR}" \
    --location="${REGION}" \
    --schedule="0 23 28-31 * *" \
    --time-zone="${TIMEZONE}" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_PREPARAR}:run" \
    --message-body="{}" \
    --oauth-service-account-email="${SA_EMAIL}" \
    --description="ADE: Crea el esquema insumos_aaaamm en PostgreSQL el ultimo dia del mes" \
    --attempt-deadline=600s \
    --max-retry-attempts=3 \
    --min-backoff=30s \
    --max-backoff=300s \
    --project="${PROJECT_ID}" \
    --quiet 2>/dev/null || \
gcloud scheduler jobs update http "${SCHEDULER_JOB_PREPARAR}" \
    --location="${REGION}" \
    --schedule="0 23 28-31 * *" \
    --time-zone="${TIMEZONE}" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_PREPARAR}:run" \
    --message-body="{}" \
    --oauth-service-account-email="${SA_EMAIL}" \
    --description="ADE: Crea el esquema insumos_aaaamm en PostgreSQL el ultimo dia del mes" \
    --attempt-deadline=600s \
    --project="${PROJECT_ID}" \
    --quiet

log_success "Cloud Scheduler '${SCHEDULER_JOB_PREPARAR}' configurado."
log_info "  Programacion: 0 23 28-31 * * (${TIMEZONE})"
log_info "  Nota: El Cloud Run Job valida si es el ultimo dia del mes antes de ejecutar."

# Job 2: Pipeline de cifras control (primer dia del mes a las 08:00 CST)
log_info "Configurando Cloud Scheduler - Pipeline Cifras Control..."

gcloud scheduler jobs create http "${SCHEDULER_JOB_PIPELINE}" \
    --location="${REGION}" \
    --schedule="0 8 1 * *" \
    --time-zone="${TIMEZONE}" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_PIPELINE}:run" \
    --message-body="{}" \
    --oauth-service-account-email="${SA_EMAIL}" \
    --description="ADE: Ejecuta el pipeline de validacion de cifras control (Dataflow)" \
    --attempt-deadline=3600s \
    --max-retry-attempts=2 \
    --min-backoff=60s \
    --max-backoff=600s \
    --project="${PROJECT_ID}" \
    --quiet 2>/dev/null || \
gcloud scheduler jobs update http "${SCHEDULER_JOB_PIPELINE}" \
    --location="${REGION}" \
    --schedule="0 8 1 * *" \
    --time-zone="${TIMEZONE}" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_PIPELINE}:run" \
    --message-body="{}" \
    --oauth-service-account-email="${SA_EMAIL}" \
    --description="ADE: Ejecuta el pipeline de validacion de cifras control (Dataflow)" \
    --attempt-deadline=3600s \
    --project="${PROJECT_ID}" \
    --quiet

log_success "Cloud Scheduler '${SCHEDULER_JOB_PIPELINE}' configurado."
log_info "  Programacion: 0 8 1 * * (${TIMEZONE}) - Primer dia del mes a las 08:00"

# ---------------------------------------------------------------------------
# PASO 9: Mostrar resumen de la configuracion
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
echo "  RESUMEN DE CONFIGURACION - ADE CIFRAS CONTROL"
echo "============================================================"
echo ""
echo "  Proyecto GCP:    ${PROJECT_ID}"
echo "  Region:          ${REGION}"
echo "  Zona horaria:    ${TIMEZONE}"
echo ""
echo "  Cloud Scheduler Jobs:"
echo "  +-----------------------------------------+------------------+"
echo "  | Job                                     | Programacion     |"
echo "  +-----------------------------------------+------------------+"
printf "  | %-39s | %-16s |\n" "${SCHEDULER_JOB_PREPARAR}" "0 23 28-31 * *"
printf "  | %-39s | %-16s |\n" "${SCHEDULER_JOB_PIPELINE}" "0 8 1 * *"
echo "  +-----------------------------------------+------------------+"
echo ""
echo "  Cloud Run Jobs:"
echo "  - ${JOB_PREPARAR}"
echo "  - ${JOB_PIPELINE}"
echo "  - ${JOB_NOTIFICAR}"
echo ""
echo "  GCS Bucket: ${GCS_BUCKET}"
echo "  Depositar CSV de Elias en: ${GCS_BUCKET}/cifras_control/"
echo ""
echo "  Para ejecutar manualmente el preparar entorno:"
echo "  gcloud scheduler jobs run ${SCHEDULER_JOB_PREPARAR} --location=${REGION}"
echo ""
echo "  Para ejecutar manualmente el pipeline:"
echo "  gcloud scheduler jobs run ${SCHEDULER_JOB_PIPELINE} --location=${REGION}"
echo ""
echo "============================================================"
log_success "Configuracion completada exitosamente."
