from datetime import datetime, timedelta, timezone
from typing import Optional
from typing import cast

from jose import jwt, JWTError
from passlib.context import CryptContext
import bcrypt

from app.core.config import settings
from app.modules.auth.schemas import TokenData # Importamos TokenData para la estructura del payload

# Configuración para el hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un token de acceso JWT.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # Usar cast con verificación
        user_id = cast(str, payload.get("id")) if "id" in payload else None
        user_role = cast(Optional[str], payload.get("role"))
        user_email = cast(Optional[str], payload.get("email"))
        
        if user_id is None:
            return None
            
        return TokenData(id=user_id, role=user_role, email=user_email)
    except JWTError:
        return None