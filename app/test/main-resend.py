from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

import resend
from resend import Emails

from app.database.mongodb import connect_to_mongo, close_mongo_connection
from app.modules.auth.router import router as auth_router
from app.modules.residentes.router import router as resident_router
from app.modules.solicitudes.router import router as requests_router
from app.modules.sorteo.router import router as lottery_router

# Configurar la clave API de Resend
RESEND_KEY = os.getenv('RESEND_KEY')
if not RESEND_KEY:
    raise RuntimeError("La variable de entorno RESEND_KEY no está configurada.")
resend.api_key = RESEND_KEY

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Conexión a MongoDB
    await connect_to_mongo()
    print("✅ Conexión a MongoDB establecida exitosamente.")

    # Prueba de envío de correo
    test_email = "nhenaoz@unicartagena.edu.co"  # reemplaza por un correo válido
    html_content = """
    <html>
      <body>
        <h1>¡Hola, Mundo!</h1>
        <p>Esta es una prueba de envío con Resend desde Park‑Net API.</p>
        <p>Fecha y hora: Domingo, 15 de Junio de 2025 11:31 (UTC-5)</p>
      </body>
    </html>
    """

    params: Emails.SendParams = {
        "from": "Park‑Net Notificaciones <onboarding@resend.dev>",
        "to": [test_email],
        "subject": "Prueba de Correo – Hello World",
        "html": html_content
    }

    try:
        # Emails.send es síncrono y devuelve un dict
        result = Emails.send(params)
        print(f"✅ Prueba de correo enviada con éxito a {test_email}; response id = {result.get('id')}")
    except Exception as e:
        print(f"❌ Error en prueba de correo a {test_email}: {e}")

    yield

    # Cierre de conexión
    await close_mongo_connection()
    print("✅ Conexión a MongoDB cerrada.")

app = FastAPI(
    title="Park‑Net API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(auth_router)
app.include_router(resident_router)
app.include_router(requests_router)
app.include_router(lottery_router)

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Bienvenido a Park‑Net API"}
