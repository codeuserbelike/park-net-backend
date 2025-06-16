from fastapi import FastAPI, HTTPException
from app.database.mongodb import connect_to_mongo, close_mongo_connection, get_database
from contextlib import asynccontextmanager
from app.core.security import get_password_hash, verify_password  # Importa las funciones actualizadas
from app.modules.auth.router import router as auth_router  # Importa el router de autenticación

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    db = get_database()
    
    # Crear un administrador si no existe
    admin = await db.users.find_one({"email": "admin@admin.com"})
    if not admin:
        from app.modules.residentes.models import User
        
        # PRUEBA DE HASHING - ANTES DE CREAR EL ADMIN
        test_password = "admin_password"
        test_hash = get_password_hash(test_password)
        print(f"\n🔒 PRUEBA DE SEGURIDAD:")
        print(f"Contraseña original: {test_password}")
        print(f"Hash generado: {test_hash}")
        print(f"Verificación exitosa: {verify_password(test_password, test_hash)}")
        print(f"Verificación fallida: {verify_password('wrong_password', test_hash)}\n")
        
        admin_user = User(
            full_name="Admin Principal",
            cc="0000000000",
            email="admin@admin.com",
            hashed_password=test_hash,  # Usamos el hash generado
            apartment="Oficina Administración",
            phone_number="+573000000000",
            role="administrador",
            status="active"
        ) # type: ignore
        
        result = await db.users.insert_one(admin_user.model_dump(by_alias=True, exclude_unset=True))
        print(f"✅ Admin creado con ID: {result.inserted_id}")
    
    yield
    await close_mongo_connection()

app = FastAPI(lifespan=lifespan)

# Incluye todos los routers necesarios
app.include_router(auth_router)

@app.get("/")
async def root():
    return {"message": "Bienvenido al sistema de gestión de condominios Park-Net"}

# Ruta adicional para probar seguridad en tiempo real
@app.get("/test-security/{password}")
async def test_security(password: str):
    try:
        hashed = get_password_hash(password)
        return {
            "password": password,
            "hashed": hashed,
            "verify_correct": verify_password(password, hashed),
            "verify_wrong": verify_password(password + "x", hashed)
        }
    except Exception as e:
        raise HTTPException(500, f"Error en seguridad: {str(e)}")