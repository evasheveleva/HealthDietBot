from aiogram.fsm.state import State, StatesGroup


class User(StatesGroup):
    weight = State()
    height = State()
    age = State()
    activity_lvl = State()
    water_goal = State()
    calorie_goal = State()

