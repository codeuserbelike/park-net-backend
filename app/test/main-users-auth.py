from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from app.database.mongodb import connect_to_mongo, close_mongo_connection, get_database
from app.core.security import get_password_hash, verify_password
from app.modules.auth.router import router as auth_router
from app.modules.residentes.router import router as users_router # Importamos el nuevo router de usuarios/residentes
from app.modules.residentes.models import User # Necesario para crear el admin user

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
    # Usamos 'cc' en lugar de 'email' para el login del administrador, por tu cambio en UserLogin
    admin = await db.users.find_one({"cc": "0000000000", "role": "administrador"}) 
    if not admin:
        print("\n⏳ Creando usuario administrador por defecto...")
        
        # PRUEBA DE HASHING - ANTES DE CREAR EL ADMIN (¡Esto es bueno para depuración!)
        test_password = "admin_password" # Contraseña por defecto para el admin
        test_hash = get_password_hash(test_password)
        print(f"\n🔒 PRUEBA DE SEGURIDAD INTERNA (main.py):")
        print(f"Contraseña original: {test_password}")
        print(f"Hash generado: {test_hash}")
        print(f"Verificación exitosa: {verify_password(test_password, test_hash)}")
        print(f"Verificación fallida (pass incorrecta): {verify_password('wrong_password', test_hash)}\n")
        
        # Creamos la instancia del modelo User para el administrador
        admin_user_data = User(
            full_name="Admin Principal",
            cc="0000000000", # CC por defecto para el admin
            email="admin@admin.com", # Email para el admin
            hashed_password=test_hash,
            apartment="Oficina Administración",
            phone_number="+573000000000",
            role="administrador",
            status="active"
        ) # type: ignore

        try:
            # Insertamos el documento directamente en la colección 'users'
            result = await db.users.insert_one(admin_user_data.model_dump(by_alias=True, exclude_unset=True))
            print(f"✅ Usuario administrador creado con ID: {result.inserted_id}")
            print(f"   Credenciales iniciales: CC='0000000000', Contraseña='{test_password}'")
        except Exception as e:
            print(f"❌ Error al crear el usuario administrador: {e}")
    else:
        print("ℹ️ Usuario administrador ya existe. Saltando creación.")
    
    yield # Aquí la aplicación comienza a recibir solicitudes
    
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
app.include_router(auth_router) # Prefijo y versión para el router de autenticación
app.include_router(users_router) # Prefijo y versión para el router de usuarios/residentes

# --- Rutas base y de prueba ---
@app.get("/", tags=["Root"])
async def root():
    """
    Ruta raíz de la API.
    """
    return {"message": "Bienvenido al sistema de gestión de condominios Park-Net API"}

@app.get("/test-security/{password}", tags=["Testing"])
async def test_security_endpoint(password: str):
    """
    Ruta de prueba para verificar el hashing de contraseñas.
    """
    try:
        hashed = get_password_hash(password)
        return {
            "password": password,
            "hashed": hashed,
            "verify_correct": verify_password(password, hashed),
            "verify_wrong": verify_password(password + "x", hashed)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en seguridad: {str(e)}")