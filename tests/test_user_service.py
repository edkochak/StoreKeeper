import pytest
from app.services.user_service import UserService
from app.models.user import User


@pytest.mark.asyncio
async def test_get_or_create(session):
    svc = UserService(session)

    user = await svc.get_or_create("John", "Doe", "manager")
    assert isinstance(user, User)
    assert user.id is not None

    same_user = await svc.get_or_create("John", "Doe", "manager")
    assert same_user.id == user.id
    assert same_user.first_name == "John"
    assert same_user.last_name == "Doe"
    assert same_user.role == "manager"
