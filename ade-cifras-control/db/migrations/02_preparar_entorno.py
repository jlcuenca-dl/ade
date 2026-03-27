"""
Script: 02_preparar_entorno.py
Proyecto: ADE - Atlas de Datos Estadisticos
Descripcion: Script Python que crea dinamicamente el esquema insumos_aaaamm
             y la tabla cifras_control en PostgreSQL (GCP Cloud SQL).
             Disenado para ser invocado por Cloud Scheduler o Cloud Functions
             el ultimo dia de cada mes.

Autor: Equipo ADE / Exelixi
"""

import logging
import os
import sys
from datetime import datetime

import psycopg2
from psycopg2 import sql, OperationalError, ProgrammingError

# ---------------------------------------------------------------------------
# Configuracion de logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ade.preparar_entorno")


# ---------------------------------------------------------------------------
# Configuracion de conexion a PostgreSQL
# Se recomienda usar Google Secret Manager en produccion.
# Las variables de entorno se inyectan desde Cloud Run / Cloud Functions.
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "host":     os.environ.get("DB_HOST", "127.0.0.1"),
    "port":     int(os.environ.get("DB_PORT", "5432")),
    "dbname":   os.environ.get("DB_NAME", "ade_bd"),
    "user":     os.environ.get("DB_USER", "ade_user"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "connect_timeout": 10,
    "sslmode":  os.environ.get("DB_SSLMODE", "require"),
}


def obtener_nombre_esquema(fecha: datetime = None) -> str:
    """Construye el nombre del esquema insumos_aaaamm para la fecha dada.

    Args:
        fecha: Objeto datetime. Si es None, usa la fecha actual del sistema.

    Returns:
        Cadena con el nombre del esquema, ej. 'insumos_202603'.
    """
    if fecha is None:
        fecha = datetime.now()
    return f"insumos_{fecha.strftime('%Y%m')}"


def obtener_conexion() -> psycopg2.extensions.connection:
    """Establece y retorna una conexion a PostgreSQL.

    Returns:
        Objeto de conexion psycopg2 activo.

    Raises:
        OperationalError: Si no se puede conectar a la base de datos.
    """
    try:
        logger.info(
            "Conectando a PostgreSQL en %s:%s base de datos '%s'...",
            DB_CONFIG["host"],
            DB_CONFIG["port"],
            DB_CONFIG["dbname"],
        )
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
        logger.info("Conexion establecida correctamente.")
        return conn
    except OperationalError as exc:
        logger.error("No se pudo conectar a PostgreSQL: %s", exc)
        raise


def crear_esquema(conn: psycopg2.extensions.connection, nombre_esquema: str) -> None:
    """Crea el esquema en PostgreSQL si no existe.

    Args:
        conn: Conexion activa a PostgreSQL.
        nombre_esquema: Nombre del esquema a crear (ej. 'insumos_202603').

    Raises:
        ProgrammingError: Si ocurre un error de SQL al crear el esquema.
    """
    try:
        with conn.cursor() as cur:
            # Usar sql.Identifier para evitar inyeccion SQL en nombres de objetos
            query = sql.SQL("CREATE SCHEMA IF NOT EXISTS {esquema}").format(
                esquema=sql.Identifier(nombre_esquema)
            )
            cur.execute(query)
            logger.info("Esquema '%s' creado o ya existente.", nombre_esquema)
    except ProgrammingError as exc:
        logger.error("Error al crear el esquema '%s': %s", nombre_esquema, exc)
        raise


