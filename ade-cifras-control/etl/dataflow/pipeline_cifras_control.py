"""
Script: pipeline_cifras_control.py
Proyecto: ADE - Atlas de Datos Estadisticos
Descripcion: Pipeline de Apache Beam / Google Cloud Dataflow que:
    1. Lee y parsea el archivo CSV de control enviado por Elias (DBA SIISA).
       El CSV contiene: Database, Tabla, Unloaded.
    2. Se conecta al esquema insumos_aaaamm en PostgreSQL y ejecuta un
       COUNT(*) real para cada tabla listada en el CSV (registros Copied).
    3. Inserta o actualiza la tabla cifras_control con los valores de
       Unloaded (SIISA) y Copied (PostgreSQL).
    4. Calcula la diferencia = unloaded - copied (columna generada en BD).
    5. Actualiza el estatus de cada fila: OK si diferencia=0, DISCREPANCIA
       si diferencia != 0.

Ejecucion local (DirectRunner):
    python pipeline_cifras_control.py \
        --runner=DirectRunner \
        --csv_path=gs://ade-bucket/cifras_control/cifras_202603.csv \
        --db_host=127.0.0.1 \
        --db_port=5432 \
        --db_name=ade_bd \
        --db_user=ade_user \
        --db_password=SECRET \
        --anio=2026 \
        --mes=03

Ejecucion en Dataflow (DataflowRunner):
    python pipeline_cifras_control.py \
        --runner=DataflowRunner \
        --project=mi-proyecto-gcp \
        --region=us-central1 \
        --temp_location=gs://ade-bucket/tmp \
        --staging_location=gs://ade-bucket/staging \
        --csv_path=gs://ade-bucket/cifras_control/cifras_202603.csv \
        --db_host=127.0.0.1 \
        --db_port=5432 \
        --db_name=ade_bd \
        --db_user=ade_user \
        --db_password=SECRET \
        --anio=2026 \
        --mes=03

Autor: Equipo ADE / Exelixi
"""

import csv
import io
import logging
import sys
from datetime import datetime
from typing import Dict, Iterator, List, Optional, Tuple

import apache_beam as beam
from apache_beam.io import ReadFromText
from apache_beam.options.pipeline_options import PipelineOptions, SetupOptions

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ade.pipeline_cifras_control")


# ===========================================================================
# OPCIONES PERSONALIZADAS DEL PIPELINE
# ===========================================================================
class AdeOptions(PipelineOptions):
    """Opciones personalizadas para el pipeline ADE Cifras Control.

    Extiende PipelineOptions de Apache Beam para recibir parametros
    especificos del proceso de validacion mensual.
    """

    @classmethod
    def _add_argparse_args(cls, parser):
        parser.add_argument(
            "--csv_path",
            required=True,
            help="Ruta GCS del CSV de control enviado por Elias. "
                 "Ej: gs://ade-bucket/cifras_control/cifras_202603.csv",
        )
        parser.add_argument(
            "--db_host",
            default="127.0.0.1",
            help="Host de PostgreSQL (Cloud SQL o IP privada).",
        )
        parser.add_argument(
            "--db_port",
            default="5432",
            help="Puerto de PostgreSQL.",
        )
        parser.add_argument(
            "--db_name",
            default="ade_bd",
            help="Nombre de la base de datos PostgreSQL.",
        )
        parser.add_argument(
            "--db_user",
            default="ade_user",
            help="Usuario de PostgreSQL.",
        )
        parser.add_argument(
            "--db_password",
            default="",
            help="Password de PostgreSQL. En produccion usar Secret Manager.",
        )
        parser.add_argument(
            "--db_sslmode",
            default="require",
            help="Modo SSL para la conexion PostgreSQL.",
        )
        parser.add_argument(
            "--anio",
            default=None,
            help="Anio del esquema insumos (4 digitos). Ej: 2026. "
                 "Si no se indica, usa el anio actual.",
        )
        parser.add_argument(
            "--mes",
            default=None,
            help="Mes del esquema insumos (2 digitos). Ej: 03. "
                 "Si no se indica, usa el mes actual.",
        )
        parser.add_argument(
            "--pipeline_run_id",
            default=None,
            help="Identificador unico de la ejecucion del pipeline. "
                 "Se genera automaticamente si no se proporciona.",
        )


# ===========================================================================
# FUNCIONES AUXILIARES
# ===========================================================================

