from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ReglaMIT(BaseModel):
    id_incidencia: str
    nombre_funcion: str
    descripcion: Optional[str] = None
    severidad: str  # Campo Obligatorio
    linea_producto: Optional[str] = None
    ramo: Optional[str] = None
    subramo: Optional[str] = None
    cve_producto: Optional[str] = None
    tags_config: Optional[str] = None
    status: Optional[str] = "ACTIVO"
    activo: bool = True
    fec_status: Optional[datetime] = None