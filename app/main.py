import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Importamos los routers (Incluyendo el NUEVO de incidencias)
from app.api import reglas, usuarios, pedimentos, incidencias

app = FastAPI(title="ADE Core Enterprise")

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de Archivos Estáticos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# --- REGISTRO DE RUTAS (ROUTERS) ---
app.include_router(reglas.router, prefix="/api/reglas", tags=["Reglas MIT"])
app.include_router(usuarios.router, prefix="/api/usuarios", tags=["Usuarios"])
app.include_router(pedimentos.router, prefix="/api/pedimentos", tags=["Pedimentos"])
# NUEVO: Registramos Incidencias
app.include_router(incidencias.router, prefix="/api/incidencias", tags=["Incidencias"])

# --- RUTAS DE LA INTERFAZ (HTML) ---

@app.get("/")
def read_root():
    return {"mensaje": "ADE Core API v6.0 Enterprise - Online"}

@app.get("/mit")
async def serve_mit_module():
    return FileResponse(os.path.join(BASE_DIR, "ui", "mit.html"))

@app.get("/usuarios")
async def serve_usuarios_module():
    return FileResponse(os.path.join(BASE_DIR, "ui", "usuarios.html"))

@app.get("/pedimentos")
async def serve_pedimentos_module():
    return FileResponse(os.path.join(BASE_DIR, "ui", "pedimentos.html"))

# NUEVO: Ruta para ver la pantalla de Incidencias
@app.get("/incidencias")
async def serve_incidencias_module():
    file_path = os.path.join(BASE_DIR, "ui", "incidencias.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "Módulo Incidencias no encontrado"}

@app.get("/dashboard")
async def serve_dashboard_module():
    return FileResponse(os.path.join(BASE_DIR, "ui", "dashboard.html"))