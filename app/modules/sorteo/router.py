from typing import Annotated, List, Optional, Literal # Asegúrate de importar Literal
from fastapi import APIRouter, Depends, HTTPException, Response, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.mongodb import get_database
from app.modules.sorteo.service import LotteryService
from app.modules.sorteo.schemas import LotteryCreate, LotteryResultOut, MyAssignmentOut
from app.modules.residentes.models import User
from app.core.dependencies import get_current_active_admin_user, get_current_active_user

router = APIRouter(prefix="/lottery", tags=["Lottery"])

@router.post("/execute", response_model=LotteryResultOut, status_code=status.HTTP_201_CREATED)
async def execute_lottery_endpoint(
    lottery_data: LotteryCreate,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    current_admin: Annotated[User, Depends(get_current_active_admin_user)] # Solo administradores pueden ejecutar el sorteo
):
    """
    ## Ejecutar el Sorteo de Parqueo
    
    Permite a un **administrador** ejecutar el sorteo de parqueo para un período específico.
    Se deben especificar el número de espacios disponibles para automóviles y motocicletas.
    
    - **period**: Período del sorteo en formato `YYYY-MM` (ej. "2025-07").
    - **num_car_spots**: Cantidad de espacios disponibles para automóviles.
    - **num_moto_spots**: Cantidad de espacios disponibles para motocicletas.
    
    Retorna el resultado detallado del sorteo, incluyendo ganadores y no ganadores.
    """
    lottery_service = LotteryService(db)
    result = await lottery_service.execute_lottery(lottery_data)
    return result

@router.get("/{lottery_period}", response_model=LotteryResultOut)
async def get_lottery_results_by_period(
    lottery_period: str,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    current_admin: Annotated[User, Depends(get_current_active_admin_user)], # Solo administradores pueden ver los resultados completos
    # Nuevo parámetro de consulta para filtrar por tipo de vehículo
    vehicle_type: Optional[Literal["automovil", "motocicleta"]] = Query(
        None, 
        description="Filtrar los ganadores por tipo de vehículo (automovil o motocicleta)."
    )
):
    """
    ## Obtener Resultados de Sorteo por Período
    
    Permite a un **administrador** consultar el resultado detallado de un sorteo 
    anteriormente ejecutado para un período específico (ej. "2025-07").
    
    Opcionalmente, puede **filtrar a los ganadores** por tipo de vehículo (automóvil o motocicleta).
    
    Retorna el objeto completo del sorteo con ganadores y no ganadores.
    Si se aplica un filtro de `vehicle_type`, solo la lista de `winners` en la respuesta se ajustará.
    """
    lottery_service = LotteryService(db)
    # Pasa el parámetro de filtro directamente al servicio
    result = await lottery_service.get_lottery_result(lottery_period, vehicle_type=vehicle_type) 
    
    return result

@router.get("/my-assignment/{lottery_period}", response_model=List[MyAssignmentOut])
async def get_my_lottery_assignment(
    lottery_period: str,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    current_user: Annotated[User, Depends(get_current_active_user)] # Cualquier usuario activo puede ver su asignación
):
    """
    ## Consultar Mi Asignación de Parqueo
    
    Permite a un **usuario autenticado** (residente o administrador) consultar si 
    se le ha asignado un espacio de parqueo para un período específico.
    
    Retorna una lista de asignaciones si el usuario ganó un spot para ese período 
    (puede incluir asignaciones para automóvil y/o motocicleta).
    Si no hay asignaciones, retorna una lista vacía.
    """
    lottery_service = LotteryService(db)
    # Convertir ObjectId del usuario a string antes de pasarlo al servicio
    user_id_str = str(current_user.id) if current_user.id else ""
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de usuario no disponible.")
        
    my_assignments = await lottery_service.get_my_assignment(user_id_str, lottery_period)
    return my_assignments

@router.delete("/{lottery_period}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lottery_results(
    lottery_period: str,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    current_admin: Annotated[User, Depends(get_current_active_admin_user)] # Solo administradores pueden borrar sorteos
):
    """
    ## Eliminar un Sorteo por Período
    
    Permite a un **administrador** eliminar un sorteo y todos sus resultados
    para un período específico (ej. "2025-07").
    
    - **lottery_period**: Período del sorteo a eliminar en formato `YYYY-MM`.
    
    Retorna un estado `204 No Content` si el sorteo fue eliminado exitosamente.
    Retorna `404 Not Found` si el sorteo no existe.
    """
    lottery_service = LotteryService(db)
    result = await lottery_service.delete_lottery_result(lottery_period)
    return result