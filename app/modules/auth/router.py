from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm # Para el endpoint de token

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.mongodb import get_database
from app.modules.auth.service import AuthService
from app.modules.auth.schemas import Token, UserLogin
from app.modules.residentes.models import User
from app.modules.residentes.schemas import ResidentCreate, ResidentOut # Para el registro de residentes
from app.core.dependencies import get_current_user, get_current_active_admin_user # Para proteger rutas de prueba

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=ResidentOut, status_code=status.HTTP_201_CREATED)
async def register_new_resident(
    user_data: ResidentCreate,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]
):
    """
    Permite el registro de un nuevo residente.
    Por defecto, el estado del usuario será 'pending_approval' y el rol 'residente'.
    """
    auth_service = AuthService(db)
    new_user = await auth_service.register_user(user_data)
    return new_user

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], # Formulario estándar para OAuth2
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]
):
    """
    Obtiene un token de acceso JWT.
    Requiere 'username' (que será el CC) y 'password'.
    """
    # OAuth2PasswordRequestForm usa 'username' por convención, lo mapeamos a 'cc'
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cédula de ciudadanía o contraseña incorrectos, o usuario inactivo.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = await auth_service.create_access_token_for_user(user)
    return token

@router.get("/me", response_model=ResidentOut)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Obtiene la información del usuario actualmente autenticado.
    Requiere un token JWT válido.
    """
    # El objeto 'current_user' ya ha sido validado por la dependencia get_current_user
    return current_user

@router.get("/admin-only", status_code=status.HTTP_200_OK)
async def admin_only_endpoint(
    current_admin: Annotated[User, Depends(get_current_active_admin_user)]
):
    """
    Ejemplo de endpoint protegido que solo un administrador activo puede acceder.
    """
    return {"message": f"Bienvenido administrador {current_admin.full_name}! Tienes acceso a esta ruta secreta."}