import pytest
from unittest.mock import AsyncMock, patch
from aiogram.types import Message, User as TgUser, Chat
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from app.handlers.admin_handler import (
    cmd_edit_store,
    process_edit_store_selection,
    process_edit_store_field,
    process_edit_store_value,
    cmd_edit_manager,
    process_edit_manager_selection,
    process_edit_manager_field,
    process_edit_manager_value,
)
from app.core.states import EditStoreStates, EditManagerStates
from app.services.store_service import StoreService
from app.services.user_service import UserService
from app.models.store import Store
from app.models.user import User


@pytest.fixture
def create_message():
    def _create_message(text="", chat_id=123456789, from_user_id=123456789):
        message = AsyncMock(spec=Message)
        message.text = text
        message.chat = Chat(id=chat_id, type="private")
        message.from_user = TgUser(id=from_user_id, is_bot=False, first_name="Test")

        message.answer = AsyncMock()
        message.answer.return_value = AsyncMock()
        return message

    return _create_message


@pytest.fixture
def state():
    storage = MemoryStorage()
    state = FSMContext(storage=storage, key="test")
    return state


@pytest.fixture
def session_patch(session):

    class SessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            pass

    with patch("app.handlers.admin_handler.get_session", return_value=SessionContext()):
        yield session


@pytest.fixture(scope="module")
def fresh_session_factory():
    from sqlalchemy.ext.asyncio import (
        create_async_engine,
        async_sessionmaker,
        AsyncSession,
    )
    from app.core.database import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async def _factory():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        sessionmaker_ = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        return sessionmaker_()

    yield _factory

    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(engine.dispose())


@pytest.mark.asyncio
async def test_cmd_edit_store(create_message, state, session_patch):
    """Тест команды редактирования магазина"""

    store_svc = StoreService(session_patch)
    store = await store_svc.get_or_create("TestEditStore")

    message = create_message()
    await cmd_edit_store(message, state)

    message.answer.assert_called_once()
    assert "Выберите магазин для редактирования" in message.answer.call_args[0][0]

    assert await state.get_state() == EditStoreStates.waiting_store


@pytest.mark.asyncio
async def test_edit_store_flow(create_message, state, session_patch):
    """Тест полного потока редактирования магазина"""

    store_svc = StoreService(session_patch)
    store = await store_svc.get_or_create("FlowTestStore")
    await store_svc.set_plan(store, 100.0)

    message1 = create_message("FlowTestStore")
    await process_edit_store_selection(message1, state)

    assert await state.get_state() == EditStoreStates.waiting_field
    state_data = await state.get_data()
    assert state_data["store_name"] == "FlowTestStore"

    message2 = create_message("Изменить план")
    await process_edit_store_field(message2, state)

    assert await state.get_state() == EditStoreStates.waiting_value
    state_data = await state.get_data()
    assert state_data["edit_field"] == "plan"

    store_service = StoreService(session_patch)

    message3 = create_message("200.5")

    with patch(
        "app.services.store_service.StoreService.get_by_name", return_value=store
    ):
        with patch(
            "app.services.store_service.StoreService.set_plan", return_value=store
        ):
            await process_edit_store_value(message3, state)

    assert await state.get_state() is None


@pytest.mark.asyncio
async def test_cmd_edit_manager(create_message, state, session_patch):
    """Тест команды редактирования менеджера"""

    user_svc = UserService(session_patch)
    manager = await user_svc.get_or_create("TestEdit", "Manager", "manager")

    with patch(
        "app.services.user_service.UserService.get_all_users", return_value=[manager]
    ), patch("app.handlers.admin_handler.ADMIN_CHAT_IDS", [123456789]):

        message = create_message()
        await cmd_edit_manager(message, state)

        message.answer.assert_called_once()
        assert "Выберите менеджера для редактирования" in message.answer.call_args[0][0]

        assert await state.get_state() == EditManagerStates.waiting_manager