def crear_tabla_cifras_control(
    conn: psycopg2.extensions.connection, nombre_esquema: str
) -> None:
    """Crea la tabla cifras_control dentro del esquema indicado.

    La tabla almacena la conciliacion entre registros extraidos de SIISA
    (unloaded) y los registros efectivamente copiados en PostgreSQL (copied).
    La columna diferencia se calcula como columna generada: unloaded - copied.

    Args:
        conn: Conexion activa a PostgreSQL.
        nombre_esquema: Nombre del esquema donde se creara la tabla.

    Raises:
        ProgrammingError: Si ocurre un error de SQL al crear la tabla.
    """
    try:
        with conn.cursor() as cur:
            # DDL de la tabla cifras_control
            # Nota: psycopg2 sql.SQL no soporta GENERATED ALWAYS directamente
            # en todas las versiones, por eso se construye como texto seguro
            # usando sql.Identifier solo para el nombre del esquema.
            ddl_tabla = sql.SQL("""
                CREATE TABLE IF NOT EXISTS {esquema}.cifras_control (
                    id                  SERIAL          PRIMARY KEY,
                    database            VARCHAR(100)    NOT NULL,
                    tabla               VARCHAR(200)    NOT NULL,
                    unloaded            BIGINT          NOT NULL DEFAULT 0,
                    copied              BIGINT          NOT NULL DEFAULT 0,
                    diferencia          BIGINT
                        GENERATED ALWAYS AS (unloaded - copied) STORED,
                    estatus             VARCHAR(20)     NOT NULL DEFAULT 'PENDIENTE'
                        CHECK (estatus IN ('PENDIENTE', 'OK', 'DISCREPANCIA')),
                    fecha_ejecucion     TIMESTAMP       NOT NULL DEFAULT NOW(),
                    pipeline_run_id     VARCHAR(200),
                    observaciones       TEXT,
                    CONSTRAINT uq_cifras_control_tabla
                        UNIQUE (database, tabla)
                )
            """).format(esquema=sql.Identifier(nombre_esquema))

            cur.execute(ddl_tabla)
            logger.info(
                "Tabla 'cifras_control' creada en esquema '%s'.", nombre_esquema
            )

            # Indices para optimizar consultas de validacion
            idx_estatus = sql.SQL("""
                CREATE INDEX IF NOT EXISTS idx_cifras_control_estatus
                    ON {esquema}.cifras_control (estatus)
            """).format(esquema=sql.Identifier(nombre_esquema))
            cur.execute(idx_estatus)

            idx_diferencia = sql.SQL("""
                CREATE INDEX IF NOT EXISTS idx_cifras_control_diferencia
                    ON {esquema}.cifras_control (diferencia)
            """).format(esquema=sql.Identifier(nombre_esquema))
            cur.execute(idx_diferencia)

            logger.info(
                "Indices creados en '%s.cifras_control'.", nombre_esquema
            )

    except ProgrammingError as exc:
        logger.error(
            "Error al crear la tabla cifras_control en '%s': %s",
            nombre_esquema,
            exc,
        )
        raise


def preparar_entorno(fecha: datetime = None) -> str:
    """Funcion principal: crea el esquema y la tabla cifras_control.

    Orquesta la conexion, creacion de esquema y tabla dentro de una
    transaccion atomica. En caso de error hace rollback completo.

    Args:
        fecha: Fecha de referencia para el nombre del esquema.
               Si es None, usa la fecha actual.

    Returns:
        Nombre del esquema creado (ej. 'insumos_202603').

    Raises:
        Exception: Cualquier error durante la preparacion del entorno.
    """
    nombre_esquema = obtener_nombre_esquema(fecha)
    logger.info(
        "=== Iniciando preparacion del entorno para esquema: %s ===",
        nombre_esquema,
    )

    conn = None
    try:
        conn = obtener_conexion()

        crear_esquema(conn, nombre_esquema)
        crear_tabla_cifras_control(conn, nombre_esquema)

        conn.commit()
        logger.info(
            "=== Entorno preparado exitosamente. Esquema: %s ===",
            nombre_esquema,
        )
        return nombre_esquema

    except Exception as exc:
        if conn:
            conn.rollback()
            logger.warning("Rollback ejecutado por error: %s", exc)
        logger.error("Fallo en la preparacion del entorno: %s", exc)
        raise

    finally:
        if conn:
            conn.close()
            logger.info("Conexion a PostgreSQL cerrada.")


# ---------------------------------------------------------------------------
# Punto de entrada para ejecucion directa o desde Cloud Functions
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        esquema_creado = preparar_entorno()
        print(f"OK: Esquema '{esquema_creado}' listo para recibir la carga mensual.")
        sys.exit(0)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
