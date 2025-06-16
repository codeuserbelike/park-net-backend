from typing import Optional
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.modules.residentes.models import User # Necesitamos el modelo User
from app.modules.residentes.schemas import ResidentCreate # Para el registro
from app.modules.auth.schemas import Token # Para el token de respuesta
from app.shared.repository import BaseRepository # Usaremos el BaseRepository

class AuthService:
    """
    Servicio de autenticación para gestionar el registro y login de usuarios.
    GRASP: Information Expert - Es responsable de la lógica de negocio de autenticación.
    """
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.user_repository = BaseRepository(self.db["users"], User) # Instancia el repositorio para la colección 'users'

    async def register_user(self, user_data: ResidentCreate) -> Optional[User]:
        # Verificaciones de unicidad (email y cc)
        existing_user_email = await self.user_repository.find_one({"email": user_data.email})
        if existing_user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está registrado."
            )
            
        existing_user_cc = await self.user_repository.find_one({"cc": user_data.cc})
        if existing_user_cc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La cédula de ciudadanía ya está registrada."
            )

        # Hashear la contraseña
        hashed_password = get_password_hash(user_data.password)
        
        # Crear la instancia de User directamente
        new_user = User(
            full_name=user_data.full_name,
            cc=user_data.cc,
            email=user_data.email,
            hashed_password=hashed_password,
            apartment=user_data.apartment,
            phone_number=user_data.phone_number,
            # No especificamos role ni status, Pydantic usará los valores por defecto
        ) # type: ignore
        
        # Guardar en la base de datos
        created_user = await self.user_repository.create(new_user)
        
        return created_user

    async def authenticate_user(self, cc: str, password: str) -> Optional[User]:
        """
        Autentica un usuario verificando su CC y contraseña.
        Retorna el objeto User si la autenticación es exitosa y el usuario está activo.
        """
        user = await self.user_repository.find_one({"cc": cc})
        if not user:
            return None # Usuario no encontrado

        # Verificar la contraseña
        if not verify_password(password, user.hashed_password):
            return None # Contraseña incorrecta
        
        # Verificar el estado del usuario (debe estar activo para iniciar sesión)
        if user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tu cuenta está en estado '{user.status}'. Contacta al administrador."
            )

        return user

    async def create_access_token_for_user(self, user: User) -> Token:
        """
        Crea un token de acceso JWT para un usuario dado.
        """
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # El payload del token debe contener información mínima pero suficiente para identificar
        # al usuario y sus permisos (rol).
        # Convertimos el ObjectId del usuario a string para el payload del token.
        token_data = {
            "id": str(user.id),
            "role": user.role,
            "email": user.email # Incluir email puede ser útil, aunque el login sea por cc
        }
        
        access_token = create_access_token(
            data=token_data, expires_delta=access_token_expires
        )
        return Token(access_token=access_token, token_type="bearer")