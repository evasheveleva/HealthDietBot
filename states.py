from aiogram.fsm.state import State, StatesGroup


class User(StatesGroup):
    """Состояния для регистрации пользователя"""
    gender = State()
    weight = State()
    height = State()
    age = State()
    activity_level = State()


class EditProfileStates(StatesGroup):
    """Состояния для редактирования профиля"""
    choosing_field = State()
    editing_gender = State()
    editing_weight = State()
    editing_height = State()
    editing_age = State()
    editing_activity = State()


class PhotoRecognitionStates(StatesGroup):
    """Состояния для обработки фото блюда"""
    waiting_for_correction = State()


class DeleteProfileStates(StatesGroup):
    """Состояния для удаления профиля"""
    confirmation = State()