def construir_nombre_esquema(anio: Optional[str], mes: Optional[str]) -> str:
    """Construye el nombre del esquema insumos_aaaamm.

    Args:
        anio: Anio en formato 4 digitos. Si es None usa el actual.
        mes: Mes en formato 2 digitos. Si es None usa el actual.

    Returns:
        Nombre del esquema, ej. 'insumos_202603'.
    """
    ahora = datetime.now()
    a = anio if anio else ahora.strftime("%Y")
    m = mes if mes else ahora.strftime("%m")
    return f"insumos_{a}{m}"


def generar_run_id(pipeline_run_id: Optional[str]) -> str:
    """Genera o retorna el identificador de ejecucion del pipeline.

    Args:
        pipeline_run_id: ID proporcionado por el usuario o None.

    Returns:
        Cadena con el ID de ejecucion.
    """
    if pipeline_run_id:
        return pipeline_run_id
    return f"ade_cifras_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


# ===========================================================================
# TRANSFORMS DE APACHE BEAM
# ===========================================================================

class ParsearCSVFn(beam.DoFn):
    """Parsea cada linea del CSV de control enviado por Elias.

    El CSV tiene el siguiente formato (con encabezado):
        Database,Tabla,Unloaded
        atlas,s4_statpol,1500000
        atlas,s00_cat_productos,250
        dwh,dwh_polizas,980000

    Emite diccionarios con las claves: database, tabla, unloaded.
    Las filas con errores de parseo se emiten al tag 'errores'.
    """

    ENCABEZADOS_ESPERADOS = {"database", "tabla", "unloaded"}

    def process(self, linea: str, *args, **kwargs) -> Iterator[Dict]:
        """Procesa una linea del CSV.

        Args:
            linea: Cadena de texto con una fila del CSV.

        Yields:
            Diccionario con database, tabla, unloaded.
            O diccionario de error con la clave '_error'.
        """
        linea = linea.strip()

        # Ignorar lineas vacias
        if not linea:
            return

        try:
            reader = csv.DictReader(
                io.StringIO(linea),
                fieldnames=["database", "tabla", "unloaded"],
            )
            for fila in reader:
                # Ignorar la fila de encabezado si viene en el CSV
                if fila["database"].strip().lower() == "database":
                    return

                database = fila.get("database", "").strip()
                tabla = fila.get("tabla", "").strip()
                unloaded_raw = fila.get("unloaded", "0").strip()

                if not database or not tabla:
                    logger.warning(
                        "Fila con campos vacios ignorada: %s", linea
                    )
                    return

                # Convertir unloaded a entero, manejar valores no numericos
                try:
                    unloaded = int(unloaded_raw.replace(",", ""))
                except ValueError:
                    logger.warning(
                        "Valor no numerico en Unloaded para tabla '%s': '%s'. "
                        "Se asigna 0.",
                        tabla,
                        unloaded_raw,
                    )
                    unloaded = 0

                yield {
                    "database": database,
                    "tabla": tabla,
                    "unloaded": unloaded,
                }

        except Exception as exc:
            logger.error("Error al parsear linea CSV '%s': %s", linea, exc)
            yield {"_error": str(exc), "_linea": linea}


