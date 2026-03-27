from fastapi import APIRouter, HTTPException
from app.core.firestore import get_db
from app.core.pedimentos_models import PedimentoInfo
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

router = APIRouter()
db = get_db()
COL_PEDIMENTOS = "ade_pedimentos"
COL_COMENTARIOS = "ade_ped_comentarios"

class Comentario(BaseModel):
    id_comentario: Optional[str] = None
    id_pedimento: str 
    id_usuario_emisor: str
    texto: str
    fec_hora: Optional[datetime] = None

@router.get("", response_model=List[dict])
def buscar_pedimentos(
    q: Optional[str]=None, status: Optional[str]=None, padre: Optional[str]=None,
    linea: Optional[str]=None, ramo: Optional[str]=None, subramo: Optional[str]=None,
    producto: Optional[str]=None, tags: Optional[str]=None, resp: Optional[str]=None
):
    try:
        docs = db.collection(COL_PEDIMENTOS).stream()
        resultado = []
        for doc in docs:
            d = doc.to_dict()
            d["id_pedimento"] = doc.id
            
            cumple = True
            # Búsqueda general
            if q:
                txt = f"{d.get('id_pedimento','')} {d.get('titulo','')} {d.get('id_responsable','')} {str(d.get('tags_pedimento',''))}".lower()
                if q.lower() not in txt: cumple = False
            
            # Filtros específicos
            if padre and d.get('id_pedimento_padre') != padre: cumple = False
            if linea and d.get('linea_negocio') != linea: cumple = False
            if ramo and d.get('ramo') != ramo: cumple = False
            if resp and resp != '@yo' and d.get('id_responsable') != resp: cumple = False
            if status:
                st_real = d.get('status', 'SOLICITADO')
                if status != st_real: cumple = False
            
            if cumple:
                resultado.append(d)
        return resultado
    except Exception as e:
        print(f"ERROR PEDIMENTOS: {e}")
        return []

@router.post("")
def guardar_pedimento(item: PedimentoInfo):
    try:
        doc_ref = db.collection(COL_PEDIMENTOS).document(item.id_pedimento)
        if doc_ref.get().exists:
             raise HTTPException(status_code=400, detail="El ID de pedimento ya existe.")
        datos = item.dict()
        datos['fec_status'] = datetime.now()
        doc_ref.set(datos)
        return {"mensaje": "Pedimento creado"}
    except Exception as e:
        print(f"Error al guardar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{id_pedimento}")
def actualizar_pedimento(id_pedimento: str, item: PedimentoInfo):
    try:
        doc_ref = db.collection(COL_PEDIMENTOS).document(id_pedimento)
        datos = item.dict(exclude={'id_pedimento'}) 
        datos['fec_status'] = datetime.now()
        doc_ref.update(datos)
        return {"mensaje": "Pedimento actualizado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{id_pedimento}")
def baja_logica_pedimento(id_pedimento: str):
    try:
        db.collection(COL_PEDIMENTOS).document(id_pedimento).update({
            "activo": False, "status": "CANCELADO", "fec_status": datetime.now()
        })
        return {"mensaje": "Pedimento cancelado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{id_pedimento}/comentarios")
def leer_comentarios(id_pedimento: str):
    try:
        docs = db.collection(COL_COMENTARIOS).where("id_pedimento", "==", id_pedimento).stream()
        lista = [doc.to_dict() for doc in docs]
        lista.sort(key=lambda x: str(x.get('fec_hora', '')))
        return lista
    except Exception as e:
        print(f"Error comentarios: {e}")
        return []

@router.post("/{id_pedimento}/comentarios")
def agregar_comentario(id_pedimento: str, comentario: Comentario):
    try:
        uid = str(uuid.uuid4())
        datos = comentario.dict()
        datos['id_comentario'] = uid
        datos['fec_hora'] = datetime.now()
        db.collection(COL_COMENTARIOS).document(uid).set(datos)
        return {"mensaje": "Comentario agregado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# ... (imports anteriores)

@router.get("/nuevo_folio")
def obtener_siguiente_folio():
    """Calcula el siguiente ID consecutivo del año actual (Ej: PED-2026-005)"""
    try:
        anio_actual = datetime.now().year
        prefix = f"PED-{anio_actual}-"
        
        # Obtenemos todos los IDs que empiecen con el prefijo del año
        docs = db.collection(COL_PEDIMENTOS)\
                 .where("id_pedimento", ">=", prefix)\
                 .where("id_pedimento", "<", f"PED-{anio_actual+1}-")\
                 .stream()
        
        max_seq = 0
        for doc in docs:
            try:
                # Extraemos el número final: PED-2026-005 -> 5
                parts = doc.id.split('-')
                if len(parts) == 3:
                    seq = int(parts[2])
                    if seq > max_seq: max_seq = seq
            except:
                continue
        
        # Generamos el siguiente
        nuevo_id = f"{prefix}{str(max_seq + 1).zfill(3)}"
        return {"nuevo_id": nuevo_id}
    except Exception as e:
        print(f"Error generando folio: {e}")
        # Fallback por si falla
        return {"nuevo_id": f"PED-{datetime.now().year}-001"}