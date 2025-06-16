from typing import List, Optional, Dict
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime

from app.modules.residentes.models import User
from app.modules.residentes.schemas import ResidentCreate, ResidentUpdate, AdminUserUpdate
from app.shared.repository import BaseRepository
from app.core.security import get_password_hash

class ResidentService:
    """
    Servicio de lógica de negocio para la gestión de usuarios (residentes y administradores).
    GRASP: Information Expert - Es responsable de la lógica de negocio de los usuarios.
    """
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.user_repository = BaseRepository(self.db["users"], User)

    async def _get_user_by_identifier(self, identifier: str) -> Optional[User]:
        """
        Método interno para obtener un usuario por ID o CC.
        """
        # Intentar buscar por ObjectId
        if ObjectId.is_valid(identifier):
            user = await self.user_repository.get(identifier)
            if user:
                return user
        
        # Si no se encontró por ID o el ID no era válido, intentar buscar por CC
        user = await self.user_repository.find_one({"cc": identifier})
        return user

    async def get_user_by_id(self, user_id: str) -> User:
        """
        Obtiene un usuario por su ID. Lanza 404 si no se encuentra.
        """
        user = await self._get_user_by_identifier(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
        return user

    async def get_all_users(
        self, 
        skip: int = 0, 
        limit: int = 200,
        status_filter: Optional[str] = None,
        role_filter: Optional[str] = None
    ) -> List[User]:
        """
        Obtiene una lista de todos los usuarios, con paginación y filtros opcionales.
        Prioriza el orden: pending_approval, then active, then inactive.
        """
        query = {}
        if status_filter:
            query["status"] = status_filter
        if role_filter:
            query["role"] = role_filter

        # Usar find_many para obtener múltiples documentos con paginación
        users = await self.user_repository.find_many(query, skip=skip, limit=limit)

        # Ordenar en Python: pending_approval > active > inactive
        status_order = {"pending_approval": 0, "active": 1, "inactive": 2}
        users.sort(key=lambda user: (status_order.get(user.status, 99), user.full_name.lower()))
        
        return users

    async def create_user(self, user_data: ResidentCreate, role: str = "residente", status_initial: str = "pending_approval") -> User:
        """
        Crea un nuevo usuario.
        Valida unicidad de email y CC, hashea la contraseña y asigna rol/estado inicial.
        """
        # Si el administrador proporcionó un rol o estado, usarlo, de lo contrario usar los defaults del método
        final_role = user_data.role if hasattr(user_data, 'role') and user_data.role else role
        final_status = user_data.status if hasattr(user_data, 'status') and user_data.status else status_initial

        existing_user_email = await self.user_repository.find_one({"email": user_data.email})
        if existing_user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está registrado."
            )
        
        existing_user_cc = await self.user_repository.find_one({"cc": user_data.cc})
        if existing_user_cc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La cédula de ciudadanía ya está registrada."
            )

        hashed_password = get_password_hash(user_data.password)
        
        new_user = User(
            full_name=user_data.full_name,
            cc=user_data.cc,
            email=user_data.email,
            hashed_password=hashed_password,
            apartment=user_data.apartment,
            phone_number=user_data.phone_number,
            role=final_role,
            status=final_status
        ) # type: ignore
        
        created_user = await self.user_repository.create(new_user)
        return created_user

    async def update_user(self, user_id: str, user_update: ResidentUpdate) -> User:
        """
        Actualiza la información de un usuario existente por ID.
        """
        existing_user = await self._get_user_by_identifier(user_id)
        if not existing_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

        update_data = user_update.model_dump(exclude_unset=True)
        
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(update_data["password"])
            del update_data["password"]
        
        update_data["updated_at"] = datetime.utcnow()

        updated_user = await self.user_repository.update(existing_user.id, update_data) # type: ignore
        if not updated_user:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo actualizar el usuario.")
        
        return updated_user

    async def admin_update_user(self, user_id: str, admin_user_update: AdminUserUpdate) -> User:
        """
        Permite a un administrador actualizar cualquier campo de un usuario por ID,
        incluyendo rol y estado.
        """
        existing_user = await self._get_user_by_identifier(user_id)
        if not existing_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

        update_data = admin_user_update.model_dump(exclude_unset=True)
        
        # Validar si el administrador intenta cambiar su propio rol a residente
        if existing_user.role == "administrador" and "role" in update_data and update_data["role"] == "residente":
            admin_count = await self.user_repository.count({"role": "administrador"})
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No puedes degradar al último administrador del sistema."
                )

        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(update_data["password"])
            del update_data["password"]
        
        update_data["updated_at"] = datetime.utcnow()

        updated_user = await self.user_repository.update(existing_user.id, update_data) # type: ignore
        if not updated_user:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo actualizar el usuario.")
        
        return updated_user

    async def delete_user(self, user_id: str) -> Dict[str, str]:
        """
        Elimina un usuario por su ID.
        """
        user_to_delete = await self._get_user_by_identifier(user_id)
        if not user_to_delete:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
        
        if user_to_delete.role == "administrador":
            admin_count = await self.user_repository.count({"role": "administrador"})
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se puede eliminar el último usuario administrador del sistema."
                )
        
        deleted = await self.user_repository.delete(user_to_delete.id) # type: ignore
        if not deleted:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo eliminar el usuario.")
        
        return {"message": "Usuario eliminado exitosamente."}