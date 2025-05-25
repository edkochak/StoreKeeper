from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import and_
from sqlalchemy.sql import func
from app.models.user import User
import logging

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_full_name(self, first_name: str, last_name: str) -> Optional[User]:
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.store),
                selectinload(User.revenues),
            )
            .filter_by(first_name=first_name, last_name=last_name)
        )
        return result.scalars().first()

    async def get_by_name(self, first_name: str, last_name: str) -> Optional[User]:
        """Получить пользователя по имени и фамилии"""

        try:
            query = (
                select(User)
                .where(
                    and_(
                        func.lower(User.first_name) == func.lower(first_name),
                        func.lower(User.last_name) == func.lower(last_name),
                    )
                )
                .options(selectinload(User.store))
            )
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка при поиске пользователя: {e }")

            query = (
                select(User)
                .where(
                    and_(
                        User.first_name == first_name,
                        User.last_name == last_name,
                    )
                )
                .options(selectinload(User.store))
            )
            result = await self.session.execute(query)
            return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Получает пользователя по ID.

        Args:
            user_id: ID пользователя

        Returns:
            Optional[User]: Объект пользователя или None, если пользователь не найден
        """
        query = select(User).where(User.id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self, first_name: str, last_name: str, role: str, store_id: Optional[int] = None
    ) -> User:
        user = User(
            first_name=first_name, last_name=last_name, role=role, store_id=store_id
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_all(self) -> List[User]:
        result = await self.session.execute(
            select(User).options(
                selectinload(User.store),
                selectinload(User.revenues),
            )
        )
        return result.scalars().all()

    async def update_store(self, user: User, store_id: int) -> User:
        user.store_id = store_id
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_first_name(self, user: User, first_name: str) -> User:
        """Обновить имя пользователя"""
        user.first_name = first_name
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_last_name(self, user: User, last_name: str) -> User:
        """Обновить фамилию пользователя"""
        user.last_name = last_name
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete_user(self, user: User) -> None:
        await self.session.delete(user)
        await self.session.commit()

    async def update_chat_id(self, user: User, chat_id: int) -> User:
        """Обновить Telegram chat_id пользователя"""
        user.chat_id = chat_id
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