@pytest.mark.asyncio
async def test_edit_manager_flow(create_message, state, session_patch):
    """Тест полного потока редактирования менеджера"""

    user_svc = UserService(session_patch)
    store_svc = StoreService(session_patch)

    manager = await user_svc.get_or_create("FlowTest", "Manager", "manager")
    store = await store_svc.get_or_create("ManagerTestStore")

    message1 = create_message("FlowTest Manager")
    await process_edit_manager_selection(message1, state)

    assert await state.get_state() == EditManagerStates.waiting_field
    state_data = await state.get_data()
    assert state_data["manager_name"] == "FlowTest Manager"

    message2 = create_message("Изменить магазин")

    with patch(
        "app.services.store_service.StoreService.list_stores", return_value=[store]
    ):
        await process_edit_manager_field(message2, state)

    assert await state.get_state() == EditManagerStates.waiting_value
    state_data = await state.get_data()
    assert state_data["edit_field"] == "store"
    assert state_data["first_name"] == "FlowTest"
    assert state_data["last_name"] == "Manager"

    message3 = create_message("ManagerTestStore")

    with patch(
        "app.services.user_service.UserService.get_by_name", return_value=manager
    ):
        with patch(
            "app.services.store_service.StoreService.get_by_name", return_value=store
        ):
            with patch(
                "app.services.user_service.UserService.assign_store",
                return_value=manager,
            ):
                await process_edit_manager_value(message3, state)

    assert await state.get_state() is None


@pytest.mark.skip(reason="Многословные фамилии больше не поддерживаются")
@pytest.mark.asyncio
async def test_edit_manager_multiname_flow(create_message, state, session_patch):
    """Тест редактирования менеджера с многословной фамилией (отключен)"""
    user_svc = UserService(session_patch)
    manager = await user_svc.get_or_create(
        "Екатерина", "Тараскина Тараскина", "manager"
    )

    message1 = create_message("Екатерина Тараскина Тараскина")
    await process_edit_manager_selection(message1, state)

    assert await state.get_state() == EditManagerStates.waiting_field
    data = await state.get_data()
    assert data["manager_name"] == "Екатерина Тараскина Тараскина"


@pytest.mark.asyncio
async def test_manager_delete_flow(create_message, state, session_patch):
    """Тест удаления менеджера"""
    user_svc = UserService(session_patch)
    manager = await user_svc.get_or_create("Single", "Word", "manager")

    message1 = create_message("Single Word")
    await process_edit_manager_selection(message1, state)
    assert await state.get_state() == EditManagerStates.waiting_field

    message2 = create_message("Удалить менеджера")
    with patch(
        "app.services.user_service.UserService.delete_user", return_value=None
    ) as mock_del:
        await process_edit_manager_field(message2, state)

    mock_del.assert_called_once_with(manager)
    assert await state.get_state() is None


@pytest.mark.asyncio
async def test_store_delete_flow(create_message, state, session_patch):
    """Тест удаления магазина"""
    store_svc = StoreService(session_patch)
    store = await store_svc.get_or_create("OneWordStore")

    message1 = create_message("OneWordStore")
    await process_edit_store_selection(message1, state)
    assert await state.get_state() == EditStoreStates.waiting_field

    message2 = create_message("Удалить магазин")
    with patch(
        "app.services.store_service.StoreService.delete_store", return_value=None
    ) as mock_del:
        await process_edit_store_field(message2, state)

    mock_del.assert_called_once_with(store)
    assert await state.get_state() is None


@pytest.mark.asyncio
async def test_manager_single_word_validation(create_message, state, session_patch):
    """Тест проверки, что имя и фамилия - одно слово каждое"""
    user_svc = UserService(session_patch)

    with pytest.raises(ValueError):
        await user_svc.get_or_create("John Paul", "Doe", "manager")

    with pytest.raises(ValueError):
        await user_svc.get_or_create("John", "Van Doe", "manager")


@pytest.mark.asyncio
async def test_eager_load_store(fresh_session_factory):
    """Тест, проверяющий, что можно получить store без DetachedInstanceError после закрытия сессии."""

    session1 = await fresh_session_factory()
    user_svc_1 = UserService(session1)
    store_svc_1 = StoreService(session1)
    store = await store_svc_1.get_or_create("EagerLoadStore")
    manager = await user_svc_1.get_or_create(
        "Eager", "Test", "manager", store_id=store.id
    )
    await session1.close()

    session2 = await fresh_session_factory()
    user_svc_2 = UserService(session2)
    loaded_manager = await user_svc_2.get_by_name_with_store("Eager", "Test")
    assert loaded_manager is not None
    assert loaded_manager.store is not None
    await session2.close()
