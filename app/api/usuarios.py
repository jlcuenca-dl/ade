from fastapi import APIRouter, HTTPException
from app.core.firestore import get_db
from app.core.user_models import UsuarioADE
from typing import List, Optional
from datetime import datetime

router = APIRouter()
db = get_db()
COL_USUARIOS = "ade_usuarios"

@router.get("/buscar", response_model=List[dict])
def buscar_usuarios(q: Optional[str]=None):
    """Búsqueda simple para debug"""
    try:
        docs = db.collection(COL_USUARIOS).stream()
        resultado = []
        for doc in docs:
            d = doc.to_dict()
            d["id_usuario"] = doc.id
            # Asegurar que responsabilidades sea una lista, aunque no exista en BD
            if "responsabilidades" not in d:
                d["responsabilidades"] = []
            resultado.append(d)
        return resultado
    except Exception as e:
        print(f"❌ Error buscando usuarios: {e}")
        return []

@router.post("/guardar")
def guardar_usuario(usuario: UsuarioADE):
    try:
        print(f"📥 Intentando guardar usuario: {usuario.id_usuario}")
        print(f"📋 Responsabilidades recibidas: {len(usuario.responsabilidades)}")

        doc_ref = db.collection(COL_USUARIOS).document(usuario.id_usuario)
        datos = usuario.dict()
        datos['fec_status'] = datetime.now()
        
        doc_ref.set(datos)
        print("✅ Usuario guardado exitosamente")
        return {"mensaje": "Usuario creado"}
    except Exception as e:
        print(f"🔥 ERROR AL GUARDAR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{id_usuario}")
def actualizar_usuario(id_usuario: str, usuario: UsuarioADE):
    try:
        print(f"🔄 Intentando actualizar: {id_usuario}")
        print(f"📋 Nuevas responsabilidades: {usuario.responsabilidades}")

        doc_ref = db.collection(COL_USUARIOS).document(id_usuario)
        
        # Convertimos a dict y forzamos la estructura correcta
        datos = usuario.dict(exclude={'id_usuario'})
        datos['fec_status'] = datetime.now()

        doc_ref.update(datos)
        print("✅ Usuario actualizado correctamente")
        return {"mensaje": "Usuario actualizado"}
    except Exception as e:
        print(f"🔥 ERROR AL ACTUALIZAR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{id_usuario}")
def baja_logica_usuario(id_usuario: str):
    try:
        db.collection(COL_USUARIOS).document(id_usuario).update({
            "activo": False,
            "fec_status": datetime.now()
        })
        return {"mensaje": "Baja aplicada"}
    except Exception as e:
        raise HTTPException(500, str(e))