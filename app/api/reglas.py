from fastapi import APIRouter, HTTPException
from app.core.firestore import get_db
from app.core.mit_models import ReglaMIT
from typing import List, Optional
from datetime import datetime

router = APIRouter()
db = get_db()
COL_REGLAS = "ade_cat_reglas"

@router.get("", response_model=List[dict])
def buscar_reglas(
    q: Optional[str]=None, severidad: Optional[str]=None, 
    ramo: Optional[str]=None, status: Optional[str]=None
):
    """Consulta con filtros Enterprise"""
    try:
        docs = db.collection(COL_REGLAS).stream()
        resultado = []
        for doc in docs:
            d = doc.to_dict()
            d["id_incidencia"] = doc.id
            
            # Filtros en memoria (Firestore native filters require composite indexes)
            cumple = True
            
            # Filtro Texto General
            if q:
                txt = f"{d.get('id_incidencia','')} {d.get('nombre_funcion','')} {str(d.get('tags_config',''))}".lower()
                if q.lower() not in txt: cumple = False
            
            # Filtros Específicos
            if severidad and severidad != "" and d.get('severidad') != severidad: cumple = False
            if ramo and ramo != "" and d.get('ramo') != ramo: cumple = False
            
            # Filtro Status (Mapeo booleano/string)
            if status:
                st_real = d.get('status', 'ACTIVO')
                if status == 'ACTIVO' and st_real != 'ACTIVO': cumple = False
                if status == 'INACTIVO' and st_real != 'INACTIVO': cumple = False

            if cumple:
                resultado.append(d)
        return resultado
    except Exception as e:
        print(f"ERROR BUSCAR: {e}")
        return []

@router.post("")
def guardar_regla(regla: ReglaMIT):
    """ALTA: Crea un registro nuevo"""
    try:
        doc_ref = db.collection(COL_REGLAS).document(regla.id_incidencia)
        # Validar si ya existe para no sobrescribir accidentalmente en un POST
        if doc_ref.get().exists:
             raise HTTPException(status_code=400, detail="El ID de incidencia ya existe.")
             
        datos = regla.dict()
        datos['fec_status'] = datetime.now()
        datos['status'] = 'ACTIVO'
        datos['activo'] = True
        doc_ref.set(datos)
        return {"mensaje": "Regla creada exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{id_regla}")
def actualizar_regla(id_regla: str, regla: ReglaMIT):
    """CAMBIO: Actualiza datos sin tocar el ID"""
    try:
        doc_ref = db.collection(COL_REGLAS).document(id_regla)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Regla no encontrada")

        datos = regla.dict(exclude={'id_incidencia'}) # Nunca actualizamos la PK
        datos['fec_status'] = datetime.now()
        
        # Mantenemos consistencia entre booleano y status string
        if datos.get('activo') is True: datos['status'] = 'ACTIVO'
        if datos.get('activo') is False: datos['status'] = 'INACTIVO'

        doc_ref.update(datos)
        return {"mensaje": "Regla actualizada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{id_regla}")
def baja_logica_regla(id_regla: str):
    """BAJA: Lógica (Soft Delete)"""
    try:
        # NO BORRAMOS, SOLO ACTUALIZAMOS STATUS
        db.collection(COL_REGLAS).document(id_regla).update({
            "activo": False,
            "status": "INACTIVO",
            "fec_status": datetime.now()
        })
        return {"mensaje": "Baja lógica aplicada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))