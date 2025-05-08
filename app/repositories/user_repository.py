from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload  # <-- импортируем
from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_full_name(self, first_name: str, last_name: str) -> Optional[User]:
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.store),  # жадно подгружаем магазин
                selectinload(User.revenues),  # жадно подгружаем выручки
            )
            .filter_by(first_name=first_name, last_name=last_name)
        )
        return result.scalars().first()

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
                selectinload(User.store),  # жадно подгружаем магазин
                selectinload(User.revenues),  # жадно подгружаем выручки
            )
        )
        return result.scalars().all()

    async def update_store(self, user: User, store_id: int) -> User:
        user.store_id = store_id
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
