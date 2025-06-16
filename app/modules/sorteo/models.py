from datetime import datetime
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

# Esquema anidado para los ganadores y no ganadores dentro del resultado del sorteo
class LotteryParticipantResult(BaseModel):
    """
    Representa un participante en el sorteo y su resultado (ganador/no ganador).
    """
    user_id: str = Field(..., description="ID del usuario")
    cc: str = Field(..., description="Cédula de ciudadanía del usuario")
    full_name: str = Field(..., description="Nombre completo del usuario")
    apartment: str = Field(..., description="Apartamento del usuario")
    vehicle_type: Literal["automovil", "motocicleta"] = Field(..., description="Tipo de vehículo de la solicitud")
    license_plate: str = Field(..., description="Placa del vehículo")
    spot: Optional[str] = Field(None, description="Identificador del spot de parqueo asignado (si ganó)")
    request_id: str = Field(..., description="ID de la solicitud de parqueo asociada")

class LotteryResult(BaseModel):
    """
    Modelo de datos para el resultado de un Sorteo de Parqueo.
    Representa un documento en la colección 'lotteries'.
    """
    id: Optional[str] = Field(None, alias="_id") # Alias _id para mapear con MongoDB
    
    period: str = Field(
        ..., 
        min_length=7, 
        max_length=7, 
        pattern=r"^\d{4}-\d{2}$", 
        description="Período del sorteo en formato YYYY-MM (ej. '2025-07')"
    )
    total_car_spots_offered: int = Field(..., ge=0, description="Número total de espacios de carro ofrecidos en este sorteo.")
    total_moto_spots_offered: int = Field(..., ge=0, description="Número total de espacios de moto ofrecidos en este sorteo.")
    
    winners: List[LotteryParticipantResult] = Field(
        default_factory=list, 
        description="Lista de usuarios que ganaron un spot de parqueo en este sorteo."
    )
    non_winners: List[LotteryParticipantResult] = Field(
        default_factory=list, 
        description="Lista de usuarios que participaron pero no ganaron un spot de parqueo en este sorteo."
    )
    
    executed_at: datetime = Field(default_factory=datetime.utcnow, description="Fecha y hora en que se ejecutó el sorteo.")

    class Config:
        populate_by_name = True # Permite que los campos se mapeen por su alias (_id)
        json_schema_extra = {
            "example": {
                "period": "2025-07",
                "total_car_spots_offered": 10,
                "total_moto_spots_offered": 5,
                "winners": [
                    {
                        "user_id": "666c8a7f7b1e3e4d5f6a2b1c",
                        "cc": "1193597666",
                        "full_name": "Juan Pérez",
                        "apartment": "Torre 2, Apto 101",
                        "vehicle_type": "automovil",
                        "license_plate": "XYZ789",
                        "spot": "P1-A01",
                        "request_id": "666d9b8c7d1e3f4a5b6c2d1e"
                    }
                ],
                "non_winners": [
                    {
                        "user_id": "666c8a7f7b1e3e4d5f6a2b1d",
                        "cc": "1028345678",
                        "full_name": "Ana María Restrepo",
                        "apartment": "Torre 5, Apto 203",
                        "vehicle_type": "automovil",
                        "license_plate": "QWE123",
                        "spot": None,
                        "request_id": "666d9b8c7d1e3f4a5b6c2d1f"
                    }
                ],
                "executed_at": "2025-06-30T10:00:00Z"
            }
        }