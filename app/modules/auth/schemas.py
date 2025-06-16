from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# --- Esquemas de Autenticación ---

class UserLogin(BaseModel):
    """
    Esquema para las credenciales de inicio de sesión.
    """
    cc: str = Field(
        ...,
        min_length=6,
        max_length=20,
        examples=["1028345678"]
    )
    password: str = Field(..., examples=["passwordAdminSeguro"])

    class Config:
        json_schema_extra = {
            "example": {
                "cc": "1023456789",
                "password": "SecureAdminPassword"
            }
        }


class Token(BaseModel):
    """
    Esquema para la respuesta de un token JWT.
    """
    access_token: str = Field(..., examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    token_type: str = Field("bearer", examples=["bearer"])


class TokenData(BaseModel):
    """
    Esquema para los datos contenidos dentro de un token JWT (payload).
    El 'sub' (subject) usualmente contiene el identificador del usuario.
    """
    id: Optional[str] = None # Usamos str aquí porque el ObjectId ya estaría serializado a string en el token
    role: Optional[str] = None
    email: Optional[EmailStr] = None # Puede ser útil para validaciones adicionales o información rápida