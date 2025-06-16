from typing import AsyncGenerator, Generator, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from jose import JWTError

from app.database.mongodb import get_database
from app.core.security import decode_access_token
from app.modules.residentes.models import User # Necesitamos el modelo User para tipado
from app.shared.repository import BaseRepository

# Esquema de seguridad OAuth2 con password flow para el token.
# Indica a FastAPI que espere un token en el header "Authorization: Bearer <token>"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token") # 'tokenUrl' es la URL donde se obtiene el token

async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """
    Dependencia que proporciona una instancia de la base de datos a los endpoints.
    Asegura que la conexión se maneje correctamente.
    """
    db = get_database()
    # Esta es una dependencia asíncrona, 'yield' permite que el código después del yield
    # se ejecute después de que la respuesta haya sido enviada.
    try:
        yield db
    finally:
        # En FastAPI, para 'yield' con dependencias de DB, no se cierra aquí.
        # La conexión global se cierra en los eventos de shutdown de la app (main.py).
        pass

async def get_current_user(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    """
    Dependencia para obtener el usuario autenticado a partir del token JWT.
    Retorna el objeto User si el token es válido y el usuario está activo.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Decodificar el token para obtener los datos del payload
    token_data = decode_access_token(token)
    if token_data is None:
        raise credentials_exception

    # El ID del usuario está en el campo 'id' del payload
    user_id = token_data.id
    if user_id is None:
        raise credentials_exception

    # Recuperar el usuario de la base de datos usando el ID del token
    user_repository = BaseRepository(db["users"], User)
    current_user = await user_repository.get(user_id)
    
    if current_user is None:
        raise credentials_exception
    
    # Opcional: Puedes añadir una verificación de estado aquí si no lo hiciste en el servicio de autenticación
    # if current_user.status != "active":
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Tu cuenta no está activa. Contacta al administrador."
    #     )

    return current_user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependencia para obtener el usuario autenticado y asegurar que esté activo.
    """
    if current_user.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario inactivo")
    return current_user

async def get_current_active_admin_user(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """
    Dependencia para obtener el usuario autenticado y activo y asegurar que sea administrador.
    """
    if current_user.role != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador."
        )
    return current_user