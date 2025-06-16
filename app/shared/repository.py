from bson import ObjectId
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument
import pymongo
import pymongo.errors

# Define un TypeVar para el modelo Pydantic que usará el repositorio
ModelType = TypeVar("ModelType", bound=BaseModel)

class BaseRepository(Generic[ModelType]):
    """
    Repositorio base genérico para operaciones CRUD básicas en MongoDB.
    
    Este repositorio implementa un enfoque centralizado para la conversión de IDs:
    1. Todos los documentos recuperados de MongoDB tendrán su campo '_id' convertido a 'id' (string)
    2. Elimina el campo '_id' original para evitar conflictos con los modelos Pydantic
    3. Garantiza consistencia en el manejo de IDs en toda la aplicación
    
    Atributos:
        collection (AsyncIOMotorCollection): Colección de MongoDB
        model (Type[ModelType]): Clase del modelo Pydantic para validación
    """
    
    def __init__(self, collection: AsyncIOMotorCollection, model: Type[ModelType]):
        """
        Inicializa el repositorio con una colección de MongoDB y un modelo Pydantic.
        
        Args:
            collection: Colección de MongoDB para operaciones
            model: Clase del modelo Pydantic para validación de documentos
        """
        self.collection = collection
        self.model = model

    async def create(self, obj_in: BaseModel) -> ModelType:
        """
        Crea un nuevo documento en la colección.
        
        Convierte el modelo Pydantic a diccionario, lo inserta en MongoDB,
        luego recupera y valida el documento creado con el campo 'id' como string.
        
        Args:
            obj_in: Instancia del modelo Pydantic con datos a insertar
            
        Returns:
            ModelType: Instancia del modelo con datos del documento creado
            
        Raises:
            RuntimeError: Si falla la inserción o no se encuentra el documento creado
        """
        # Convertir el Pydantic model a diccionario, excluyendo campos no definidos
        insert_data = obj_in.model_dump(exclude={"id"})
        
        # Insertar el documento en MongoDB
        result = await self.collection.insert_one(insert_data)
        
        # Verificar que la inserción fue exitosa
        if not result.inserted_id:
            raise RuntimeError("Failed to insert document")
        
        # Recuperar el documento recién insertado
        created_doc = await self.collection.find_one({"_id": result.inserted_id})
        
        # Verificar que se encontró el documento
        if not created_doc:
            raise RuntimeError("Inserted document not found")
        
        # Transformación centralizada: convertir ObjectId a string y renombrar a 'id'
        created_doc["id"] = str(created_doc.pop("_id"))
        return self.model.model_validate(created_doc)

    async def get(self, item_id: str) -> Optional[ModelType]:
        """
        Obtiene un documento por su ID.
        
        Realiza la conversión de:
        - ID de entrada (string) → ObjectId para consulta MongoDB
        - Documento resultante: '_id' (ObjectId) → 'id' (string)
        
        Args:
            item_id: ID del documento como string
            
        Returns:
            ModelType | None: Instancia del modelo con los datos del documento,
            o None si no se encuentra
        """
        try:
            # Convertir string ID a ObjectId de MongoDB
            obj_id = ObjectId(item_id)
            
            # Buscar el documento por su ID
            doc = await self.collection.find_one({"_id": obj_id})
            
            if doc:
                # Transformación centralizada
                doc["id"] = str(doc.pop("_id"))
                return self.model.model_validate(doc)
        except (pymongo.errors.PyMongoError, Exception) as e:
            print(f"Error getting document: {e}")
        return None

    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 200, 
        sort_field: Optional[str] = None, 
        sort_direction: int = 1
    ) -> List[ModelType]:
        """
        Obtiene múltiples documentos con paginación y ordenamiento opcional.
        
        Aplica la transformación centralizada a cada documento recuperado:
        '_id' (ObjectId) → 'id' (string)
        
        Args:
            skip: Número de documentos a omitir (paginación)
            limit: Número máximo de documentos a devolver
            sort_field: Campo para ordenar los resultados
            sort_direction: Dirección de ordenamiento (1 = ascendente, -1 = descendente)
            
        Returns:
            List[ModelType]: Lista de instancias del modelo con los documentos
        """
        # Crear cursor base para todos los documentos
        cursor = self.collection.find({})
        
        # Aplicar ordenamiento si se especificó
        if sort_field:
            cursor = cursor.sort(sort_field, sort_direction)
            
        # Aplicar paginación
        cursor = cursor.skip(skip).limit(limit)
        
        # Procesar resultados con transformación centralizada
        results = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(self.model.model_validate(doc))
        return results

    async def update(
        self, 
        item_id: str, 
        update_data: Dict[str, Any]
    ) -> Optional[ModelType]:
        """
        Actualiza un documento por su ID.
        
        Realiza la conversión de:
        - ID de entrada (string) → ObjectId para consulta MongoDB
        - Documento resultante: '_id' (ObjectId) → 'id' (string)
        
        Args:
            item_id: ID del documento como string
            update_data: Diccionario con campos a actualizar
            
        Returns:
            ModelType | None: Instancia del modelo con los datos actualizados,
            o None si no se encuentra el documento
        """
        try:
            obj_id = ObjectId(item_id)
            updated_doc = await self.collection.find_one_and_update(
                {"_id": obj_id},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER
            )
            if updated_doc:
                updated_doc["id"] = str(updated_doc.pop("_id"))
                return self.model.model_validate(updated_doc)
        except pymongo.errors.PyMongoError as e:
            print(f"Error updating document: {e}")
        return None

    async def delete(self, item_id: str) -> bool:
        """
        Elimina un documento por su ID.
        
        Realiza la conversión de:
        - ID de entrada (string) → ObjectId para consulta MongoDB
        
        Args:
            item_id: ID del documento como string
            
        Returns:
            bool: True si se eliminó el documento, False en caso contrario
        """
        try:
            obj_id = ObjectId(item_id)
            result = await self.collection.delete_one({"_id": obj_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False

    async def find_one(self, query: Dict[str, Any]) -> Optional[ModelType]:
        """
        Encuentra un documento mediante una consulta específica.
        
        Aplica la transformación centralizada al documento recuperado:
        '_id' (ObjectId) → 'id' (string)
        
        Args:
            query: Diccionario con criterios de búsqueda
            
        Returns:
            ModelType | None: Instancia del modelo con el documento encontrado,
            o None si no se encuentra
        """
        doc = await self.collection.find_one(query)
        if doc:
            doc["id"] = str(doc.pop("_id"))
            return self.model.model_validate(doc)
        return None

    async def find_many(
        self, 
        query: Dict[str, Any], 
        skip: int = 0, 
        limit: int = 100
    ) -> List[ModelType]:
        """
        Encuentra múltiples documentos mediante una consulta específica con paginación.
        
        Aplica la transformación centralizada a cada documento recuperado:
        '_id' (ObjectId) → 'id' (string)
        
        Args:
            query: Diccionario con criterios de búsqueda
            skip: Número de documentos a omitir (paginación)
            limit: Número máximo de documentos a devolver
            
        Returns:
            List[ModelType]: Lista de instancias del modelo con los documentos encontrados
        """
        cursor = self.collection.find(query).skip(skip).limit(limit)
        results = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            results.append(self.model.model_validate(doc))
        return results

    async def count(self, query: Dict[str, Any]) -> int:
        """
        Cuenta el número de documentos que cumplen con una consulta específica.
        
        Args:
            query: Diccionario con criterios de búsqueda
            
        Returns:
            int: Número de documentos que cumplen con la consulta
        """
        return await self.collection.count_documents(query)