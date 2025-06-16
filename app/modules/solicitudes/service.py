# app/modules/solicitudes/service.py
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId

from app.modules.solicitudes.models import Request
from app.modules.solicitudes.schemas import RequestCreate, RequestUpdateStatus
from app.modules.residentes.models import User
from app.shared.repository import BaseRepository

class RequestService:
    """
    Servicio de lógica de negocio para la gestión de solicitudes de parqueo.
    """
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.request_repository = BaseRepository(self.db["requests"], Request)
        self.user_repository = BaseRepository(self.db["users"], User)

    async def create_request(self, request_data: RequestCreate, current_user: User) -> Request:
        """
        Crea una nueva solicitud de parqueo por parte de un residente.
        Verifica que no exista una solicitud pendiente o aceptada para el mismo tipo de vehículo y período.
        
        Reglas:
        1. Si ya existe una solicitud (pendiente o aceptada) para el mismo tipo de vehículo y período, 
        se rechaza la nueva solicitud con un error.
        2. Si no existe solicitud para ese período o si existe pero está rechazada, se permite crear una nueva solicitud.
        3. Las solicitudes para diferentes períodos son completamente independientes.
        """
        # Verificar si el usuario ya tiene una solicitud pendiente o aceptada para el mismo tipo de vehículo y período
        existing_request = await self.request_repository.find_one({
            "user_id": str(current_user.id),
            "vehicle_type": request_data.vehicle_type,
            "lottery_period": request_data.lottery_period,
            "status": {"$in": ["pending", "accepted"]}
        })

        if existing_request:
            # Si existe una solicitud activa (pendiente o aceptada) para el mismo período, rechazamos la nueva
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya tienes una solicitud {existing_request.status} para '{request_data.vehicle_type}' en el período {request_data.lottery_period}."
            )

        # Construir el objeto Request
        new_request = Request(
            user_id=str(current_user.id),
            resident_cc=current_user.cc,
            resident_full_name=current_user.full_name,
            vehicle_type=request_data.vehicle_type,
            license_plate=request_data.license_plate,
            description=request_data.description,
            disability=request_data.disability,
            pay=request_data.pay,
            lottery_period=request_data.lottery_period,
            status="pending"
        ) # type: ignore
        
        created_request = await self.request_repository.create(new_request)
        return created_request

    async def get_request_by_id(self, request_id: str) -> Request:
        """
        Obtiene una solicitud por su ID.
        """
        request = await self.request_repository.get(request_id)
        if not request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud no encontrada.")
        return request

    async def get_user_requests(self, user_id: str, skip: int = 0, limit: int = 100) -> List[Request]:
        """
        Obtiene todas las solicitudes de un usuario específico.
        """
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de usuario inválido.")
            
        # CORRECCIÓN: Usar find_many en lugar de find
        requests = await self.request_repository.find_many({"user_id": user_id}, skip=skip, limit=limit)
        return requests

    async def get_all_requests(
        self, 
        status_filter: Optional[str] = None, 
        lottery_period_filter: Optional[str] = None, 
        skip: int = 0, 
        limit: int = 200
    ) -> List[Request]:
        """
        Obtiene una lista de todas las solicitudes, con filtros y paginación.
        Prioriza el orden: pending, then accepted, then rejected.
        """
        query = {}
        if status_filter:
            query["status"] = status_filter
        if lottery_period_filter:
            query["lottery_period"] = lottery_period_filter

        # CORRECCIÓN: Usar find_many en lugar de find
        all_requests = await self.request_repository.find_many(query, skip=0, limit=0)  # Obtener todos sin paginación inicial
        
        # Ordenar en Python: pending > accepted > rejected
        status_order = {"pending": 0, "accepted": 1, "rejected": 2}
        all_requests.sort(key=lambda req: status_order.get(req.status, 99))
        
        # Aplicar paginación después del ordenamiento
        return all_requests[skip : skip + limit]

    async def update_request_status(self, request_id: str, new_status: str) -> Request:
        """
        Permite a un administrador actualizar el estado de una solicitud.
        También actualiza los slots de vehículos del usuario si la solicitud es aceptada/rechazada.
        """
        request = await self.request_repository.get(request_id)
        if not request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud no encontrada.")

        if request.status == new_status:
            return request

        update_data = {"status": new_status, "updated_at": datetime.utcnow()}
        updated_request = await self.request_repository.update(request_id, update_data)

        if not updated_request:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo actualizar el estado de la solicitud.")
        
        # Actualizar el campo 'vehicle_slots' del usuario
        user = await self.user_repository.get(updated_request.user_id)
        if user:
            vehicle_type = updated_request.vehicle_type
            user_vehicle_slots = user.vehicle_slots.copy()  # Crear copia para modificar
            
            if new_status == "accepted":
                user_vehicle_slots[vehicle_type] = {
                    "available": False,
                    "request_id": str(updated_request.id)
                }
            elif new_status in ["rejected", "pending"]:
                if user_vehicle_slots.get(vehicle_type, {}).get("request_id") == str(updated_request.id):
                    user_vehicle_slots[vehicle_type] = {
                        "available": True,
                        "request_id": None
                    }
                
            # Persistir los cambios en el usuario
            await self.user_repository.update(
                str(user.id), 
                {"vehicle_slots": user_vehicle_slots, "updated_at": datetime.utcnow()}
            )

        return updated_request

    async def delete_request(self, request_id: str) -> Dict[str, str]:
        """
        Elimina una solicitud por su ID.
        """
        request_to_delete = await self.request_repository.get(request_id)
        if not request_to_delete:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud no encontrada.")
            
        deleted = await self.request_repository.delete(request_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo eliminar la solicitud.")
        
        # Liberar el slot del usuario si la solicitud estaba aceptada
        if request_to_delete.status == "accepted":
            user = await self.user_repository.get(request_to_delete.user_id)
            if user:
                vehicle_type = request_to_delete.vehicle_type
                user_vehicle_slots = user.vehicle_slots.copy()
                
                if user_vehicle_slots.get(vehicle_type, {}).get("request_id") == str(request_to_delete.id):
                    user_vehicle_slots[vehicle_type] = {
                        "available": True,
                        "request_id": None
                    }
                    
                    await self.user_repository.update(
                        str(user.id), 
                        {"vehicle_slots": user_vehicle_slots, "updated_at": datetime.utcnow()}
                    )
        
        return {"message": "Solicitud eliminada exitosamente."}