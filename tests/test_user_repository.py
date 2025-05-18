import pytest
from datetime import date
from app.repositories.user_repository import UserRepository
from app.models.user import User


@pytest.mark.asyncio
async def test_user_repository(session):
    repo = UserRepository(session)

    user = await repo.get_by_full_name("Alice", "Wonder")
    assert user is None

    user = await repo.create("Alice", "Wonder", "manager")
    assert isinstance(user, User)
    assert user.id is not None

    same = await repo.get_by_full_name("Alice", "Wonder")
    assert same.id == user.id
