from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, EmailStr

class User(BaseModel):
    """
    Modelo de datos para los usuarios (Residentes y Administradores).
    Representa un documento en la colección 'users'.
    """
    id: Optional[str] = Field(None)
    full_name: str = Field(..., min_length=3, max_length=100)
    cc: str = Field(
        ...,
        min_length=6,
        max_length=20,
        description="Cédula de ciudadanía, debe ser única en la base de datos"
    )
    email: EmailStr = Field(
        ...,
        description="Correo electrónico, usado para login. Debe ser único en la base de datos",
        examples=["usuario@condominio.com"]
    )
    hashed_password: str = Field(
        ...,
        description="Contraseña hasheada usando bcrypt"
    )
    apartment: str = Field(
        ...,
        min_length=3,
        max_length=50,
        examples=["Torre 1, Apto 101"]
    )
    phone_number: str = Field(
        ...,
        min_length=7,
        max_length=20,
        examples=["+573001234567"]
    )
    role: Literal["residente", "administrador"] = Field(
        default="residente",
        description="Rol del usuario en el sistema"
    )
    status: Literal["pending_approval", "active", "inactive"] = Field(
        default="pending_approval",
        description="Estado del usuario en el flujo de aprobación"
    )
    vehicle_slots: dict = Field(
        default_factory=lambda: {
            "automovil": {"available": True, "request_id": None},
            "motocicleta": {"available": True, "request_id": None}
        },
        description="Estado de asignación de puestos para vehículos"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Juan Pérez",
                "cc": "123456789",
                "email": "juan@condominio.com",
                "apartment": "Torre 1, Apto 101",
                "phone_number": "+573001234567",
                "role": "residente",
                "status": "pending_approval",
                "vehicle_slots": {
                    "automovil": {"available": True, "request_id": None},
                    "motocicleta": {"available": True, "request_id": None}
                }
            }
        }