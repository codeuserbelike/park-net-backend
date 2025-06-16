# app/test/main-repository.py
from fastapi import FastAPI
from app.database.mongodb import connect_to_mongo, close_mongo_connection, get_database
from app.modules.residentes.models import User
from app.shared.repository import BaseRepository 
from contextlib import asynccontextmanager
from bson import ObjectId
import asyncio
from typing import cast

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    db = get_database()
    user_repo = BaseRepository(db["users"], User)
    
    print("\n" + "="*50)
    print("INICIO DE PRUEBAS DEL REPOSITORIO")
    print("="*50)
    
    # 1. Prueba de creación
    new_user = User(
        full_name="Admin Test",
        cc="1193597001",
        email="admin_test@condominio.com",
        hashed_password="hashed_pass_123",
        apartment="Torre Test, Apto 101",
        phone_number="+573001111111",
        role="administrador",
        status="active"
    ) # type: ignore
    
    created_user = await user_repo.create(new_user)
    
    # Asegurarnos de que el ID existe
    if not created_user.id:
        raise RuntimeError("Usuario creado sin ID")
    
    # Convertir a string no opcional para las siguientes operaciones
    user_id = cast(str, created_user.id)
    
    print("\n✅ Usuario creado:")
    print(f"ID: {user_id}")
    print(f"Nombre: {created_user.full_name}")
    print(f"Email: {created_user.email}")
    
    # 2. Prueba de obtención por ID
    fetched_user = await user_repo.get(user_id)
    print("\n✅ Usuario obtenido por ID:")
    print(f"ID coincide: {user_id == fetched_user.id}") # type: ignore
    print(f"Nombre coincide: {created_user.full_name == fetched_user.full_name}") # type: ignore
    
    # 3. Prueba de actualización
    update_data = {"phone_number": "+573002222222", "apartment": "Torre Test, Apto 202"}
    updated_user = await user_repo.update(user_id, update_data)
    print("\n✅ Usuario actualizado:")
    print(f"Teléfono actualizado: {updated_user.phone_number}") # type: ignore
    print(f"Apartamento actualizado: {updated_user.apartment}") # type: ignore
    
    # 4. Prueba de búsqueda por query
    query_user = await user_repo.find_one({"email": "admin_test@condominio.com"})
    print("\n✅ Usuario encontrado por query:")
    print(f"ID encontrado: {query_user.id if query_user else 'No encontrado'}")
    
    # 5. Prueba de obtención múltiple
    all_users = await user_repo.get_multi()
    print("\n✅ Usuarios obtenidos (get_multi):")
    print(f"Total usuarios: {len(all_users)}")
    print(f"Primer usuario: {all_users[0].full_name if all_users else 'Ninguno'}")
    
    # 6. Prueba de búsqueda múltiple
    active_users = await user_repo.find_many({"status": "active"})
    print("\n✅ Usuarios activos encontrados:")
    print(f"Total activos: {len(active_users)}")
    
    # 7. Prueba de eliminación
    delete_result = await user_repo.delete(user_id)
    print("\n✅ Usuario eliminado:")
    print(f"Eliminación exitosa: {delete_result}")
    
    # 8. Verificación post-eliminación
    deleted_user_check = await user_repo.get(user_id)
    print(f"Usuario aún existe: {deleted_user_check is not None}")
    
    print("\n" + "="*50)
    print("FIN DE PRUEBAS DEL REPOSITORIO")
    print("="*50)
    
    yield
    
    await close_mongo_connection()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Pruebas de repositorio completadas. Ver consola para resultados."}