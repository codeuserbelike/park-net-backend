from typing import Annotated, List, Optional, Literal # Importar Literal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.mongodb import get_database
from app.modules.residentes.service import ResidentService
from app.modules.residentes.schemas import ResidentCreate, ResidentUpdate, AdminUserUpdate, ResidentOut
from app.modules.residentes.models import User
from app.core.dependencies import get_current_active_user, get_current_active_admin_user

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", response_model=ResidentOut, status_code=status.HTTP_201_CREATED)
async def create_user_by_admin(
    user_data: ResidentCreate,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    current_admin: Annotated[User, Depends(get_current_active_admin_user)] # Solo administradores pueden crear usuarios
):
    """
    Crea un nuevo usuario. Por defecto, crea un residente en estado 'pending_approval'.
    Un administrador puede especificar el rol y el estado inicial del usuario.
    Requiere permisos de administrador.
    """
    resident_service = ResidentService(db)
    # user_data.role y user_data.status ahora pueden ser Optional en ResidentCreate
    new_user = await resident_service.create_user(
        user_data,
        role=user_data.role if user_data.role else "residente", # Usar el rol proporcionado o el default
        status_initial=user_data.status if user_data.status else "pending_approval" # Usar el estado proporcionado o el default
    )
    return new_user

@router.get("/", response_model=List[ResidentOut])
async def get_all_users(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    current_admin: Annotated[User, Depends(get_current_active_admin_user)], # Solo administradores pueden listar todos
    status_filter: Optional[Literal["pending_approval", "active", "inactive"]] = Query(
        None, 
        description="Filtrar por estado del usuario."
    ),
    role_filter: Optional[Literal["residente", "administrador"]] = Query(
        None, 
        description="Filtrar por rol del usuario."
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200)
):
    """
    Obtiene una lista de todos los usuarios con paginación y filtros opcionales.
    Requiere permisos de administrador.
    Los usuarios se ordenan por defecto: pendientes de aprobación, luego activos, luego inactivos.
    """
    resident_service = ResidentService(db)
    users = await resident_service.get_all_users(
        skip=skip, 
        limit=limit,
        status_filter=status_filter, # Pasar el filtro de estado
        role_filter=role_filter # Pasar el filtro de rol
    )
    return users

@router.get("/{identifier}", response_model=ResidentOut)
async def get_user(
    identifier: str, # Este parámetro puede ser ID o CC
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    current_user: Annotated[User, Depends(get_current_active_user)] # Cualquier usuario activo puede ver su perfil
):
    """
    Obtiene un usuario por su ID o Cédula de Ciudadanía (CC).
    Los usuarios pueden ver su propio perfil. Los administradores pueden ver cualquier perfil.
    """
    resident_service = ResidentService(db)
    user = await resident_service._get_user_by_identifier(identifier)

    # Lógica de autorización: Un usuario solo puede ver su propio perfil, a menos que sea un admin
    if str(current_user.id) != str(user.id) and current_user.cc != user.cc and current_user.role != "administrador": # type: ignore
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver el perfil de este usuario."
        )
    return user

@router.put("/me", response_model=ResidentOut)
async def update_my_profile(
    user_update: ResidentUpdate,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    current_user: Annotated[User, Depends(get_current_active_user)] # Un usuario puede actualizar su propio perfil
):
    """
    Actualiza la información del perfil del usuario actualmente autenticado.
    """
    resident_service = ResidentService(db)
    # El usuario solo puede actualizar su propio perfil, usamos su propio ID
    updated_user = await resident_service.update_user(str(current_user.id), user_update)
    return updated_user

@router.put("/{identifier}", response_model=ResidentOut)
async def admin_update_user(
    identifier: str, # Este parámetro puede ser ID o CC
    user_update: AdminUserUpdate,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    current_admin: Annotated[User, Depends(get_current_active_admin_user)] # Solo administradores pueden actualizar cualquier usuario
):
    """
    Actualiza la información de un usuario específico por su ID o Cédula de Ciudadanía (CC).
    Requiere permisos de administrador.
    Permite cambiar el rol y el estado de aprobación del usuario.
    """
    resident_service = ResidentService(db)
    updated_user = await resident_service.admin_update_user(identifier, user_update)
    return updated_user

@router.delete("/{identifier}", status_code=status.HTTP_200_OK)
async def delete_user_by_admin(
    identifier: str, # Este parámetro puede ser ID o CC
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    current_admin: Annotated[User, Depends(get_current_active_admin_user)] # Solo administradores pueden eliminar usuarios
):
    """
    Elimina un usuario por su ID o Cédula de Ciudadanía (CC).
    Requiere permisos de administrador.
    """
    resident_service = ResidentService(db)
    result = await resident_service.delete_user(identifier)
    return result