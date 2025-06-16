from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator

# --- Esquemas de Entrada (Input Schemas) ---

class RequestCreate(BaseModel):
    """
    Esquema para que un residente cree una nueva solicitud de parqueo.
    El user_id, resident_cc y resident_full_name serán inyectados por el servicio
    desde el usuario autenticado.
    """
    vehicle_type: Literal["automovil", "motocicleta"] = Field(..., description="Tipo de vehículo solicitado")
    license_plate: str = Field(..., min_length=3, max_length=10, examples=["ABC123"], description="Placa del vehículo")
    description: Optional[str] = Field(None, max_length=500, examples=["Mi carro es un sedan."], description="Descripción adicional de la solicitud")
    disability: bool = Field(False, description="Indica si el residente tiene alguna discapacidad.")
    pay: bool = Field(False, description="Indica si el residente ya realizó el pago de la cuota.")
    lottery_period: str = Field(
        ..., 
        min_length=7, 
        max_length=7, 
        pattern=r"^\d{4}-\d{2}$", 
        examples=["2025-07"],
        description="Período de sorteo en formato YYYY-MM."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "vehicle_type": "automovil",
                "license_plate": "XYZ789",
                "description": "Necesito un espacio techado.",
                "disability": False,
                "pay": True,
                "lottery_period": "2025-07"
            }
        }

class RequestUpdateStatus(BaseModel):
    """
    Esquema para que un administrador actualice el estado de una solicitud.
    """
    status: Literal["pending", "accepted", "rejected"] = Field(..., description="Nuevo estado de la solicitud.")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "accepted"
            }
        }

# --- Esquemas de Salida (Output Schemas) ---

class RequestOut(BaseModel):
    """
    Esquema para la salida de datos de una solicitud de parqueo.
    """
    id: Optional[str] = Field(None, examples=["666c8a7f7b1e3e4d5f6a2b1e"])
    user_id: str
    resident_cc: str
    resident_full_name: str
    vehicle_type: Literal["automovil", "motocicleta"]
    license_plate: str
    description: Optional[str]
    disability: bool
    pay: bool
    status: Literal["pending", "accepted", "rejected"]
    lottery_period: str
    created_at: datetime
    updated_at: datetime
    
    @field_validator("id", mode="before")
    def convert_objectid_to_str(cls, v):
        """Convierte ObjectId a str para asegurar la compatibilidad con Pydantic."""
        if isinstance(v, datetime): # A veces el validator puede recibir otros tipos si no está bien encadenado.
            return str(v)
        return str(v) if v is not None else None

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat() # Asegura que datetime se serialice correctamente a ISO format
        }
        json_schema_extra = {
            "example": {
                "id": "666c8a7f7b1e3e4d5f6a2b1e",
                "user_id": "666c8a7f7b1e3e4d5f6a2b1c",
                "resident_cc": "1193597666",
                "resident_full_name": "Juan Pérez",
                "vehicle_type": "automovil",
                "license_plate": "ABC123",
                "description": "Descripcion de prueba.",
                "disability": False,
                "pay": True,
                "status": "pending",
                "lottery_period": "2025-07",
                "created_at": "2025-06-15T00:00:00.000Z",
                "updated_at": "2025-06-15T00:00:00.000Z"
            }
        }