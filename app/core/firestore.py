import firebase_admin
from firebase_admin import credentials, firestore
import os

def get_db():
    # Evita reiniciar la app si ya existe (útil para el reload)
    if not firebase_admin._apps:
        try:
            # TRUCO INFALIBLE: Usar la ruta de ESTE archivo (firestore.py) como ancla
            # Estamos en: .../ade-core/app/core/firestore.py
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Subimos 2 niveles para llegar a la raíz (ade-core)
            # Nivel 1: .../ade-core/app
            # Nivel 2: .../ade-core
            root_dir = os.path.dirname(os.path.dirname(current_dir))
            
            # Construimos la ruta a la llave
            cred_path = os.path.join(root_dir, "service-account.json")

            print(f"🔎 BUSCANDO LLAVE EN: {cred_path}") # Esto saldrá en tu terminal

            if not os.path.exists(cred_path):
                # Intento de emergencia: buscar en la carpeta actual de ejecución
                cred_path = "service-account.json"
            
            if not os.path.exists(cred_path):
                raise FileNotFoundError(f"CRÍTICO: No se encuentra 'service-account.json' en {root_dir}")

            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("✅ CONEXIÓN A FIREBASE EXITOSA")
            
        except Exception as e:
            print(f"❌ ERROR DE CONEXIÓN: {e}")
            raise e
    
    return firestore.client()