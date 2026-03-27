-- scripts/init-db.sql
-- Script de inicialización para PostgreSQL local
-- Se ejecuta automáticamente al crear el contenedor por primera vez

-- Extensiones útiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Schema base (placeholder — se extenderá conforme crezca el proyecto)
CREATE TABLE IF NOT EXISTS health_check (
    id SERIAL PRIMARY KEY,
    checked_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO health_check DEFAULT VALUES;
