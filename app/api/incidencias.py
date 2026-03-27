from fastapi import APIRouter, HTTPException
from app.core.firestore import get_db
from app.core.incidencias_models import Incidencia
from typing import List, Optional
from datetime import datetime

router = APIRouter()
db = get_db()
COL_INCIDENCIAS = "ade_bitacora_incidencias"

@router.get("", response_model=List[dict])
def buscar_incidencias(
    q: Optional[str]=None,       # Búsqueda general
    severidad: Optional[str]=None,
    status: Optional[str]=None,
    poliza: Optional[str]=None,  # Búsqueda exacta de póliza
    linea: Optional[str]=None
):
    try:
        docs = db.collection(COL_INCIDENCIAS).stream()
        resultado = []
        for doc in docs:
            d = doc.to_dict()
            d["id_bitacora"] = doc.id
            
            # --- FILTROS ---
            cumple = True
            
            # Texto General
            if q:
                txt = f"{d.get('id_bitacora','')} {d.get('poliza_id_nk','')} {d.get('descripcion_error','')} {str(d.get('tags_config',''))}".lower()
                if q.lower() not in txt: cumple = False
            
            # Filtros Específicos
            if severidad and d.get('severidad') != severidad: cumple = False
            if status and d.get('status') != status: cumple = False
            if linea and d.get('linea_negocio') != linea: cumple = False
            
            # Filtro por Póliza (Exacto o parcial)
            if poliza and poliza.lower() not in str(d.get('poliza_id_nk','')).lower(): cumple = False

            if cumple:
                resultado.append(d)
        
        # Ordenar por severidad (ALTA primero) para visualización
        # Un truco simple: ALTA < BAJA alfabéticamente no sirve, ordenamos manual
        prioridad = {"ALTA": 0, "MEDIA": 1, "BAJA": 2, "ADVERTENCIA": 3}
        resultado.sort(key=lambda x: prioridad.get(x.get('severidad', 'BAJA'), 99))
        
        return resultado
    except Exception as e:
        print(f"Error incidencias: {e}")
        return []

@router.post("")
def registrar_incidencia(item: Incidencia):
    try:
        doc_ref = db.collection(COL_INCIDENCIAS).document(item.id_bitacora)
        if doc_ref.get().exists:
             raise HTTPException(400, "ID de incidencia ya existe")
        
        datos = item.dict()
        if not datos.get('fec_deteccion'):
            datos['fec_deteccion'] = datetime.now().isoformat()
        datos['fec_actualizacion'] = datetime.now().isoformat()
        
        doc_ref.set(datos)
        return {"mensaje": "Incidencia registrada"}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.put("/{id_bitacora}")
def actualizar_incidencia(id_bitacora: str, item: Incidencia):
    try:
        doc_ref = db.collection(COL_INCIDENCIAS).document(id_bitacora)
        datos = item.dict(exclude={'id_bitacora'})
        datos['fec_actualizacion'] = datetime.now().isoformat()
        doc_ref.update(datos)
        return {"mensaje": "Incidencia actualizada"}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.delete("/{id_bitacora}")
def cerrar_incidencia(id_bitacora: str):
    try:
        # Baja lógica: Se marca como cerrada o inactiva
        db.collection(COL_INCIDENCIAS).document(id_bitacora).update({
            "activo": False,
            "status": "CERRADA-MANUAL",
            "fec_actualizacion": datetime.now().isoformat()
        })
        return {"mensaje": "Incidencia cerrada"}
    except Exception as e:
        raise HTTPException(500, str(e))