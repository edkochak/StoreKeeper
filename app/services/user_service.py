from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.repositories.user_repository import UserRepository
from app.models.user import User


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
        return await self.repo.get_by_full_name(first_name, last_name)

    async def assign_store(self, user: User, store_id: int) -> User:
        """Привязать менеджера к магазину"""
        return await self.repo.update_store(user, store_id)

    async def get_all_users(self) -> List[User]:
        """Получить всех пользователей"""
        return await self.repo.get_all()
