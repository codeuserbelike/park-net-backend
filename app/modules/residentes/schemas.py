from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, EmailStr, field_validator

# --- Esquemas de Entrada (Input Schemas) ---

class ResidentCreate(BaseModel):
    """
    Esquema para crear un nuevo residente.
    Incluye la contraseña en texto plano, que será hasheada por el servicio.
    """
    full_name: str = Field(..., min_length=3, max_length=100, examples=["Ana María Restrepo"])
    cc: str = Field(
        ...,
        min_length=6,
        max_length=20,
        examples=["1028345678"],
        description="Cédula de ciudadanía, debe ser única."
    )
    email: EmailStr = Field(
        ...,
        examples=["ana.restrepo@condominio.com"],
        description="Correo electrónico, usado para login y debe ser único."
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=50,
        examples=["passwordSeguro123"],
        description="Contraseña del usuario en texto plano."
    )
    apartment: str = Field(
        ...,
        min_length=3,
        max_length=50,
        examples=["Torre 5, Apto 203"]
    )
    phone_number: str = Field(
        ...,
        min_length=7,
        max_length=20,
        examples=["+573109876543"]
    )
    # Permite al admin definir el rol y estado inicial si usa este esquema
    role: Optional[Literal["residente", "administrador"]] = Field(
        "residente", # Default si no se especifica, pero se puede sobrescribir
        description="Rol del usuario en el sistema."
    )
    status: Optional[Literal["pending_approval", "active", "inactive"]] = Field(
        "pending_approval", # Default si no se especifica
        description="Estado del usuario en el flujo de aprobación (pending_approval, active, inactive)."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Ana María Restrepo",
                "cc": "1028345678",
                "email": "ana.restrepo@condominio.com",
                "password": "SecurePassword123",
                "apartment": "Torre 5, Apto 203",
                "phone_number": "+573109876543"
                # "role": "residente", # Estos campos son opcionales en el input si el admin los quiere forzar
                # "status": "pending_approval"
            }
        }


class ResidentUpdate(BaseModel):
    """
    Esquema para actualizar la información de un residente.
    Todos los campos son opcionales para permitir actualizaciones parciales.
    """
    full_name: Optional[str] = Field(None, min_length=3, max_length=100, examples=["Ana M. Restrepo"])
    email: Optional[EmailStr] = Field(None, examples=["ana.restrepo_new@condominio.com"])
    phone_number: Optional[str] = Field(None, min_length=7, max_length=20, examples=["+573109876543"])
    password: Optional[str] = Field(None, min_length=8, max_length=50, description="Solo si se desea cambiar la contraseña.")
    # El CC, rol y status generalmente no se actualizan por el propio residente
    # Si el administrador necesita actualizar el status o rol, se manejaría con otro esquema específico de administración.


class AdminUserUpdate(BaseModel):
    """
    Esquema para que un administrador actualice la información de cualquier usuario,
    incluyendo su rol y estado de aprobación.
    """
    full_name: Optional[str] = Field(None, min_length=3, max_length=100) # Se añade para que el admin pueda cambiarlo
    cc: Optional[str] = Field(None, min_length=6, max_length=20)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=50, description="Contraseña en texto plano para hashear")
    apartment: Optional[str] = Field(None, min_length=3, max_length=50)
    phone_number: Optional[str] = Field(None, min_length=7, max_length=20)
    role: Optional[Literal["residente", "administrador"]] = None
    status: Optional[Literal["pending_approval", "active", "inactive"]] = Field(
        None, 
        description="Estado de aprobación del usuario: 'pending_approval', 'active', 'inactive'."
    )
    # No se incluye vehicle_slots aquí, ya que su gestión es más compleja y ligada a las solicitudes.

# --- Esquemas de Salida (Output Schemas) ---

class VehicleSlotInfo(BaseModel):
    """
    Esquema para la información detallada de un slot de vehículo.
    """
    available: bool = Field(..., description="Indica si el slot está disponible")
    request_id: Optional[str] = Field(None, description="ID de la solicitud asociada, si está asignado")

class ResidentOut(BaseModel):
    """
    Esquema para la salida de datos de un residente.
    No incluye la contraseña hasheada para seguridad.
    """
    id: Optional[str] = Field(default=None)
    full_name: str
    cc: str
    email: EmailStr
    apartment: str
    phone_number: str
    role: Literal["residente", "administrador"]
    status: Literal["pending_approval", "active", "inactive"]
    vehicle_slots: dict[Literal["automovil", "motocicleta"], VehicleSlotInfo] # Mapea las claves a VehicleSlotInfo
    
    # Opcional: Validador para convertir ObjectId a string si es necesario
    @field_validator("id", mode="before")
    def validate_id(cls, v):
        if hasattr(v, "id"):
            return str(v.id)
        return str(v)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "666c8a7f7b1e3e4d5f6a2b1c",
                "full_name": "Juan David Pérez",
                "cc": "1193597666",
                "email": "juan.perez@email.com",
                "apartment": "Torre 2, Apto 101",
                "phone_number": "+573001234567",
                "role": "residente",
                "status": "pending_approval",
                "vehicle_slots": {
                    "automovil": {"available": True, "request_id": None},
                    "motocicleta": {"available": True, "request_id": None}
                }
            }
        }