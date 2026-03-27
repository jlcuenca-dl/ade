# ADE - Automatizacion de Cifras Control
## Proyecto Atlas de Datos Estadisticos | Seguros Atlas

---

## Descripcion General

Este modulo automatiza el proceso de **Sincronizacion Mensual y Validacion de Insumos (COPIA SIISA - ADE)** descrito en el Documento Maestro del Proyecto ADE.

El proceso cubre las 4 fases del flujo operativo:

- **Fase 1**: Creacion automatica del esquema `insumos_aaaamm` en PostgreSQL el ultimo dia del mes.
- **Fase 2**: Lectura del CSV de control enviado por Elias (DBA SIISA) y conteo real de registros en PostgreSQL.
- **Fase 3**: Generacion automatica de la tabla `cifras_control` con los campos Unloaded, Copied y Diferencia.
- **Fase 4**: Deteccion de discrepancias y generacion de borrador de correo via Gmail API para notificar al DBA.

---

## Estructura del Proyecto

```
ade-cifras-control/
├── db/
│   └── migrations/
│       ├── 01_crear_esquema_insumos.sql    -- DDL SQL puro (PL/pgSQL dinamico)
│       └── 02_preparar_entorno.py          -- Script Python para crear esquema y tabla
├── etl/
│   └── dataflow/
│       └── pipeline_cifras_control.py      -- Pipeline Apache Beam / Dataflow
├── scheduler/
│   └── configurar_cloud_scheduler.sh       -- Script gcloud para Cloud Scheduler
├── notificaciones/
│   └── generar_borrador_gmail.py           -- Script Gmail API para borradores
├── config/
│   └── requirements.txt                    -- Dependencias Python
└── README.md                               -- Este archivo
```

---

## Parte 1: Scripts de Base de Datos (PostgreSQL)

### Archivo: `db/migrations/01_crear_esquema_insumos.sql`

Script SQL puro con PL/pgSQL anonimo que crea dinamicamente el esquema y la tabla.

**Ejecucion manual via psql:**
```
psql -h 127.0.0.1 -U ade_user -d ade_bd -f db/migrations/01_crear_esquema_insumos.sql
```

**Estructura de la tabla `cifras_control`:**

| Campo           | Tipo         | Descripcion                                      |
|-----------------|--------------|--------------------------------------------------|
| id              | SERIAL PK    | Identificador autoincremental                    |
| database        | VARCHAR(100) | Base de datos de origen (atlas, dwh, datastage)  |
| tabla           | VARCHAR(200) | Nombre de la tabla copiada (s4_statpol, etc.)    |
| unloaded        | BIGINT       | Registros extraidos desde SIISA (reportados por Elias) |
| copied          | BIGINT       | Registros contados en PostgreSQL insumos_aaaamm  |
| diferencia      | BIGINT       | Columna generada: unloaded - copied              |
| estatus         | VARCHAR(20)  | OK / DISCREPANCIA / PENDIENTE                    |
| fecha_ejecucion | TIMESTAMP    | Fecha y hora de la ejecucion del pipeline        |
| pipeline_run_id | VARCHAR(200) | ID de la ejecucion del pipeline para auditoria   |
| observaciones   | TEXT         | Notas adicionales (ej. tabla no encontrada)      |

### Archivo: `db/migrations/02_preparar_entorno.py`

Script Python que invoca el DDL de forma programatica. Disenado para ser ejecutado por Cloud Run Jobs.

**Variables de entorno requeridas:**
```
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=ade_bd
DB_USER=ade_user
DB_PASSWORD=<secreto en Secret Manager>
DB_SSLMODE=require
```

**Ejecucion local:**
```
export DB_HOST=127.0.0.1
export DB_PASSWORD=mi_password
python db/migrations/02_preparar_entorno.py
```

---

## Parte 2: Pipeline de Dataflow (Apache Beam)

### Archivo: `etl/dataflow/pipeline_cifras_control.py`

Pipeline de Apache Beam que implementa las 4 etapas de procesamiento:

1. **LeerCSV**: Lee el archivo CSV desde Google Cloud Storage.
2. **ParsearCSV**: Parsea cada linea y extrae `database`, `tabla`, `unloaded`.
3. **ContarEnPostgres**: Ejecuta `SELECT COUNT(*) FROM esquema.tabla` en PostgreSQL.
4. **UpsertCifrasControl**: Inserta o actualiza `cifras_control` con los resultados.

**Formato del CSV de entrada (enviado por Elias):**
```
Database,Tabla,Unloaded
atlas,s4_statpol,1500000
atlas,s00_cat_productos,250
dwh,dwh_polizas,980000
datastage,ds_emisiones,45000
```

