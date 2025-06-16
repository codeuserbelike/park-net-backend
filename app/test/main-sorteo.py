from typing import Annotated
from fastapi import FastAPI, HTTPException, Depends
from contextlib import asynccontextmanager
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.dependencies import get_current_active_admin_user
from app.database.mongodb import connect_to_mongo, close_mongo_connection, get_database
from app.core.security import get_password_hash, verify_password
from app.modules.auth.router import router as auth_router
from app.modules.residentes.router import router as users_router
from app.modules.solicitudes.router import router as requests_router
from app.modules.sorteo.router import router as lottery_router
from app.modules.residentes.models import User
from app.modules.solicitudes.models import Request
from app.modules.sorteo.schemas import LotteryCreate
from app.modules.sorteo.service import LotteryService

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Función de ciclo de vida de la aplicación FastAPI.
    Se ejecuta al iniciar (startup) y al detener (shutdown) la aplicación.
    """
    print("🚀 Iniciando conexión con MongoDB...")
    await connect_to_mongo()
    print("✅ Conexión a MongoDB establecida.")
    
    db = get_database()
    
    # --- Lógica para asegurar que exista un usuario administrador por defecto ---
    admin = await db.users.find_one({"cc": "0000000000", "role": "administrador"}) 
    if not admin:
        print("\n⏳ Creando usuario administrador por defecto...")
        
        # PRUEBA DE HASHING - ANTES DE CREAR EL ADMIN
        test_password = "admin_password"
        test_hash = get_password_hash(test_password)
        print(f"\n🔒 PRUEBA DE SEGURIDAD INTERNA (main.py):")
        print(f"Contraseña original: {test_password}")
        print(f"Hash generado: {test_hash}")
        print(f"Verificación exitosa: {verify_password(test_password, test_hash)}")
        print(f"Verificación fallida (pass incorrecta): {verify_password('wrong_password', test_hash)}\n")
        
        # Creamos la instancia del modelo User para el administrador
        admin_user_data = User(
            full_name="Admin Principal",
            cc="0000000000",
            email="admin@admin.com",
            hashed_password=test_hash,
            apartment="Oficina Administración",
            phone_number="+573000000000",
            role="administrador",
            status="active"
        ) # type: ignore

        try:
            # Insertamos el documento directamente en la colección 'users'
            result = await db.users.insert_one(admin_user_data.model_dump(by_alias=True, exclude_unset=True))
            admin_id = str(result.inserted_id)
            print(f"✅ Usuario administrador creado con ID: {admin_id}")
            print(f"   Credenciales iniciales: CC='0000000000', Contraseña='{test_password}'")
        except Exception as e:
            print(f"❌ Error al crear el usuario administrador: {e}")
            admin_id = None
    else:
        admin_id = str(admin["_id"])
        print("ℹ️ Usuario administrador ya existe. Saltando creación.")
    
    # --- Crear usuario residente de prueba ---
    resident = await db.users.find_one({"cc": "1234567890"})
    if not resident:
        print("\n⏳ Creando usuario residente de prueba...")
        resident_password = "resident_password"
        resident_hash = get_password_hash(resident_password)
        resident_user_data = User(
            full_name="Residente de Prueba",
            cc="1234567890",
            email="residente@prueba.com",
            hashed_password=resident_hash,
            apartment="Torre A, Apto 101",
            phone_number="+573001234567",
            role="residente",
            status="active"
        ) # type: ignore
        
        try:
            result = await db.users.insert_one(resident_user_data.model_dump(by_alias=True, exclude_unset=True))
            resident_id = str(result.inserted_id)
            print(f"✅ Usuario residente creado con ID: {resident_id}")
            print(f"   Credenciales: CC='1234567890', Contraseña='{resident_password}'")
        except Exception as e:
            print(f"❌ Error al crear el usuario residente: {e}")
            resident_id = None
    else:
        resident_id = str(resident["_id"])
        print("ℹ️ Usuario residente de prueba ya existe. Saltando creación.")
    
    # --- Crear solicitudes de prueba ---
    if resident_id:
        print("\n⏳ Creando solicitudes de prueba para el residente...")
        current_period = datetime.now().strftime("%Y-%m")
        
        # Solicitud pendiente
        request_pending = Request(
            user_id=resident_id,
            resident_cc="1234567890",
            resident_full_name="Residente de Prueba",
            vehicle_type="automovil",
            license_plate="ABC123",
            description="Solicitud pendiente de revisión",
            disability=False,
            pay=True,
            lottery_period=current_period,
            status="pending"
        ) # type: ignore
        
        # Solicitud aceptada
        request_accepted = Request(
            user_id=resident_id,
            resident_cc="1234567890",
            resident_full_name="Residente de Prueba",
            vehicle_type="motocicleta",
            license_plate="XYZ789",
            description="Solicitud aceptada",
            disability=True,
            pay=True,
            lottery_period=current_period,
            status="accepted"
        ) # type: ignore
        
        try:
            # Insertar solicitudes
            await db.requests.insert_one(request_pending.model_dump(by_alias=True, exclude_unset=True))
            await db.requests.insert_one(request_accepted.model_dump(by_alias=True, exclude_unset=True))
            print("✅ 2 solicitudes de prueba creadas (1 pendiente, 1 aceptada)")
        except Exception as e:
            print(f"❌ Error al crear solicitudes de prueba: {e}")
    
    # --- Ejecutar sorteo de prueba al iniciar ---
    if admin_id and resident_id:
        print("\n⏳ Ejecutando sorteo de prueba al iniciar la aplicación...")
        lottery_service = LotteryService(db)
        current_period = datetime.now().strftime("%Y-%m")
        lottery_data = LotteryCreate(
            period=current_period,
            num_car_spots=1,
            num_moto_spots=1
        )
        try:
            lottery_result = await lottery_service.execute_lottery(lottery_data)
            print(f"✅ Sorteo de prueba ejecutado para el período {current_period}:")
            print(f"   Ganadores: {[w.full_name for w in lottery_result.winners]}")
            print(f"   No ganadores: {[nw.full_name for nw in lottery_result.non_winners]}")
        except HTTPException as e:
            print(f"❌ Error al ejecutar sorteo de prueba: {e.detail}")
        except Exception as e:
            print(f"❌ Error inesperado al ejecutar sorteo de prueba: {e}")

    yield  # Aquí la aplicación comienza a recibir solicitudes
    
    print("Shutting down...")
    await close_mongo_connection()
    print("MongoDB connection closed.")

# Crea la instancia de la aplicación FastAPI y asocia el ciclo de vida
app = FastAPI(
    title="Park-Net API",
    description="API para la gestión de estacionamientos en condominios.",
    version="1.0.0",
    lifespan=lifespan
)

# --- Incluye todos los routers de tu aplicación ---
app.include_router(auth_router)  # Router de autenticación
app.include_router(users_router)  # Router de usuarios/residentes
app.include_router(requests_router)  # Router de solicitudes
app.include_router(lottery_router)  # Nuevo router de sorteo

# --- Rutas base y de prueba ---
@app.get("/", tags=["Root"])
async def root():
    """
    Ruta raíz de la API.
    """
    return {"message": "Bienvenido al sistema de gestión de condominios Park-Net API"}