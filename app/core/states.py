from aiogram.fsm.state import State, StatesGroup


class AuthStates(StatesGroup):
    waiting_name = State()


class RevenueStates(StatesGroup):
    waiting_date = State()
    waiting_store = State()
    waiting_amount = State()


class PlanStates(StatesGroup):
    waiting_store = State()
    waiting_plan = State()


class AssignStates(StatesGroup):
    waiting_manager = State()
    waiting_store = State()


class CreateStoreStates(StatesGroup):
    waiting_name = State()
    waiting_plan = State()


class CreateManagerStates(StatesGroup):
    waiting_first_name = State()
    waiting_last_name = State()
    waiting_store = State()


class EditStoreStates(StatesGroup):
    waiting_store = State()
    waiting_field = State()
    waiting_value = State()


class EditManagerStates(StatesGroup):
    waiting_manager = State()
    waiting_field = State()
    waiting_value = State()
