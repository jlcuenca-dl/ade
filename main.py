# main.py — ADE Backend Entry Point
# Atlas de Datos Estadísticos
# Mantenido por: jlcuenca@datalum.mx

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="ADE - Atlas de Datos Estadísticos",
    description="API para el sistema de datos estadísticos",
    version="0.1.0",
)

# CORS — permitir orígenes según ambiente
env = os.getenv("ENV", "local")
origins = {
    "local": ["http://localhost:3000", "http://localhost:5173"],
    "desa":  ["https://ade-frontend-desa-*.run.app"],
    "qa":    ["https://ade-frontend-qa-*.run.app"],
    "prod":  ["https://ade.datalum.mx"],
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins.get(env, ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint para Cloud Run y Docker."""
    return {"status": "ok", "env": env, "version": "0.1.0"}


@app.get("/")
async def root():
    return {
        "project": "ADE - Atlas de Datos Estadísticos",
        "env": env,
        "docs": "/docs",
    }
