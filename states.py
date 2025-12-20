from aiogram.fsm.state import State, StatesGroup


class User(StatesGroup):
    gender = State()
    weight = State()
    height = State()
    age = State()
    activity_level = State()
    goal_type = State()


class EditProfileStates(StatesGroup):
    choosing_field = State()
    editing_gender = State()
    editing_weight = State()
    editing_height = State()
    editing_age = State()
    editing_activity = State()
    editing_goal = State()


class PhotoRecognitionStates(StatesGroup):
    waiting_for_correction = State()


class FoodCorrectionStates(StatesGroup):
    choosing_correction_type = State()
    correcting_grams = State()
    correcting_calories = State()


class DeleteProfileStates(StatesGroup):
    confirmation = State()

