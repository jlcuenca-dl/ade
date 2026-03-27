from pydantic import BaseModel
from typing import Optional, List, Dict

class PedimentoInfo(BaseModel):
    # Identidad
    id_pedimento: str
    id_pedimento_padre: Optional[str] = "" 
    titulo: str
    
    # Responsabilidad
    id_responsable: Optional[str] = ""
    usuarios_involucrados: List[str] = [] 
    
    # Planeación (Semáforos)
    status: Optional[str] = "SOLICITADO"
    fec_inicio: Optional[str] = None
    fec_fin: Optional[str] = None      # Fecha Compromiso (Fin de trabajo)
    fec_escala: Optional[str] = None   # Fecha Escalamiento (Alerta Roja)
    
    # Metadatos de Control (Todo junto ahora)
    linea_negocio: Optional[str] = ""
    ramo: Optional[str] = ""
    subramo: Optional[str] = ""
    cve_producto: Optional[str] = ""
    
    # Flexibilidad
    tags_pedimento: List[str] = []
    activo: bool = True