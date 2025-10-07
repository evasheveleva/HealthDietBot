from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states import User
from calculation import calc_water, calc_calorie

router = Router()

global calorie
calorie = 0


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply("Добро пожаловать! Я ваш бот.\nВведите /help для списка команд.")


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.reply(
        "Доступные команды:\n"
        "/start - Начало работы\n"
        "/help - Доступные команды\n"
        "/set_profile - настройка профиля\n"
    )


@router.message(Command("set_profile"))
async def cmd_profile(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Введите Ваш вес (в кг):")
    try:
        await state.set_state(User.weight)
    except:
        message.reply("Введите число")


@router.message(User.weight)
async def process_name_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text.replace(",", "."))
        if weight > 0 and weight < 560:
            await state.update_data(weight=weight)
            await message.reply("Введите Ваш рост (в см):")
            await state.set_state(User.height)
        else:
            raise ValueError
    except ValueError:
        await message.reply("Введите число")

@router.message(Command("check_progress"))
async def cmd_profile(message: Message, state: FSMContext):
    try:
        data_user = await state.get_data()
        drinked = data_user.get("logged_water")
        water_goal = data_user.get("water_goal")

        eaten = data_user.get("logged_calories")
        calorie_goal = data_user.get("calorie_goal")
        burned_calories = data_user.get("burned_calories")

        await message.answer(f"Прогресс:\nВода:\n - Выпито: {round(drinked)} мл из {round(water_goal)} мл.\n - Осталось: {round(water_goal - drinked)} мл.\n\nКалории:\n - Потреблено: {round(eaten)} ккал из {round(calorie_goal)} ккал.\n - Сожжено: {round(burned_calories)} ккал.\n - Баланс: {round(eaten - burned_calories)} ккал.")
    except:
        message.reply("Вы не настроили профиль.")


@router.message(User.height)
async def process_name_height(message: Message, state: FSMContext):
    try:
        height = float(message.text.replace(",", "."))
        if height > 50 and height < 252:
            await state.update_data(height=height)
            await message.reply("Введите Ваш возраст (в годах):")
            await state.set_state(User.age)
        else:
            raise ValueError
    except ValueError:
        await message.reply("Введите число")


@router.message(User.age)
async def process_name_age(message: Message, state: FSMContext):
    try:
        age = float(message.text.replace(",", "."))
        if age > 0 and age < 120:
            await state.update_data(age=age)
            await message.reply("Сколько минут активности у вас в день?")
            await state.set_state(User.activity_lvl)
        else:
            raise ValueError
    except ValueError:
        await message.reply("Введите число")


@router.message(User.activity_lvl)
async def process_name_lvl(message: Message, state: FSMContext):
    try:
        activity_lvl = float(message.text.replace(",", "."))
        if activity_lvl > -1 and activity_lvl < 1441:
            await state.update_data(activity_lvl=activity_lvl)
        else:
            raise ValueError
        await state.set_state(User.calorie_goal)
        await process_name_calorie(message, state)
    except ValueError:
        await message.reply("Введите число")


@router.message(User.calorie_goal)
async def process_name_calorie(message: Message, state: FSMContext):
    try:
        data_user = await state.get_data()
        water = calc_water(data_user.get("weight"), data_user.get("activity_lvl"))
        await state.update_data(water_goal=water)
        await message.answer(f"Ваша водная цель равна {str(water)} мл")

        calorie = calc_calorie(data_user.get("weight"),
                               data_user.get("height"),
                               data_user.get("age"),
                               data_user.get("activity_lvl"))
        await state.update_data(calorie_goal=calorie)
        await message.answer(f"Ваша цель по калориям равна {str(calorie)} калорий")
        await state.update_data(logged_water=0)
        await state.update_data(logged_calories=0)
        await state.update_data(burned_calories=0)

    except:
        await message.answer("Ошибка в вычислениях")


def setup_handlers(dp):
    dp.include_router(router)