class ContarRegistrosPostgresFn(beam.DoFn):
    """Ejecuta COUNT(*) en PostgreSQL para cada tabla del CSV.

    Para cada elemento recibido (database, tabla, unloaded), se conecta
    al esquema insumos_aaaamm y ejecuta SELECT COUNT(*) FROM tabla.
    El resultado se agrega al diccionario como 'copied'.

    Nota: En Dataflow, cada worker puede ejecutar multiples instancias
    de este DoFn. La conexion se abre en setup() y se cierra en teardown()
    para reutilizarla entre elementos del mismo bundle.
    """

    def __init__(
        self,
        db_host: str,
        db_port: str,
        db_name: str,
        db_user: str,
        db_password: str,
        db_sslmode: str,
        nombre_esquema: str,
        pipeline_run_id: str,
    ):
        """Inicializa el DoFn con los parametros de conexion.

        Args:
            db_host: Host de PostgreSQL.
            db_port: Puerto de PostgreSQL.
            db_name: Nombre de la base de datos.
            db_user: Usuario de PostgreSQL.
            db_password: Password de PostgreSQL.
            db_sslmode: Modo SSL.
            nombre_esquema: Esquema insumos_aaaamm donde buscar las tablas.
            pipeline_run_id: ID de la ejecucion del pipeline para auditoria.
        """
        self._db_host = db_host
        self._db_port = db_port
        self._db_name = db_name
        self._db_user = db_user
        self._db_password = db_password
        self._db_sslmode = db_sslmode
        self._nombre_esquema = nombre_esquema
        self._pipeline_run_id = pipeline_run_id
        self._conn = None

    def setup(self):
        """Abre la conexion a PostgreSQL al iniciar el bundle."""
        import psycopg2

        try:
            self._conn = psycopg2.connect(
                host=self._db_host,
                port=int(self._db_port),
                dbname=self._db_name,
                user=self._db_user,
                password=self._db_password,
                connect_timeout=15,
                sslmode=self._db_sslmode,
            )
            self._conn.autocommit = True
            logger.info(
                "[ContarRegistros] Conexion a PostgreSQL establecida. "
                "Esquema: %s",
                self._nombre_esquema,
            )
        except Exception as exc:
            logger.error(
                "[ContarRegistros] No se pudo conectar a PostgreSQL: %s", exc
            )
            raise

    def teardown(self):
        """Cierra la conexion a PostgreSQL al finalizar el bundle."""
        if self._conn:
            try:
                self._conn.close()
                logger.info("[ContarRegistros] Conexion a PostgreSQL cerrada.")
            except Exception as exc:
                logger.warning(
                    "[ContarRegistros] Error al cerrar conexion: %s", exc
                )

    def process(self, elemento: Dict, *args, **kwargs) -> Iterator[Dict]:
        """Cuenta los registros de la tabla en PostgreSQL.

        Args:
            elemento: Diccionario con database, tabla, unloaded.

        Yields:
            Diccionario enriquecido con el campo 'copied' (COUNT real).
        """
        import psycopg2
        from psycopg2 import sql as pg_sql

        # Ignorar elementos de error provenientes del parseo
        if "_error" in elemento:
            logger.warning(
                "[ContarRegistros] Elemento de error ignorado: %s", elemento
            )
            return

        tabla = elemento["tabla"]
        database = elemento["database"]
        unloaded = elemento["unloaded"]

        try:
            with self._conn.cursor() as cur:
                # Construir query segura con sql.Identifier para evitar
                # inyeccion SQL en nombres de esquema y tabla
                query = pg_sql.SQL(
                    "SELECT COUNT(*) FROM {esquema}.{tabla}"
                ).format(
                    esquema=pg_sql.Identifier(self._nombre_esquema),
                    tabla=pg_sql.Identifier(tabla),
                )
                cur.execute(query)
                resultado = cur.fetchone()
                copied = resultado[0] if resultado else 0

            logger.info(
                "[ContarRegistros] %s.%s -> unloaded=%d, copied=%d",
                self._nombre_esquema,
                tabla,
                unloaded,
                copied,
            )

            yield {
                "database": database,
                "tabla": tabla,
                "unloaded": unloaded,
                "copied": copied,
                "pipeline_run_id": self._pipeline_run_id,
            }

        except psycopg2.errors.UndefinedTable:
            # La tabla no existe en el esquema insumos_aaaamm
            logger.warning(
                "[ContarRegistros] Tabla '%s.%s' no encontrada en PostgreSQL. "
                "Se registra copied=0.",
                self._nombre_esquema,
                tabla,
            )
            yield {
                "database": database,
                "tabla": tabla,
                "unloaded": unloaded,
                "copied": 0,
                "pipeline_run_id": self._pipeline_run_id,
                "observaciones": f"Tabla no encontrada en {self._nombre_esquema}",
            }

        except Exception as exc:
            logger.error(
                "[ContarRegistros] Error al contar registros de '%s.%s': %s",
                self._nombre_esquema,
                tabla,
                exc,
            )
            # Intentar reconectar si la conexion se perdio
            try:
                self.setup()
            except Exception:
                pass
            yield {
                "database": database,
                "tabla": tabla,
                "unloaded": unloaded,
                "copied": 0,
                "pipeline_run_id": self._pipeline_run_id,
                "observaciones": f"Error al contar: {str(exc)[:200]}",
            }


