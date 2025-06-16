import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env
load_dotenv()

class Settings(BaseSettings):
    """
    Configuración de la aplicación cargada desde variables de entorno.
    """
    model_config = SettingsConfigDict(case_sensitive=True)

    # Configuración de la base de datos MongoDB
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017/park-net")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "park-net")

    # Clave secreta para JWT (JSON Web Tokens)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "ES_UN_SECRETO")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # Tiempo de expiración del token de acceso

# Instancia de configuración para ser usada en la aplicación
settings = Settings()