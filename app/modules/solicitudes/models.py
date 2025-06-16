from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field
from bson import ObjectId # Importar ObjectId para referencia interna si se necesitara tipado exacto, aunque lo manejaremos como str

class Request(BaseModel):
    """
    Modelo de datos para las Solicitudes de Parqueo.
    Representa un documento en la colección 'requests'.
    """
    id: Optional[str] = Field(None, alias="_id") # Alias _id para mapear con MongoDB
    
    # Información del residente (referencia directa al usuario)
    user_id: str = Field(..., description="ID del usuario (residente) que realiza la solicitud")
    resident_cc: str = Field(..., description="Cédula de ciudadanía del residente (copia para fácil acceso)")
    resident_full_name: str = Field(..., description="Nombre completo del residente (copia para fácil acceso)")

    # Información del vehículo
    vehicle_type: Literal["automovil", "motocicleta"] = Field(..., description="Tipo de vehículo solicitado")
    license_plate: str = Field(..., min_length=3, max_length=10, description="Placa del vehículo")
    
    description: Optional[str] = Field(None, max_length=500, description="Descripción adicional de la solicitud")
    disability: bool = Field(False, description="Indica si el residente tiene alguna discapacidad (prioridad para sorteo)")
    pay: bool = Field(False, description="Indica si el residente ya realizó el pago de la cuota (prioridad para sorteo)")
    
    # Estado de la solicitud
    status: Literal["pending", "accepted", "rejected"] = Field(
        default="pending",
        description="Estado actual de la solicitud: pendiente, aceptada o rechazada."
    )
    
    # Período del sorteo
    lottery_period: str = Field(
        ..., 
        min_length=7, 
        max_length=7, 
        pattern=r"^\d{4}-\d{2}$", 
        description="Período de sorteo en formato YYYY-MM (ej. '2025-07')"
    )

    # Marcas de tiempo
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True # Permite que los campos se mapeen por su alias (_id)
        json_schema_extra = {
            "example": {
                "user_id": "666c8a7f7b1e3e4d5f6a2b1c",
                "resident_cc": "1193597666",
                "resident_full_name": "Juan Pérez",
                "vehicle_type": "automovil",
                "license_plate": "XYZ789",
                "description": "Necesito un espacio amplio.",
                "disability": False,
                "pay": True,
                "status": "pending",
                "lottery_period": "2025-07"
            }
        }