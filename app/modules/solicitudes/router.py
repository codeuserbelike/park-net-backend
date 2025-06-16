from typing import Annotated, List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.mongodb import get_database
from app.modules.solicitudes.service import RequestService
from app.modules.solicitudes.schemas import RequestCreate, RequestUpdateStatus, RequestOut
from app.modules.residentes.models import User # Necesario para los tipos de dependencia
from app.core.dependencies import get_current_active_user, get_current_active_admin_user

router = APIRouter(prefix="/requests", tags=["Requests"])

@router.post("/", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
async def create_request(
    request_data: RequestCreate,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    current_user: Annotated[User, Depends(get_current_active_user)] # Solo usuarios activos pueden crear solicitudes
):
    """
    Crea una nueva solicitud de parqueo para el usuario autenticado.
    """
    request_service = RequestService(db)
    new_request = await request_service.create_request(request_data, current_user)
    return new_request

@router.get("/me", response_model=List[RequestOut])
async def get_my_requests(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    current_user: Annotated[User, Depends(get_current_active_user)], # Un usuario puede ver sus propias solicitudes
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200)
):
    """
    Obtiene todas las solicitudes de parqueo del usuario actualmente autenticado.
    """
    request_service = RequestService(db)
    requests = await request_service.get_user_requests(str(current_user.id), skip=skip, limit=limit)
    return requests

@router.get("/{request_id}", response_model=RequestOut)
async def get_request_details(
    request_id: str,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    current_user: Annotated[User, Depends(get_current_active_user)] # Un usuario puede ver su propia solicitud, un admin cualquier solicitud
):
    """
    Obtiene los detalles de una solicitud específica por su ID.
    Los usuarios pueden ver sus propias solicitudes. Los administradores pueden ver cualquier solicitud.
    """
    request_service = RequestService(db)
    request = await request_service.get_request_by_id(request_id)

    # Lógica de autorización: Un usuario solo puede ver sus propias solicitudes, a menos que sea un admin
    if str(current_user.id) != request.user_id and current_user.role != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver esta solicitud."
        )
    return request

@router.get("/", response_model=List[RequestOut])
async def get_all_requests(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    current_admin: Annotated[User, Depends(get_current_active_admin_user)], # Solo administradores pueden listar todas las solicitudes
    status_filter: Optional[Literal["pending", "accepted", "rejected"]] = Query(None, description="Filtrar por estado de la solicitud"),
    lottery_period_filter: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$", description="Filtrar por período de sorteo (YYYY-MM)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200)
):
    """
    Obtiene una lista de todas las solicitudes de parqueo con filtros y paginación.
    Requiere permisos de administrador.
    Las solicitudes se ordenan por defecto: pendientes, luego aceptadas, luego rechazadas.
    """
    request_service = RequestService(db)
    requests = await request_service.get_all_requests(
        status_filter=status_filter,
        lottery_period_filter=lottery_period_filter,
        skip=skip,
        limit=limit
    )
    return requests

@router.put("/{request_id}/status", response_model=RequestOut)
async def update_request_status(
    request_id: str,
    status_update: RequestUpdateStatus,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    current_admin: Annotated[User, Depends(get_current_active_admin_user)] # Solo administradores pueden actualizar el estado
):
    """
    Actualiza el estado de una solicitud de parqueo específica por su ID.
    Requiere permisos de administrador.
    """
    request_service = RequestService(db)
    updated_request = await request_service.update_request_status(request_id, status_update.status)
    return updated_request

@router.delete("/{request_id}", status_code=status.HTTP_200_OK)
async def delete_request(
    request_id: str,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    current_admin: Annotated[User, Depends(get_current_active_admin_user)] # Solo administradores pueden eliminar solicitudes
):
    """
    Elimina una solicitud de parqueo por su ID.
    Requiere permisos de administrador.
    """
    request_service = RequestService(db)
    result = await request_service.delete_request(request_id)
    return result