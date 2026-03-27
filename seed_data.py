# seed_data.py
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta

# Inicializar (Asegúrate que 'service-account.json' existe)
try:
    cred = credentials.Certificate("service-account.json")
    firebase_admin.initialize_app(cred)
except ValueError:
    pass # Ya inicializado

db = firestore.client()

def sembrar():
    print(">>> LIMPIANDO BASE DE DATOS...")
    # Limpiar colecciones clave
    for col in ["ade_usuarios", "ade_cat_reglas", "ade_pedimentos"]:
        docs = db.collection(col).stream()
        for doc in docs:
            doc.reference.delete()

    print(">>> CREANDO DATOS NUEVOS COMPATIBLES...")

    # 1. USUARIO (Con Área)
    db.collection("ade_usuarios").document("ANA001").set({
        "id_usuario": "ANA001",
        "nombre_completo": "Ana Analista",
        "correo_electronico": "ana@ade.mx",
        "rol_jerarquico": "ANALISTA",
        "area": "Mesa de Control",
        "activo": True,
        "fec_status": datetime.now(),
        "responsabilidades": [{"linea_negocio": "AUTOS", "ramo": "Autos", "sub_ramo": "Gral", "cve_producto": "Todos"}]
    })

    # 2. REGLA MIT (Con Vigencia Flexible)
    db.collection("ade_cat_reglas").document("VAL-001").set({
        "id_incidencia": "VAL-001",
        "nombre_funcion": "fn_valida_rfc",
        "descripcion": "Valida longitud de RFC",
        "severidad": "ALTA",
        "ramo": "VIDA",
        "status": "activo",
        "fec_status": datetime.now(),
        "vigencia": {"inicio": datetime.now(), "fin": None}, # Flexible
        "correcciones": {"valor_num": None, "valor_str": None, "valor_fec": None},
        "tags_config": ["#Fiscal"]
    })

    # 3. PEDIMENTO (Con Semáforos y Metadata)
    db.collection("ade_pedimentos").document("PED-2026-001").set({
        "id_pedimento": "PED-2026-001",
        "titulo": "Carga Mensual Enero",
        "id_responsable": "ANA001",
        "area_solicitada": "Mesa de Control",
        "ramo": "VIDA",
        "prioridad": "ALTA",
        "estatus": "SOLICITADO",
        "activo": True,
        "fec_status": datetime.now(),
        "metadata_control": {"ramo": "VIDA", "prioridad": "ALTA"},
        "tiempos": {
            "fec_inicio": datetime.now(),
            "fec_bloqueo": datetime.now() + timedelta(days=2),
            "fec_limite": datetime.now() + timedelta(days=5)
        },
        "bitacora_comentarios": [
            {
                "id_comentario": "c1", "id_autor": "Sistema", 
                "mensaje": "Pedimento inicializado", 
                "fec_comentario": datetime.now(), "tags": []
            }
        ]
    })

    print(">>> ¡LISTO! Base de datos reiniciada correctamente.")

if __name__ == "__main__":
    sembrar()