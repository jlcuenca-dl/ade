from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ValoresIncidencia(BaseModel):
    valor_incorrecto: Optional[str] = None # Valor en SIISA
    valor_sugerido: Optional[str] = None   # Valor en ADE

class Incidencia(BaseModel):
    # Identificadores
    id_bitacora: str               # ID único de la incidencia
    poliza_id_nk: str              # Clave natural (SIISA)
    id_pedimento_ref: Optional[str] = None # Vínculo con Pedimentos
    
    # Tiempos
    fec_deteccion: Optional[str] = None
    fec_actualizacion: Optional[str] = None
    
    # Estado y Responsable
    status: str = "DETECTADA"      # detectada, en_pedimento, atendida, cerrada-reproceso
    usuario_atencion: Optional[str] = None
    
    # Gobernanza (Columnas de Control)
    severidad: str                 # ALTA, MEDIA, BAJA, ADVERTENCIA
    linea_negocio: Optional[str] = None
    ramo: Optional[str] = None
    sub_ramo: Optional[str] = None
    cve_producto: Optional[str] = None
    fase_proceso: Optional[str] = "MIT_VALIDACION" # Dónde se detectó
    
    # Datos del Error
    descripcion_error: str         # Qué falló
    valores: ValoresIncidencia     # Comparativa (Incorrecto vs Sugerido)
    
    # Flexibilidad
    tags_config: List[str] = []    # [#Semilla, #Prioridad, #Origen]
    activo: bool = True