**Ejecucion local (DirectRunner para pruebas):**
```
pip install -r config/requirements.txt

python etl/dataflow/pipeline_cifras_control.py \
    --runner=DirectRunner \
    --csv_path=gs://ade-cifras-control-bucket/cifras_control/cifras_202603.csv \
    --db_host=127.0.0.1 \
    --db_port=5432 \
    --db_name=ade_bd \
    --db_user=ade_user \
    --db_password=MI_PASSWORD \
    --anio=2026 \
    --mes=03
```

**Ejecucion en produccion (DataflowRunner):**
```
python etl/dataflow/pipeline_cifras_control.py \
    --runner=DataflowRunner \
    --project=mi-proyecto-gcp \
    --region=us-central1 \
    --temp_location=gs://ade-cifras-control-bucket/tmp \
    --staging_location=gs://ade-cifras-control-bucket/staging \
    --csv_path=gs://ade-cifras-control-bucket/cifras_control/cifras_202603.csv \
    --db_host=127.0.0.1 \
    --db_port=5432 \
    --db_name=ade_bd \
    --db_user=ade_user \
    --db_password=MI_PASSWORD \
    --anio=2026 \
    --mes=03
```

**Nota sobre la conexion a Cloud SQL desde Dataflow:**
En produccion, usar el Cloud SQL Auth Proxy como sidecar o configurar la IP privada de la instancia Cloud SQL dentro de la VPC del proyecto GCP.

---

## Parte 3: Automatizacion con Cloud Scheduler

### Archivo: `scheduler/configurar_cloud_scheduler.sh`

Script bash que configura toda la infraestructura de automatizacion en GCP.

**Prerequisitos:**
```
gcloud auth login
gcloud config set project MI_PROYECTO_GCP
```

**Ejecucion:**
```
export GCP_PROJECT_ID=mi-proyecto-gcp
export GCP_REGION=us-central1
chmod +x scheduler/configurar_cloud_scheduler.sh
./scheduler/configurar_cloud_scheduler.sh
```

**Programacion de los jobs:**

| Job de Cloud Scheduler              | Expresion Cron  | Zona Horaria         | Descripcion                              |
|-------------------------------------|-----------------|----------------------|------------------------------------------|
| ade-preparar-entorno-fin-de-mes     | 0 23 28-31 * *  | America/Mexico_City  | Crea esquema insumos_aaaamm              |
| ade-ejecutar-cifras-control         | 0 8 1 * *       | America/Mexico_City  | Ejecuta pipeline de validacion           |

**Nota sobre el ultimo dia del mes:**
Cloud Scheduler no soporta nativamente la expresion "ultimo dia del mes". La solucion implementada usa `28-31 * *` y el Cloud Run Job valida internamente si la fecha de ejecucion es el ultimo dia del mes calendario antes de proceder. Esto garantiza que el esquema se cree exactamente el ultimo dia de cada mes.

**Recursos creados por el script:**
- Service Account: `ade-dataflow-sa@PROYECTO.iam.gserviceaccount.com`
- Roles IAM: dataflow.worker, dataflow.developer, storage.objectAdmin, cloudsql.client, secretmanager.secretAccessor
- Bucket GCS: `gs://ade-cifras-control-bucket`
- Cloud Run Jobs: preparar-entorno, pipeline-cifras, notificar-discrepancias
- Cloud Scheduler Jobs: 2 jobs programados

**Ejecucion manual de los jobs:**
```
# Ejecutar preparacion de entorno manualmente
gcloud scheduler jobs run ade-preparar-entorno-fin-de-mes --location=us-central1

# Ejecutar pipeline de cifras control manualmente
gcloud scheduler jobs run ade-ejecutar-cifras-control --location=us-central1
```

---

## Parte 4: Generacion de Borrador de Correo (Gmail API)

### Archivo: `notificaciones/generar_borrador_gmail.py`

Script Python que evalua la tabla `cifras_control` y genera un borrador de correo en Gmail si detecta discrepancias.

**Comportamiento:**
- Si todas las tablas tienen `diferencia = 0`: No genera borrador. Termina con mensaje OK.
- Si alguna tabla tiene `diferencia != 0`: Genera un borrador HTML con tabla de discrepancias dirigido a Elias.
- El borrador **NO se envia automaticamente**. El equipo ADE lo revisa y envia manualmente.

**Configuracion de credenciales Gmail API:**

