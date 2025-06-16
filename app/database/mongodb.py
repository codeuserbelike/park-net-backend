from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError
from app.core.config import settings

client: AsyncIOMotorClient = None  # type: ignore

async def connect_to_mongo():
    """
    Establece la conexión a la base de datos MongoDB.
    """
    global client
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        await client.admin.command('ping')
        print(f"Conexión a MongoDB establecida exitosamente a {settings.MONGODB_URL}")
        await create_indexes()
    except ServerSelectionTimeoutError as err:
        print(f"Error al conectar a MongoDB: {err}. Asegúrate de que MongoDB esté corriendo.")
        raise
    except Exception as e:
        print(f"Error inesperado al conectar a MongoDB: {e}")
        raise

async def close_mongo_connection():
    """
    Cierra la conexión a la base de datos MongoDB.
    """
    global client
    if client:
        client.close()
        print("Conexión a MongoDB cerrada.")

def get_database():
    """
    Retorna la instancia de la base de datos MongoDB.
    """
    if client:
        return client[settings.MONGODB_DB_NAME]
    raise Exception("La conexión a la base de datos no ha sido establecida.")

async def create_indexes():
    db = get_database()
    await db.users.create_index("email", unique=True)
    await db.users.create_index("cc", unique=True)