class UpsertCifrasControlFn(beam.DoFn):
    """Inserta o actualiza registros en la tabla cifras_control.

    Usa INSERT ... ON CONFLICT DO UPDATE (upsert) para manejar
    re-ejecuciones del pipeline sin duplicar registros.
    La diferencia (unloaded - copied) es una columna generada en la BD.
    El estatus se actualiza automaticamente segun la diferencia.
    """

    def __init__(
        self,
        db_host: str,
        db_port: str,
        db_name: str,
        db_user: str,
        db_password: str,
        db_sslmode: str,
        nombre_esquema: str,
    ):
        """Inicializa el DoFn con los parametros de conexion.

        Args:
            db_host: Host de PostgreSQL.
            db_port: Puerto de PostgreSQL.
            db_name: Nombre de la base de datos.
            db_user: Usuario de PostgreSQL.
            db_password: Password de PostgreSQL.
            db_sslmode: Modo SSL.
            nombre_esquema: Esquema insumos_aaaamm donde esta cifras_control.
        """
        self._db_host = db_host
        self._db_port = db_port
        self._db_name = db_name
        self._db_user = db_user
        self._db_password = db_password
        self._db_sslmode = db_sslmode
        self._nombre_esquema = nombre_esquema
        self._conn = None

    def setup(self):
        """Abre la conexion a PostgreSQL al iniciar el bundle."""
        import psycopg2

        try:
            self._conn = psycopg2.connect(
                host=self._db_host,
                port=int(self._db_port),
                dbname=self._db_name,
                user=self._db_user,
                password=self._db_password,
                connect_timeout=15,
                sslmode=self._db_sslmode,
            )
            self._conn.autocommit = False
            logger.info(
                "[UpsertCifras] Conexion a PostgreSQL establecida. "
                "Esquema: %s",
                self._nombre_esquema,
            )
        except Exception as exc:
            logger.error(
                "[UpsertCifras] No se pudo conectar a PostgreSQL: %s", exc
            )
            raise

    def teardown(self):
        """Cierra la conexion a PostgreSQL al finalizar el bundle."""
        if self._conn:
            try:
                self._conn.close()
                logger.info("[UpsertCifras] Conexion a PostgreSQL cerrada.")
            except Exception as exc:
                logger.warning(
                    "[UpsertCifras] Error al cerrar conexion: %s", exc
                )

    def process(self, elemento: Dict, *args, **kwargs) -> Iterator[Dict]:
        """Inserta o actualiza un registro en cifras_control.

        La diferencia se calcula como columna generada en PostgreSQL.
        El estatus se determina en Python antes del upsert:
            - 'OK' si unloaded == copied
            - 'DISCREPANCIA' si unloaded != copied

        Args:
            elemento: Diccionario con database, tabla, unloaded, copied,
                      pipeline_run_id y opcionalmente observaciones.

        Yields:
            El mismo elemento enriquecido con el estatus calculado.
        """
        import psycopg2
        from psycopg2 import sql as pg_sql

        if "_error" in elemento:
            return

        database = elemento["database"]
        tabla = elemento["tabla"]
        unloaded = elemento["unloaded"]
        copied = elemento["copied"]
        pipeline_run_id = elemento.get("pipeline_run_id", "")
        observaciones = elemento.get("observaciones", None)

        # Calcular estatus en Python (la diferencia la calcula la BD)
        estatus = "OK" if unloaded == copied else "DISCREPANCIA"

        try:
            with self._conn.cursor() as cur:
                # Upsert: si ya existe el par (database, tabla), actualiza
                upsert_query = pg_sql.SQL("""
                    INSERT INTO {esquema}.cifras_control
                        (database, tabla, unloaded, copied, estatus,
                         fecha_ejecucion, pipeline_run_id, observaciones)
                    VALUES
                        (%s, %s, %s, %s, %s, NOW(), %s, %s)
                    ON CONFLICT ON CONSTRAINT uq_cifras_control_tabla
                    DO UPDATE SET
                        unloaded        = EXCLUDED.unloaded,
                        copied          = EXCLUDED.copied,
                        estatus         = EXCLUDED.estatus,
                        fecha_ejecucion = NOW(),
                        pipeline_run_id = EXCLUDED.pipeline_run_id,
                        observaciones   = EXCLUDED.observaciones
                """).format(esquema=pg_sql.Identifier(self._nombre_esquema))

                cur.execute(
                    upsert_query,
                    (
                        database,
                        tabla,
                        unloaded,
                        copied,
                        estatus,
                        pipeline_run_id,
                        observaciones,
                    ),
                )

            self._conn.commit()
            logger.info(
                "[UpsertCifras] %s.%s -> unloaded=%d, copied=%d, "
                "diferencia=%d, estatus=%s",
                self._nombre_esquema,
                tabla,
                unloaded,
                copied,
                unloaded - copied,
                estatus,
            )

            yield {
                "database": database,
                "tabla": tabla,
                "unloaded": unloaded,
                "copied": copied,
                "diferencia": unloaded - copied,
                "estatus": estatus,
                "pipeline_run_id": pipeline_run_id,
            }

        except Exception as exc:
            self._conn.rollback()
            logger.error(
                "[UpsertCifras] Error al hacer upsert de '%s.%s': %s",
                self._nombre_esquema,
                tabla,
                exc,
            )
            try:
                self.setup()
            except Exception:
                pass
            yield {
                "database": database,
                "tabla": tabla,
                "unloaded": unloaded,
                "copied": copied,
                "diferencia": unloaded - copied,
                "estatus": "DISCREPANCIA",
                "pipeline_run_id": pipeline_run_id,
                "_upsert_error": str(exc),
            }


