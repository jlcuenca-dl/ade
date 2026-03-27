-- =============================================================================
-- SCRIPT: 01_crear_esquema_insumos.sql
-- PROYECTO: ADE - Atlas de Datos Estadisticos
-- DESCRIPCION: Crea dinamicamente el esquema insumos_aaaamm y la tabla
--              cifras_control para el mes y anio de ejecucion.
-- AUTOR: Equipo ADE / Exelixi
-- FECHA: Generado automaticamente en tiempo de ejecucion
-- =============================================================================
-- USO:
--   Este script se ejecuta via psql pasando las variables como parametros:
--   psql -v anio=$(date +%Y) -v mes=$(date +%m) -f 01_crear_esquema_insumos.sql
--
--   O bien, se invoca desde el script Python de automatizacion que construye
--   el nombre del esquema dinamicamente antes de ejecutar el DDL.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- PASO 1: Construccion dinamica del nombre del esquema
-- Se usa DO $$ ... $$ para ejecutar PL/pgSQL anonimo que permite
-- construir y ejecutar DDL con nombres dinamicos via EXECUTE.
-- -----------------------------------------------------------------------------
DO $$
DECLARE
    v_anio      TEXT;
    v_mes       TEXT;
    v_esquema   TEXT;
    v_sql       TEXT;
BEGIN
    -- Obtener anio y mes actuales con formato de 4 y 2 digitos respectivamente
    v_anio    := TO_CHAR(CURRENT_DATE, 'YYYY');
    v_mes     := TO_CHAR(CURRENT_DATE, 'MM');
    v_esquema := 'insumos_' || v_anio || v_mes;

    RAISE NOTICE 'Iniciando creacion del esquema: %', v_esquema;

    -- -------------------------------------------------------------------------
    -- PASO 2: Crear el esquema si no existe
    -- -------------------------------------------------------------------------
    v_sql := 'CREATE SCHEMA IF NOT EXISTS ' || quote_ident(v_esquema);
    EXECUTE v_sql;
    RAISE NOTICE 'Esquema % creado o ya existente.', v_esquema;

    -- -------------------------------------------------------------------------
    -- PASO 3: Crear la tabla cifras_control dentro del esquema dinamico
    -- Campos segun el proceso COPIA SIISA - ADE:
    --   database   : Base de datos de origen (ej. atlas, dwh, datastage)
    --   tabla      : Nombre de la tabla copiada (ej. s4_statpol)
    --   unloaded   : Registros extraidos desde SIISA (reportados por Elias)
    --   copied     : Registros contados en PostgreSQL insumos_aaaamm
    --   diferencia : unloaded - copied (debe ser 0 para integridad total)
    -- -------------------------------------------------------------------------
    v_sql := '
        CREATE TABLE IF NOT EXISTS ' || quote_ident(v_esquema) || '.cifras_control (
            id                  SERIAL          PRIMARY KEY,
            database            VARCHAR(100)    NOT NULL,
            tabla               VARCHAR(200)    NOT NULL,
            unloaded            BIGINT          NOT NULL DEFAULT 0,
            copied              BIGINT          NOT NULL DEFAULT 0,
            diferencia          BIGINT          GENERATED ALWAYS AS (unloaded - copied) STORED,
            estatus             VARCHAR(20)     NOT NULL DEFAULT ''PENDIENTE''
                                    CHECK (estatus IN (''PENDIENTE'', ''OK'', ''DISCREPANCIA'')),
            fecha_ejecucion     TIMESTAMP       NOT NULL DEFAULT NOW(),
            pipeline_run_id     VARCHAR(200),
            observaciones       TEXT,
            CONSTRAINT uq_cifras_control_tabla
                UNIQUE (database, tabla)
        )
    ';
    EXECUTE v_sql;
    RAISE NOTICE 'Tabla cifras_control creada en esquema %.', v_esquema;

    -- -------------------------------------------------------------------------
    -- PASO 4: Crear indice para acelerar consultas por estatus y tabla
    -- -------------------------------------------------------------------------
    v_sql := '
        CREATE INDEX IF NOT EXISTS idx_cifras_control_estatus
            ON ' || quote_ident(v_esquema) || '.cifras_control (estatus)
    ';
    EXECUTE v_sql;

    v_sql := '
        CREATE INDEX IF NOT EXISTS idx_cifras_control_diferencia
            ON ' || quote_ident(v_esquema) || '.cifras_control (diferencia)
    ';
    EXECUTE v_sql;

    RAISE NOTICE 'Indices creados correctamente en %.cifras_control.', v_esquema;
    RAISE NOTICE '=== Preparacion del entorno completada para el esquema: % ===', v_esquema;

EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Error al crear el esquema o la tabla: % - %',
            SQLERRM, SQLSTATE;
END;
$$;


-- =============================================================================
-- SCRIPT ALTERNATIVO: Uso con variables psql (para ejecucion manual o CI/CD)
-- Descomentar y usar si se prefiere pasar el nombre del esquema como variable:
--
-- \set esquema 'insumos_' :'anio' :'mes'
-- CREATE SCHEMA IF NOT EXISTS :esquema;
-- CREATE TABLE IF NOT EXISTS :esquema.cifras_control ( ... );
-- =============================================================================
