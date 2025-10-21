from aiogram.fsm.state import State, StatesGroup


class User(StatesGroup):
    weight = State()
    height = State()
    age = State()
    activity_lvl = State()
    water_goal = State()
    calorie_goal = State()
    
class EditProfileStates(StatesGroup):
    choosing_field = State()
    editing_weight = State()
    editing_height = State()
    editing_age = State()
    editing_activity = State()
    editing_water_goal = State()
    editing_calorie_goal = State()

class DeleteProfileStates(StatesGroup):
    confirmation = State()


