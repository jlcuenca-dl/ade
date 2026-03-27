from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class ResponsabilidadUsuario(BaseModel):
    # Relajamos la validación: si llega vacío, no explota
    linea_negocio: Optional[str] = "General"
    ramo: Optional[str] = "General"
    subramo: Optional[str] = ""
    cve_producto: Optional[str] = ""
    es_principal: bool = False

class UsuarioADE(BaseModel):
    id_usuario: str
    nombre_completo: str
    correo_electronico: Optional[str] = ""
    id_reporta_a: Optional[str] = ""
    rol_jerarquico: Optional[str] = "ANALISTA"

    # La lista clave
    responsabilidades: List[ResponsabilidadUsuario] = []

    tags: Optional[str] = ""
    activo: bool = True
    status: Optional[str] = "ACTIVO"
    fec_status: Optional[datetime] = None