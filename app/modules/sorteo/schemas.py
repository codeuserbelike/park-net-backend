from datetime import datetime
from typing import Optional, Literal, List
from pydantic import BaseModel, Field, field_validator

# --- Esquemas de Entrada (Input Schemas) ---

class LotteryCreate(BaseModel):
    """
    Esquema para iniciar un nuevo sorteo.
    Define el período y la cantidad de spots disponibles.
    """
    period: str = Field(
        ...,
        min_length=7,
        max_length=7,
        pattern=r"^\d{4}-\d{2}$",
        examples=["2025-07"],
        description="Período para el cual se realizará el sorteo (YYYY-MM)."
    )
    num_car_spots: int = Field(
        ..., 
        ge=0, 
        description="Número de espacios de parqueo para automóviles disponibles para el sorteo."
    )
    num_moto_spots: int = Field(
        ..., 
        ge=0, 
        description="Número de espacios de parqueo para motocicletas disponibles para el sorteo."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "period": "2025-07",
                "num_car_spots": 10,
                "num_moto_spots": 5
            }
        }

# --- Esquemas de Salida (Output Schemas) ---

class LotteryAssignmentOut(BaseModel):
    """
    Esquema para representar una asignación de parqueo individual dentro del resultado del sorteo.
    """
    user_id: str
    cc: str
    full_name: str
    apartment: str
    vehicle_type: Literal["automovil", "motocicleta"]
    license_plate: str
    spot: Optional[str] = Field(None, description="Identificador del spot de parqueo asignado (si ganó)")
    request_id: str

class LotteryResultOut(BaseModel):
    """
    Esquema para la salida completa del resultado de un sorteo.
    """
    id: Optional[str] = Field(None, examples=["666c8a7f7b1e3e4d5f6a2b1f"])
    period: str
    total_car_spots_offered: int
    total_moto_spots_offered: int
    winners: List[LotteryAssignmentOut]
    non_winners: List[LotteryAssignmentOut]
    executed_at: datetime

    @field_validator("id", mode="before")
    def convert_objectid_to_str(cls, v):
        """Convierte ObjectId a str para asegurar la compatibilidad con Pydantic."""
        return str(v) if v is not None else None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat() # Asegura que datetime se serialice correctamente a ISO format
        }
        json_schema_extra = {
            "example": {
                "id": "666c8a7f7b1e3e4d5f6a2b1f",
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


class MyAssignmentOut(BaseModel):
    """
    Esquema para la salida de la asignación de parqueo de un usuario específico.
    """
    period: str
    vehicle_type: Literal["automovil", "motocicleta"]
    license_plate: str
    spot: Optional[str] = Field(None, description="Identificador del spot de parqueo asignado")
    
    class Config:
        json_schema_extra = {
            "example": {
                "period": "2025-07",
                "vehicle_type": "automovil",
                "license_plate": "XYZ789",
                "spot": "P1-A01"
            }
        }