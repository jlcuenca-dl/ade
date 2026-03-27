"""
Script: generar_borrador_gmail.py
Proyecto: ADE - Atlas de Datos Estadisticos
Descripcion: Script Python que evalua la tabla cifras_control en PostgreSQL
             y, si detecta tablas con diferencia distinta de 0, genera un
             borrador de correo electronico via Gmail API dirigido a Elias
             (DBA SIISA) con un cuadro resumen de las discrepancias.

             El borrador NO se envia automaticamente. El equipo de base de
             datos de ADE lo revisa, valida y envia de forma manual.

Prerequisitos:
    1. Credenciales OAuth 2.0 de Gmail API descargadas como credentials.json
       (o almacenadas en Secret Manager como 'ade-gmail-credentials').
    2. En la primera ejecucion se genera token.json con el consentimiento
       del usuario. En produccion usar Service Account con delegacion de
       dominio (Google Workspace).
    3. Instalar dependencias:
       pip install google-auth google-auth-oauthlib google-auth-httplib2
                   google-api-python-client psycopg2-binary

Uso:
    python generar_borrador_gmail.py \
        --esquema=insumos_202603 \
        --destinatario=elias.marcelo@segurosatlas.com.mx \
        --remitente=ade-notificaciones@segurosatlas.com.mx

Autor: Equipo ADE / Exelixi
"""

import base64
import json
import logging
import os
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional

import psycopg2
from psycopg2 import sql as pg_sql, OperationalError

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ade.generar_borrador_gmail")


# ===========================================================================
# CONFIGURACION
# ===========================================================================

# Configuracion de PostgreSQL (variables de entorno o valores por defecto)
DB_CONFIG = {
    "host":            os.environ.get("DB_HOST", "127.0.0.1"),
    "port":            int(os.environ.get("DB_PORT", "5432")),
    "dbname":          os.environ.get("DB_NAME", "ade_bd"),
    "user":            os.environ.get("DB_USER", "ade_user"),
    "password":        os.environ.get("DB_PASSWORD", ""),
    "connect_timeout": 10,
    "sslmode":         os.environ.get("DB_SSLMODE", "require"),
}

# Configuracion de Gmail
GMAIL_DESTINATARIO = os.environ.get(
    "GMAIL_DESTINATARIO", "elias.marcelo@segurosatlas.com.mx"
)
GMAIL_REMITENTE = os.environ.get(
    "GMAIL_REMITENTE", "ade-notificaciones@segurosatlas.com.mx"
)
GMAIL_CC = os.environ.get(
    "GMAIL_CC", "ramon.balderas@exelixi.com.mx"
)

# Scopes de Gmail API necesarios para crear borradores
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]