Opcion A - Desarrollo local (OAuth 2.0):
1. Ir a Google Cloud Console > APIs y Servicios > Credenciales.
2. Crear credenciales OAuth 2.0 de tipo "Aplicacion de escritorio".
3. Descargar el archivo JSON y guardarlo como `credentials.json` en el directorio de trabajo.
4. En la primera ejecucion se abrira el navegador para autorizar el acceso.

Opcion B - Produccion (Service Account con delegacion de dominio):
1. Crear Service Account en GCP.
2. Habilitar delegacion de dominio en Google Workspace Admin.
3. Almacenar las credenciales en Secret Manager como `ade-gmail-credentials`.
4. Inyectar via variable de entorno `GMAIL_CREDENTIALS`.

**Variables de entorno:**
```
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=ade_bd
DB_USER=ade_user
DB_PASSWORD=<secreto>
DB_SSLMODE=require
GMAIL_DESTINATARIO=elias.marcelo@segurosatlas.com.mx
GMAIL_REMITENTE=ade-notificaciones@segurosatlas.com.mx
GMAIL_CC=ramon.balderas@exelixi.com.mx
GMAIL_CREDENTIALS_FILE=credentials.json
```

**Ejecucion:**
```
python notificaciones/generar_borrador_gmail.py \
    --esquema=insumos_202603 \
    --destinatario=elias.marcelo@segurosatlas.com.mx \
    --remitente=ade-notificaciones@segurosatlas.com.mx
```

**Contenido del borrador generado:**
- Asunto: `[ADE] ALERTA: Discrepancias en Cifras Control - Insumos 202603 | N tabla(s) afectada(s)`
- Cuerpo HTML con:
  - Resumen ejecutivo del proceso (total tablas, OK, discrepancias)
  - Tabla detallada con: Database, Tabla, Unloaded, Copied, Diferencia, Observaciones
  - Procedimiento de correccion paso a paso
  - Datos de auditoria (esquema, fecha, pipeline run ID)

---

## Flujo Completo del Proceso Mensual

```
DIA -1 (Ultimo dia del mes, 23:00 CST)
    Cloud Scheduler dispara --> Cloud Run Job: preparar_entorno
        --> Crea esquema insumos_aaaamm en PostgreSQL
        --> Crea tabla cifras_control con indices

DIA 0 (Cierre de SIISA)
    Elias ejecuta extraccion de SIISA
        --> Deposita tablas en esquema insumos_aaaamm
        --> Genera CSV de control: cifras_AAAAMM.csv
        --> Sube CSV a gs://ade-cifras-control-bucket/cifras_control/

DIA 1 (Primer dia del mes, 08:00 CST)
    Cloud Scheduler dispara --> Cloud Run Job: pipeline_cifras_control
        --> Lee CSV de GCS
        --> Parsea: database, tabla, unloaded
        --> Ejecuta COUNT(*) en cada tabla de insumos_aaaamm
        --> Upsert en cifras_control (unloaded, copied, diferencia, estatus)

    Cloud Run Job: notificar_discrepancias
        --> Consulta cifras_control WHERE diferencia <> 0
        --> Si hay discrepancias: Crea borrador en Gmail
        --> Equipo ADE revisa y envia manualmente a Elias

    Si Elias corrige y re-carga:
        --> Re-ejecutar pipeline manualmente
        --> Verificar que diferencia = 0 en todas las tablas
```

---

## Instalacion de Dependencias

```
pip install -r config/requirements.txt
```

---

## Seguridad y Buenas Practicas

- Las contrasenas de base de datos se almacenan en **Google Secret Manager**, nunca en codigo o variables de entorno en texto plano en produccion.
- Las credenciales de Gmail API se almacenan en Secret Manager como `ade-gmail-credentials`.
- Todas las conexiones a PostgreSQL usan `sslmode=require`.
- Los nombres de esquemas y tablas en las queries SQL usan `psycopg2.sql.Identifier` para prevenir inyeccion SQL.
- El pipeline usa `setup()` y `teardown()` en los DoFn para reutilizar conexiones de base de datos entre elementos del mismo bundle, optimizando el uso de recursos.
- Los upserts usan `ON CONFLICT DO UPDATE` para garantizar idempotencia en re-ejecuciones.

---

## Contacto y Soporte

- **Product Owner**: Act. Jose Luis Cuenca Almazan
- **Lider de Desarrollo**: Ing. Ramon Balderas Jimenez (Exelixi)
- **DBA Atlas (SIISA)**: Elias Marcelo Ramirez
- **Canal de soporte**: Slack - Proyecto ADE