# ===========================================================================
# FUNCION PRINCIPAL DEL PIPELINE
# ===========================================================================

def ejecutar_pipeline(argv: List[str] = None) -> List[Dict]:
    """Construye y ejecuta el pipeline de Apache Beam.

    El pipeline realiza las siguientes etapas:
        1. Leer el CSV de control desde GCS.
        2. Parsear cada linea y extraer database, tabla, unloaded.
        3. Contar registros reales en PostgreSQL (copied).
        4. Hacer upsert en cifras_control con los resultados.

    Args:
        argv: Lista de argumentos de linea de comandos. Si es None,
              usa sys.argv.

    Returns:
        Lista de diccionarios con los resultados del pipeline
        (solo disponible con DirectRunner).
    """
    pipeline_options = PipelineOptions(argv)
    pipeline_options.view_as(SetupOptions).save_main_session = True
    ade_options = pipeline_options.view_as(AdeOptions)

    # Construir nombre del esquema y run_id
    nombre_esquema = construir_nombre_esquema(
        ade_options.anio, ade_options.mes
    )
    run_id = generar_run_id(ade_options.pipeline_run_id)

    logger.info(
        "=== Iniciando Pipeline ADE Cifras Control ==="
    )
    logger.info("Esquema destino: %s", nombre_esquema)
    logger.info("Pipeline Run ID: %s", run_id)
    logger.info("CSV de entrada: %s", ade_options.csv_path)

    # Parametros de conexion a PostgreSQL
    db_params = dict(
        db_host=ade_options.db_host,
        db_port=ade_options.db_port,
        db_name=ade_options.db_name,
        db_user=ade_options.db_user,
        db_password=ade_options.db_password,
        db_sslmode=ade_options.db_sslmode,
        nombre_esquema=nombre_esquema,
    )

    resultados = []

    with beam.Pipeline(options=pipeline_options) as pipeline:

        # ------------------------------------------------------------------
        # ETAPA 1: Leer el CSV desde GCS (o ruta local en pruebas)
        # ------------------------------------------------------------------
        lineas_csv = (
            pipeline
            | "LeerCSV" >> ReadFromText(
                ade_options.csv_path,
                skip_header_lines=1,   # Omitir encabezado Database,Tabla,Unloaded
            )
        )

        # ------------------------------------------------------------------
        # ETAPA 2: Parsear cada linea del CSV
        # ------------------------------------------------------------------
        registros_csv = (
            lineas_csv
            | "ParsearCSV" >> beam.ParDo(ParsearCSVFn())
            | "FiltrarErroresParseo" >> beam.Filter(
                lambda x: "_error" not in x
            )
        )

        # ------------------------------------------------------------------
        # ETAPA 3: Contar registros reales en PostgreSQL (Copied)
        # ------------------------------------------------------------------
        registros_con_copied = (
            registros_csv
            | "ContarEnPostgres" >> beam.ParDo(
                ContarRegistrosPostgresFn(
                    pipeline_run_id=run_id,
                    **db_params,
                )
            )
        )

        # ------------------------------------------------------------------
        # ETAPA 4: Upsert en cifras_control
        # ------------------------------------------------------------------
        resultados_upsert = (
            registros_con_copied
            | "UpsertCifrasControl" >> beam.ParDo(
                UpsertCifrasControlFn(**db_params)
            )
        )

        # ------------------------------------------------------------------
        # ETAPA 5: Log de resultados (para monitoreo en Dataflow UI)
        # ------------------------------------------------------------------
        _ = (
            resultados_upsert
            | "LogResultados" >> beam.Map(
                lambda r: logger.info(
                    "RESULTADO: database=%s tabla=%s unloaded=%d "
                    "copied=%d diferencia=%d estatus=%s",
                    r.get("database"),
                    r.get("tabla"),
                    r.get("unloaded", 0),
                    r.get("copied", 0),
                    r.get("diferencia", 0),
                    r.get("estatus"),
                )
            )
        )

    logger.info(
        "=== Pipeline ADE Cifras Control finalizado. Run ID: %s ===", run_id
    )
    return resultados


# ===========================================================================
# PUNTO DE ENTRADA
# ===========================================================================
if __name__ == "__main__":
    ejecutar_pipeline(sys.argv)