# Ruta al archivo de credenciales OAuth (en produccion usar Secret Manager)
CREDENTIALS_FILE = os.environ.get("GMAIL_CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE = os.environ.get("GMAIL_TOKEN_FILE", "token.json")


# ===========================================================================
# FUNCIONES DE BASE DE DATOS
# ===========================================================================

def obtener_conexion_postgres() -> psycopg2.extensions.connection:
    """Establece y retorna una conexion a PostgreSQL.

    Returns:
        Objeto de conexion psycopg2 activo.

    Raises:
        OperationalError: Si no se puede conectar a la base de datos.
    """
    try:
        logger.info(
            "Conectando a PostgreSQL en %s:%s...",
            DB_CONFIG["host"],
            DB_CONFIG["port"],
        )
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        logger.info("Conexion a PostgreSQL establecida.")
        return conn
    except OperationalError as exc:
        logger.error("No se pudo conectar a PostgreSQL: %s", exc)
        raise


def consultar_discrepancias(
    conn: psycopg2.extensions.connection, nombre_esquema: str
) -> List[Dict]:
    """Consulta la tabla cifras_control y retorna las filas con diferencia != 0.

    Args:
        conn: Conexion activa a PostgreSQL.
        nombre_esquema: Nombre del esquema insumos_aaaamm.

    Returns:
        Lista de diccionarios con las tablas que tienen discrepancias.
        Cada diccionario contiene: database, tabla, unloaded, copied,
        diferencia, estatus, fecha_ejecucion.

    Raises:
        Exception: Si ocurre un error al consultar la base de datos.
    """
    try:
        with conn.cursor() as cur:
            query = pg_sql.SQL("""
                SELECT
                    database,
                    tabla,
                    unloaded,
                    copied,
                    diferencia,
                    estatus,
                    fecha_ejecucion,
                    observaciones
                FROM {esquema}.cifras_control
                WHERE diferencia <> 0
                ORDER BY ABS(diferencia) DESC, tabla ASC
            """).format(esquema=pg_sql.Identifier(nombre_esquema))

            cur.execute(query)
            columnas = [desc[0] for desc in cur.description]
            filas = cur.fetchall()

            discrepancias = [dict(zip(columnas, fila)) for fila in filas]

            logger.info(
                "Consulta completada. Tablas con discrepancias: %d",
                len(discrepancias),
            )
            return discrepancias

    except Exception as exc:
        logger.error(
            "Error al consultar discrepancias en '%s.cifras_control': %s",
            nombre_esquema,
            exc,
        )
        raise


def consultar_resumen_total(
    conn: psycopg2.extensions.connection, nombre_esquema: str
) -> Dict:
    """Consulta el resumen total de la tabla cifras_control.

    Args:
        conn: Conexion activa a PostgreSQL.
        nombre_esquema: Nombre del esquema insumos_aaaamm.

    Returns:
        Diccionario con totales: total_tablas, tablas_ok, tablas_discrepancia,
        total_unloaded, total_copied, total_diferencia.
    """
    try:
        with conn.cursor() as cur:
            query = pg_sql.SQL("""
                SELECT
                    COUNT(*)                                    AS total_tablas,
                    COUNT(*) FILTER (WHERE diferencia = 0)     AS tablas_ok,
                    COUNT(*) FILTER (WHERE diferencia <> 0)    AS tablas_discrepancia,
                    COALESCE(SUM(unloaded), 0)                 AS total_unloaded,
                    COALESCE(SUM(copied), 0)                   AS total_copied,
                    COALESCE(SUM(diferencia), 0)               AS total_diferencia
                FROM {esquema}.cifras_control
            """).format(esquema=pg_sql.Identifier(nombre_esquema))

            cur.execute(query)
            columnas = [desc[0] for desc in cur.description]
            fila = cur.fetchone()
            return dict(zip(columnas, fila)) if fila else {}

    except Exception as exc:
        logger.error("Error al consultar resumen total: %s", exc)
        return {}


# ===========================================================================
# FUNCIONES DE CONSTRUCCION DEL CORREO
# ===========================================================================

def construir_tabla_html(discrepancias: List[Dict]) -> str:
    """Construye una tabla HTML con las discrepancias detectadas.

    Args:
        discrepancias: Lista de diccionarios con las tablas con diferencia != 0.

    Returns:
        Cadena HTML con la tabla de discrepancias formateada.
    """
    filas_html = ""
    for i, fila in enumerate(discrepancias):
        color_fila = "#fff8f8" if i % 2 == 0 else "#ffffff"
        diferencia = fila.get("diferencia", 0)
        color_diferencia = "#cc0000" if diferencia > 0 else "#ff6600"
        observaciones = fila.get("observaciones") or ""

        filas_html += f"""
        <tr style="background-color: {color_fila};">
            <td style="padding: 8px 12px; border: 1px solid #ddd; font-family: monospace;">
                {fila.get('database', '')}
            </td>
            <td style="padding: 8px 12px; border: 1px solid #ddd; font-family: monospace;">
                {fila.get('tabla', '')}
            </td>
            <td style="padding: 8px 12px; border: 1px solid #ddd; text-align: right;">
                {fila.get('unloaded', 0):,}
            </td>
            <td style="padding: 8px 12px; border: 1px solid #ddd; text-align: right;">
                {fila.get('copied', 0):,}
            </td>
            <td style="padding: 8px 12px; border: 1px solid #ddd; text-align: right;
                       font-weight: bold; color: {color_diferencia};">
                {diferencia:,}
            </td>
            <td style="padding: 8px 12px; border: 1px solid #ddd; font-size: 12px;
                       color: #666;">
                {observaciones}
            </td>
        </tr>"""

    tabla_html = f"""
    <table style="border-collapse: collapse; width: 100%; font-size: 13px;
                  font-family: Arial, sans-serif; margin-top: 16px;">
        <thead>
            <tr style="background-color: #1a3a5c; color: white;">
                <th style="padding: 10px 12px; border: 1px solid #ddd;
                           text-align: left;">Database</th>
                <th style="padding: 10px 12px; border: 1px solid #ddd;
                           text-align: left;">Tabla</th>
                <th style="padding: 10px 12px; border: 1px solid #ddd;
                           text-align: right;">Unloaded (SIISA)</th>
                <th style="padding: 10px 12px; border: 1px solid #ddd;
                           text-align: right;">Copied (ADE)</th>
                <th style="padding: 10px 12px; border: 1px solid #ddd;
                           text-align: right;">Diferencia</th>
                <th style="padding: 10px 12px; border: 1px solid #ddd;
                           text-align: left;">Observaciones</th>
            </tr>
        </thead>
        <tbody>
            {filas_html}
        </tbody>
    </table>"""

    return tabla_html


def construir_tabla_texto(discrepancias: List[Dict]) -> str:
    """Construye una tabla en texto plano con las discrepancias.

    Se usa como parte alternativa (plain text) del correo multipart.

    Args:
        discrepancias: Lista de diccionarios con las tablas con diferencia != 0.

    Returns:
        Cadena de texto con la tabla formateada en ASCII.
    """
    separador = "-" * 90
    encabezado = f"{'Database':<15} {'Tabla':<35} {'Unloaded':>12} {'Copied':>12} {'Diferencia':>12}"
    filas = [separador, encabezado, separador]

    for fila in discrepancias:
        linea = (
            f"{fila.get('database', ''):<15} "
            f"{fila.get('tabla', ''):<35} "
            f"{fila.get('unloaded', 0):>12,} "
            f"{fila.get('copied', 0):>12,} "
            f"{fila.get('diferencia', 0):>12,}"
        )
        filas.append(linea)

    filas.append(separador)
    return "\n".join(filas)


def construir_cuerpo_html(
    discrepancias: List[Dict],
    resumen: Dict,
    nombre_esquema: str,
    fecha_ejecucion: str,
) -> str:
    """Construye el cuerpo HTML completo del correo de notificacion.

    Args:
        discrepancias: Lista de tablas con diferencia != 0.
        resumen: Diccionario con totales del proceso.
        nombre_esquema: Nombre del esquema insumos_aaaamm.
        fecha_ejecucion: Fecha y hora de la ejecucion del pipeline.

    Returns:
        Cadena HTML con el cuerpo completo del correo.
    """
    tabla_discrepancias = construir_tabla_html(discrepancias)
    total_tablas = resumen.get("total_tablas", 0)
    tablas_ok = resumen.get("tablas_ok", 0)
    tablas_disc = resumen.get("tablas_discrepancia", 0)
    total_unloaded = resumen.get("total_unloaded", 0)
    total_copied = resumen.get("total_copied", 0)
    total_diferencia = resumen.get("total_diferencia", 0)

    html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; font-size: 14px; color: #333; }}
        .header {{ background-color: #1a3a5c; color: white; padding: 16px 20px;
                   border-radius: 4px 4px 0 0; }}
        .content {{ padding: 20px; border: 1px solid #ddd; border-top: none; }}
        .alerta {{ background-color: #fff3cd; border: 1px solid #ffc107;
                   border-radius: 4px; padding: 12px 16px; margin: 16px 0; }}
        .resumen {{ background-color: #f8f9fa; border: 1px solid #dee2e6;
                    border-radius: 4px; padding: 12px 16px; margin: 16px 0; }}
        .resumen-item {{ display: inline-block; margin: 4px 16px 4px 0; }}
        .badge-ok {{ background-color: #28a745; color: white; padding: 2px 8px;
                     border-radius: 12px; font-size: 12px; }}
        .badge-disc {{ background-color: #dc3545; color: white; padding: 2px 8px;
                       border-radius: 12px; font-size: 12px; }}
        .footer {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid #ddd;
                   font-size: 12px; color: #666; }}
        .instrucciones {{ background-color: #e8f4fd; border-left: 4px solid #1a3a5c;
                          padding: 12px 16px; margin: 16px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h2 style="margin: 0;">ADE - Alerta de Discrepancias en Cifras Control</h2>
        <p style="margin: 4px 0 0 0; font-size: 13px; opacity: 0.85;">
            Proyecto Atlas de Datos Estadisticos | Seguros Atlas
        </p>
    </div>

    <div class="content">
        <p>Estimado Elias,</p>

        <p>El sistema automatizado de validacion del proyecto ADE ha completado
        la revision de la carga mensual del esquema <strong>{nombre_esquema}</strong>
        y ha detectado <strong style="color: #dc3545;">{tablas_disc} tabla(s)
        con discrepancias</strong> entre los registros extraidos de SIISA
        (Unloaded) y los registros copiados en PostgreSQL ADE (Copied).</p>

        <div class="alerta">
            <strong>Accion requerida:</strong> Por favor revisa las tablas listadas
            a continuacion, analiza el origen de la discrepancia en SIISA, purga
            los datos incompletos en el esquema <code>{nombre_esquema}</code> y
            vuelve a ejecutar la extraccion para las tablas afectadas hasta que
            la diferencia sea 0 en todas las tablas.
        </div>

        <div class="resumen">
            <strong>Resumen del proceso - {fecha_ejecucion}</strong><br><br>
            <span class="resumen-item">
                Total de tablas procesadas: <strong>{total_tablas}</strong>
            </span>
            <span class="resumen-item">
                <span class="badge-ok">OK</span> {tablas_ok} tablas sin diferencia
            </span>
            <span class="resumen-item">
                <span class="badge-disc">DISCREPANCIA</span> {tablas_disc} tablas con diferencia
            </span>
            <br><br>
            <span class="resumen-item">
                Total Unloaded (SIISA): <strong>{total_unloaded:,}</strong>
            </span>
            <span class="resumen-item">
                Total Copied (ADE): <strong>{total_copied:,}</strong>
            </span>
            <span class="resumen-item">
                Diferencia total: <strong style="color: #dc3545;">{total_diferencia:,}</strong>
            </span>
        </div>

        <h3 style="color: #1a3a5c;">Tablas con Discrepancias ({tablas_disc})</h3>
        <p style="font-size: 13px; color: #666;">
            La columna <em>Diferencia</em> muestra el resultado de Unloaded menos Copied.
            Un valor positivo indica registros faltantes en ADE.
            Un valor negativo indica registros de mas en ADE.
        </p>

        {tabla_discrepancias}

        <div class="instrucciones">
            <strong>Procedimiento de correccion:</strong>
            <ol style="margin: 8px 0 0 0; padding-left: 20px;">
                <li>Identificar la causa de la discrepancia en el sistema SIISA.</li>
                <li>Purgar los registros incompletos de la tabla afectada en el
                    esquema <code>{nombre_esquema}</code> en PostgreSQL ADE.</li>
                <li>Re-ejecutar la extraccion y copia para las tablas afectadas.</li>
                <li>Notificar al equipo ADE cuando la re-carga este completa.</li>
                <li>El pipeline de validacion se re-ejecutara para confirmar
                    que la diferencia es 0.</li>
            </ol>
        </div>

        <p>Este correo fue generado automaticamente por el sistema ADE.
        <strong>Por favor no responder a este mensaje.</strong>
        Para consultas, contactar al equipo de desarrollo ADE via Slack.</p>

        <div class="footer">
            <p>
                Esquema validado: <code>{nombre_esquema}</code><br>
                Fecha de ejecucion: {fecha_ejecucion}<br>
                Sistema: ADE - Atlas de Datos Estadisticos | Seguros Atlas<br>
                Equipo: Exelixi - Ing. Ramon Balderas Jimenez
            </p>
        </div>
    </div>
</body>
</html>"""

    return html


def construir_cuerpo_texto(
    discrepancias: List[Dict],
    resumen: Dict,
    nombre_esquema: str,
    fecha_ejecucion: str,
) -> str:
    """Construye el cuerpo en texto plano del correo (fallback para clientes sin HTML).

    Args:
        discrepancias: Lista de tablas con diferencia != 0.
        resumen: Diccionario con totales del proceso.
        nombre_esquema: Nombre del esquema insumos_aaaamm.
        fecha_ejecucion: Fecha y hora de la ejecucion del pipeline.

    Returns:
        Cadena de texto plano con el cuerpo del correo.
    """
    tabla_texto = construir_tabla_texto(discrepancias)
    tablas_disc = resumen.get("tablas_discrepancia", 0)
    total_tablas = resumen.get("total_tablas", 0)
    tablas_ok = resumen.get("tablas_ok", 0)
    total_unloaded = resumen.get("total_unloaded", 0)
    total_copied = resumen.get("total_copied", 0)
    total_diferencia = resumen.get("total_diferencia", 0)

    texto = f"""
ADE - ALERTA DE DISCREPANCIAS EN CIFRAS CONTROL
================================================
Proyecto Atlas de Datos Estadisticos | Seguros Atlas

Estimado Elias,

El sistema automatizado de validacion del proyecto ADE ha completado la revision
de la carga mensual del esquema {nombre_esquema} y ha detectado {tablas_disc}
tabla(s) con discrepancias entre los registros extraidos de SIISA (Unloaded) y
los registros copiados en PostgreSQL ADE (Copied).

RESUMEN DEL PROCESO - {fecha_ejecucion}
Total de tablas procesadas : {total_tablas}
Tablas sin diferencia (OK) : {tablas_ok}
Tablas con discrepancia    : {tablas_disc}
Total Unloaded (SIISA)     : {total_unloaded:,}
Total Copied (ADE)         : {total_copied:,}
Diferencia total           : {total_diferencia:,}

TABLAS CON DISCREPANCIAS ({tablas_disc})
{tabla_texto}

PROCEDIMIENTO DE CORRECCION:
1. Identificar la causa de la discrepancia en el sistema SIISA.
2. Purgar los registros incompletos de la tabla afectada en el esquema
   {nombre_esquema} en PostgreSQL ADE.
3. Re-ejecutar la extraccion y copia para las tablas afectadas.
4. Notificar al equipo ADE cuando la re-carga este completa.
5. El pipeline de validacion se re-ejecutara para confirmar diferencia = 0.

Este correo fue generado automaticamente por el sistema ADE.
Para consultas, contactar al equipo de desarrollo ADE via Slack.

Esquema validado : {nombre_esquema}
Fecha ejecucion  : {fecha_ejecucion}
Sistema          : ADE - Atlas de Datos Estadisticos | Seguros Atlas
Equipo           : Exelixi - Ing. Ramon Balderas Jimenez
"""
    return texto


# ===========================================================================
# FUNCIONES DE GMAIL API
# ===========================================================================

def obtener_servicio_gmail():
    """Autentica y retorna el servicio de Gmail API.

    En desarrollo: usa credentials.json y genera token.json.
    En produccion (GCP): usa Application Default Credentials (ADC) con
    Service Account que tenga delegacion de dominio de Google Workspace.

    Returns:
        Objeto de servicio de Gmail API autenticado.

    Raises:
        Exception: Si no se pueden obtener las credenciales.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None

    # Intentar cargar token existente
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, GMAIL_SCOPES)
            logger.info("Token de Gmail cargado desde %s", TOKEN_FILE)
        except Exception as exc:
            logger.warning("No se pudo cargar el token existente: %s", exc)
            creds = None

    # Si no hay credenciales validas, iniciar flujo OAuth
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Token de Gmail renovado exitosamente.")
            except Exception as exc:
                logger.warning("No se pudo renovar el token: %s", exc)
                creds = None

        if not creds:
            # Verificar si las credenciales vienen de Secret Manager (JSON string)
            gmail_creds_json = os.environ.get("GMAIL_CREDENTIALS")
            if gmail_creds_json:
                # Credenciales inyectadas como variable de entorno (Secret Manager)
                import tempfile
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False
                ) as tmp:
                    tmp.write(gmail_creds_json)
                    tmp_path = tmp.name

                flow = InstalledAppFlow.from_client_secrets_file(
                    tmp_path, GMAIL_SCOPES
                )
                os.unlink(tmp_path)
            elif os.path.exists(CREDENTIALS_FILE):
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, GMAIL_SCOPES
                )
            else:
                raise FileNotFoundError(
                    f"No se encontraron credenciales de Gmail. "
                    f"Archivo esperado: {CREDENTIALS_FILE} o variable "
                    f"de entorno GMAIL_CREDENTIALS."
                )

            creds = flow.run_local_server(port=0)
            logger.info("Autenticacion OAuth completada.")

        # Guardar token para proximas ejecuciones
        try:
            with open(TOKEN_FILE, "w") as token_file:
                token_file.write(creds.to_json())
            logger.info("Token guardado en %s", TOKEN_FILE)
        except Exception as exc:
            logger.warning("No se pudo guardar el token: %s", exc)

    servicio = build("gmail", "v1", credentials=creds)
    logger.info("Servicio de Gmail API inicializado.")
    return servicio


def crear_mensaje_mime(
    remitente: str,
    destinatario: str,
    cc: str,
    asunto: str,
    cuerpo_html: str,
    cuerpo_texto: str,
) -> Dict:
    """Crea el mensaje MIME multipart para el borrador de Gmail.

    Args:
        remitente: Direccion de correo del remitente.
        destinatario: Direccion de correo del destinatario (Elias).
        cc: Direcciones en copia (separadas por coma).
        asunto: Asunto del correo.
        cuerpo_html: Cuerpo del correo en formato HTML.
        cuerpo_texto: Cuerpo del correo en texto plano (fallback).

    Returns:
        Diccionario con el mensaje codificado en base64 para la API de Gmail.
    """
    mensaje = MIMEMultipart("alternative")
    mensaje["From"] = remitente
    mensaje["To"] = destinatario
    if cc:
        mensaje["Cc"] = cc
    mensaje["Subject"] = asunto

    # Adjuntar partes: texto plano primero, HTML al final (preferencia del cliente)
    parte_texto = MIMEText(cuerpo_texto, "plain", "utf-8")
    parte_html = MIMEText(cuerpo_html, "html", "utf-8")

    mensaje.attach(parte_texto)
    mensaje.attach(parte_html)

    # Codificar en base64 URL-safe para la API de Gmail
    mensaje_bytes = mensaje.as_bytes()
    mensaje_b64 = base64.urlsafe_b64encode(mensaje_bytes).decode("utf-8")

    return {"message": {"raw": mensaje_b64}}


def crear_borrador_gmail(
    servicio,
    remitente: str,
    destinatario: str,
    cc: str,
    asunto: str,
    cuerpo_html: str,
    cuerpo_texto: str,
) -> Dict:
    """Crea un borrador en Gmail usando la API.

    El borrador NO se envia automaticamente. El equipo ADE lo revisa
    y envia manualmente despues de validar el contenido.

    Args:
        servicio: Objeto de servicio de Gmail API autenticado.
        remitente: Direccion de correo del remitente.
        destinatario: Direccion de correo del destinatario.
        cc: Direcciones en copia.
        asunto: Asunto del correo.
        cuerpo_html: Cuerpo HTML del correo.
        cuerpo_texto: Cuerpo texto plano del correo.

    Returns:
        Diccionario con la respuesta de la API (incluye el ID del borrador).

    Raises:
        Exception: Si ocurre un error al crear el borrador.
    """
    try:
        cuerpo_draft = crear_mensaje_mime(
            remitente, destinatario, cc, asunto, cuerpo_html, cuerpo_texto
        )

        borrador = (
            servicio.users()
            .drafts()
            .create(userId="me", body=cuerpo_draft)
            .execute()
        )

        draft_id = borrador.get("id", "N/A")
        logger.info(
            "Borrador de Gmail creado exitosamente. ID: %s", draft_id
        )
        return borrador

    except Exception as exc:
        logger.error("Error al crear el borrador de Gmail: %s", exc)
        raise


# ===========================================================================
# FUNCION PRINCIPAL
# ===========================================================================

def generar_borrador_discrepancias(
    nombre_esquema: Optional[str] = None,
    destinatario: Optional[str] = None,
    remitente: Optional[str] = None,
    cc: Optional[str] = None,
) -> Optional[str]:
    """Funcion principal: evalua cifras_control y genera borrador si hay discrepancias.

    Flujo:
        1. Conectar a PostgreSQL.
        2. Consultar tablas con diferencia != 0 en cifras_control.
        3. Si no hay discrepancias, terminar sin crear borrador.
        4. Si hay discrepancias, construir el correo HTML y texto.
        5. Autenticar con Gmail API.
        6. Crear el borrador (NO enviar).
        7. Retornar el ID del borrador creado.

    Args:
        nombre_esquema: Nombre del esquema insumos_aaaamm. Si es None,
                        usa el esquema del mes actual.
        destinatario: Email del destinatario. Si es None, usa GMAIL_DESTINATARIO.
        remitente: Email del remitente. Si es None, usa GMAIL_REMITENTE.
        cc: Emails en copia. Si es None, usa GMAIL_CC.

    Returns:
        ID del borrador creado en Gmail, o None si no habia discrepancias.

    Raises:
        Exception: Si ocurre un error critico durante el proceso.
    """
    # Determinar nombre del esquema
    if not nombre_esquema:
        nombre_esquema = f"insumos_{datetime.now().strftime('%Y%m')}"

    dest = destinatario or GMAIL_DESTINATARIO
    rem = remitente or GMAIL_REMITENTE
    copia = cc or GMAIL_CC
    fecha_ejecucion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    logger.info(
        "=== Iniciando evaluacion de cifras_control para esquema: %s ===",
        nombre_esquema,
    )

    conn = None
    try:
        # Paso 1: Conectar a PostgreSQL
        conn = obtener_conexion_postgres()

        # Paso 2: Consultar discrepancias
        discrepancias = consultar_discrepancias(conn, nombre_esquema)
        resumen = consultar_resumen_total(conn, nombre_esquema)

        # Paso 3: Si no hay discrepancias, terminar
        if not discrepancias:
            logger.info(
                "No se detectaron discrepancias en '%s.cifras_control'. "
                "No se generara borrador de correo.",
                nombre_esquema,
            )
            return None

        logger.info(
            "Se detectaron %d tabla(s) con discrepancias. "
            "Generando borrador de correo...",
            len(discrepancias),
        )

        # Paso 4: Construir el correo
        mes_anio = nombre_esquema.replace("insumos_", "")
        asunto = (
            f"[ADE] ALERTA: Discrepancias en Cifras Control - "
            f"Insumos {mes_anio} | {len(discrepancias)} tabla(s) afectada(s)"
        )

        cuerpo_html = construir_cuerpo_html(
            discrepancias, resumen, nombre_esquema, fecha_ejecucion
        )
        cuerpo_texto = construir_cuerpo_texto(
            discrepancias, resumen, nombre_esquema, fecha_ejecucion
        )

        # Paso 5: Autenticar con Gmail API
        servicio_gmail = obtener_servicio_gmail()

        # Paso 6: Crear el borrador
        borrador = crear_borrador_gmail(
            servicio=servicio_gmail,
            remitente=rem,
            destinatario=dest,
            cc=copia,
            asunto=asunto,
            cuerpo_html=cuerpo_html,
            cuerpo_texto=cuerpo_texto,
        )

        draft_id = borrador.get("id", "N/A")
        logger.info(
            "=== Borrador creado exitosamente. ID: %s ===", draft_id
        )
        logger.info(
            "IMPORTANTE: El borrador NO fue enviado. "
            "El equipo ADE debe revisarlo y enviarlo manualmente desde Gmail."
        )

        return draft_id

    except Exception as exc:
        logger.error(
            "Error en la generacion del borrador de discrepancias: %s", exc
        )
        raise

    finally:
        if conn:
            conn.close()
            logger.info("Conexion a PostgreSQL cerrada.")


# ===========================================================================
# PUNTO DE ENTRADA
# ===========================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="ADE - Generador de borrador de correo para discrepancias "
                    "en cifras control."
    )
    parser.add_argument(
        "--esquema",
        default=None,
        help="Nombre del esquema insumos_aaaamm. Ej: insumos_202603. "
             "Si no se indica, usa el mes actual.",
    )
    parser.add_argument(
        "--destinatario",
        default=None,
        help="Email del destinatario (Elias). "
             "Por defecto usa la variable de entorno GMAIL_DESTINATARIO.",
    )
    parser.add_argument(
        "--remitente",
        default=None,
        help="Email del remitente. "
             "Por defecto usa la variable de entorno GMAIL_REMITENTE.",
    )
    parser.add_argument(
        "--cc",
        default=None,
        help="Emails en copia (separados por coma).",
    )

    args = parser.parse_args()

    try:
        draft_id = generar_borrador_discrepancias(
            nombre_esquema=args.esquema,
            destinatario=args.destinatario,
            remitente=args.remitente,
            cc=args.cc,
        )

        if draft_id:
            print(f"OK: Borrador creado con ID: {draft_id}")
            print("Revisar y enviar manualmente desde Gmail.")
        else:
            print("OK: No se detectaron discrepancias. No se genero borrador.")

        sys.exit(0)

    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
