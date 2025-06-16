from contextlib import asynccontextmanager
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi.middleware.cors import CORSMiddleware

import os  # Añadido para leer la variable de entorno PORT

from app.database.mongodb import connect_to_mongo, close_mongo_connection, get_database
from app.modules.auth.router import router as auth_router
from app.modules.residentes.router import router as resident_router
from app.modules.solicitudes.router import router as requests_router
from app.modules.sorteo.router import router as lottery_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Función de ciclo de vida de la aplicación FastAPI.
    """
    print("🚀 Iniciando conexión con MongoDB...")
    await connect_to_mongo()
    print("✅ Conexión a MongoDB establecida.")
    yield
    print("🔌 Cerrando conexión con MongoDB...")
    await close_mongo_connection()
    print("✅ Conexión a MongoDB cerrada.")

# Crea la instancia de la aplicación FastAPI y asocia el ciclo de vida
app = FastAPI(
    title="Park-Net API",
    description="API para la gestión de parqueaderos en un conjunto residencial.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

origins = [
    "http://localhost",
    "http://localhost:8080",
    "*"  # Añadido para permitir acceso desde Render (ajústalo según tu frontend)
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Incluye todos los routers de tu aplicación ---
app.include_router(auth_router)
app.include_router(resident_router)
app.include_router(requests_router)
app.include_router(lottery_router)

# --- Ruta raíz de la API ---
@app.get("/", tags=["Root"])
async def root():
    """
    Ruta raíz de la API.
    """
    return {"message": "Bienvenido al sistema de gestión de parqueaderos Park-Net API"}