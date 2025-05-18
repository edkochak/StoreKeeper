from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.repositories.user_repository import UserRepository
from app.models.user import User
import logging

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)

    async def get_or_create(
        self, first_name: str, last_name: str, role: str, store_id: Optional[int] = None
    ):
        user = await self.repo.get_by_full_name(first_name, last_name)
        if not user:
            user = await self.repo.create(first_name, last_name, role, store_id)
        return user

    async def get_by_name(self, first_name: str, last_name: str) -> Optional[User]:
        """Получить пользователя по имени и фамилии"""
        logger.info(f"Поиск пользователя по имени и фамилии: {first_name} {last_name}")
        return await self.repo.get_by_name(first_name, last_name)

    async def assign_store(self, user: User, store_id: int) -> User:
        """Привязать менеджера к магазину"""
        return await self.repo.update_store(user, store_id)

    async def get_all_users(self) -> List[User]:
        """Получить всех пользователей"""
        return await self.repo.get_all()

    async def update_first_name(self, user: User, first_name: str) -> User:
        """Обновить имя пользователя"""
        return await self.repo.update_first_name(user, first_name)

    async def update_last_name(self, user: User, last_name: str) -> User:
        """Обновить фамилию пользователя"""
        return await self.repo.update_last_name(user, last_name)

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Получает пользователя по ID.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Optional[User]: Объект пользователя или None, если пользователь не найден
        """
        return await self.repo.get_by_id(user_id)

    def can_view_reports(self, user: User) -> bool:
        """
        Проверяет, может ли пользователь просматривать отчеты.
        
        Args:
            user: Пользователь для проверки
            
        Returns:
            bool: True если пользователь может просматривать отчеты, иначе False
        """
        return user.role == "admin"

    def can_manage_stores(self, user: User) -> bool:
        """
        Проверяет, может ли пользователь управлять магазинами.
        
        Args:
            user: Пользователь для проверки
            
        Returns:
            bool: True если пользователь может управлять магазинами, иначе False
        """
        return user.role == "admin"

    def can_manage_users(self, user: User) -> bool:
        """
        Проверяет, может ли пользователь управлять другими пользователями.
        
        Args:
            user: Пользователь для проверки
            
        Returns:
            bool: True если пользователь может управлять пользователями, иначе False
        """
        return user.role == "admin"
