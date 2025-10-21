from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from states import User, EditProfileStates, DeleteProfileStates
from calculation import calc_water, calc_calorie

router = Router()

global calorie
calorie = 0

user_dict: dict[int, dict[str, str | int | bool]] = {}
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

    user_data = await state.get_data()
    user_id = message.from_user.id

    user_dict[user_id] = user_data

    save_user_to_db(user_id, user_data)


    await message.answer("Профиль успешно сохранен!")
    await state.clear()

@router.message(Command(commands='profile'), StateFilter(default_state))
async def process_showdata_command(message: Message):

    user_id = message.from_user.id
    user_profile = get_user_profile(user_id)

    if user_profile:
        profile_text = ('Ваш профиль: \n\n'
            f'Вес: {user_profile.get("weight")}\n'
            f'Рост: {user_profile.get("height")}\n'
            f'Возраст: {user_profile.get("age")}\n'
            f'Минут активности в день: {user_profile.get("activity_lvl")}\n'
            f'Водная цель: {user_profile.get("water_goal")}\n'
            f'Цель по калориям: {user_profile.get("calorie_goal")}\n'
            'Чтобы изменить данные используйте /edit_profile\n'
            'Если хотите удалить профиль используйте /delete_profile'
        )
        await message.answer(profile_text)
    else:
        # Если анкеты пользователя в базе нет - предлагаем заполнить
        await message.answer(
            text='Вы еще не заполняли профиль. Чтобы приступить - '
            'отправьте команду /set_profile'
        )

@router.message(Command(commands='edit_profile'))
async def edit_profile_cmd(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_profile = get_user_profile(user_id)
    if not user_profile:
        await message.answer('У вас еще нет профиля. Создайте его командой /set_profile')
        return

    kb = [
        [KeyboardButton(text='Вес'), KeyboardButton(text='Рост')],
        [KeyboardButton(text='Возраст'), KeyboardButton(text='Уровень активности')],
        [KeyboardButton(text='Водная цель'), KeyboardButton(text='Цель по калориям')],
        [KeyboardButton(text='Отмена')]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb)
    await message.answer('Что вы хотите изменить?', reply_markup=keyboard)
    await state.set_state(EditProfileStates.choosing_field)

@router.message(EditProfileStates.choosing_field)
async def process_field_choice(message: Message, state: FSMContext):
    field_choice = message.text
    field_mapping = {
        "Вес": ("weight", EditProfileStates.editing_weight),
        "Рост": ("height", EditProfileStates.editing_height),
        "Возраст": ("age", EditProfileStates.editing_age),
        "Уровень активности": ("activity_lvl", EditProfileStates.editing_activity),
        "Водная цель": ("water_goal", EditProfileStates.editing_water_goal),
        "Цель по калориям": ("calorie_goal", EditProfileStates.editing_calorie_goal)
    }
    if field_choice == 'Отмена':
        await message.answer('Изменение отменено')
        await state.clear()
        return

    if field_choice in field_mapping:
        field_name, next_state = field_mapping[field_choice]
        await state.update_data(editing_field=field_name)
        await state.set_state(next_state)
        await message.answer('Введите данные, на которые вы хотите изменить: ')
    else:
        await message.answer('Пожалуйста, выберите поле из списка')

@router.message(EditProfileStates.editing_weight)
async def process_edit_weight(message: Message, state: FSMContext):
    new_weight = int(message.text)
    user_data = await state.get_data()
    field_name = user_data['editing_field']

    success = update_user_field(message.from_user.id, field_name, new_weight)
    if success:
        if message.from_user.id in user_dict:
            user_dict[message.from_user.id]['weight'] = new_weight
        await message.answer(f'Вес успешно изменён на {new_weight} кг')
        await process_showdata_command(message)

        await state.clear()

@router.message(EditProfileStates.editing_age)
async def process_edit_age(message: Message, state: FSMContext):
    new_age = int(message.text)
    user_data = await state.get_data()
    field_name = user_data['editing_field']

    success = update_user_field(message.from_user.id, field_name, new_age)

    if success:
        if message.from_user.id in user_dict:
            user_dict[message.from_user.id]['age'] = new_age

        await message.answer(f'Возраст успешно изменен на {new_age}')
        await process_showdata_command(message)

    await state.clear()

@router.message(EditProfileStates.editing_activity)
async def process_edit_activity(message: Message, state: FSMContext):
    new_activity = int(message.text)
    user_data = await state.get_data()
    field_name = user_data['editing_field']

    success = update_user_field(message.from_user.id, field_name, new_activity)
    if success:
        if message.from_user.id in user_dict:
            user_dict[message.from_user.id]['activity'] = new_activity
        await message.answer(f'Количество минут активности изменено на {new_activity}')
        await process_showdata_command(message)


    await state.clear()

@router.message(EditProfileStates.editing_water_goal)
async def process_edit_water(message: Message, state: FSMContext):
    new_water_goal = int(message.text)
    user_data = await state.get_data()
    field_name = user_data['editing_field']

    success = update_user_field(message.from_user.id, field_name, new_water_goal)
    if success:
        if message.from_user.id in user_dict:
            user_dict[message.from_user.id]['water_goal'] = new_water_goal
        await message.answer(f'Водная цель была изменена на {new_water_goal}')
        await process_showdata_command(message)

    await state.clear()


@router.message(EditProfileStates.editing_calorie_goal)
async def process_edit_calorie(message: Message, state: FSMContext):
    new_calorie_goal = int(message.text)
    user_data = await state.get_data()
    field_name = user_data['editing_field']

    success = update_user_field(message.from_user.id, field_name, new_calorie_goal)
    if success:
        if message.from_user.id in user_dict:
            user_dict[message.from_user.id]['calorie_goal'] = new_calorie_goal
        await message.answer(f'Цель по калориям была изменена на {new_calorie_goal}')
        await process_showdata_command(message)

    await state.clear()

@router.message(EditProfileStates.editing_height)
async def process_edit_height(message: Message, state: FSMContext):
    new_height = int(message.text)
    user_data = await state.get_data()
    field_name = user_data['editing_field']

    success = update_user_field(message.from_user.id, field_name, new_height)
    if success:
        if message.from_user.id in user_dict:
            user_dict[message.from_user.id]['calorie_goal'] = new_height
        await message.answer(f'Рост был изменен на {new_height}')
        await process_showdata_command(message)

    await state.clear()

@router.message(Command(commands='delete_profile'))
async def delete_profile_cmd(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_profile = get_user_profile(user_id)
    if not user_profile:
        await message.answer('У вас еще нет профиля')
        return
    kb = [
        [KeyboardButton(text='Да, удалить профиль'), KeyboardButton(text='Нет, отменить')]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb)

    await message.answer('Вы уверены, что хотите удалить профиль?\n\n'
                         'Все ваши данные будут безвозвратно удалены!',
                         reply_markup=keyboard)
    await state.set_state(DeleteProfileStates.confirmation)

@router.message(DeleteProfileStates.confirmation)
async def process_delete_conf(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if message.text == 'Да, удалить профиль':
        db_success = delete_user_profile(user_id)

        memory_success = False
        if user_id in user_dict:
            del user_dict[user_id]
            memory_success = True
        if db_success:
            await message.answer('Ваш профиль был успешно удален. \n\n'
                                 'Если захотите создать новый, используйте команду /set_profile',
                                 reply_markup=ReplyKeyboardRemove())
        else:
            await message.answer('Произошла ошибка при удалении профиля', reply_markup=ReplyKeyboardRemove())

    elif message.text == 'Нет, отменить':

        await message.answer('Удаление отменено', reply_markup=ReplyKeyboardRemove())
        await process_showdata_command(message)
    else:
        await message.answer('Пожалуйста, выберите вариант из клавиатуры', reply_markup=ReplyKeyboardRemove())

    await state.clear()

def setup_handlers(dp):
    dp.include_router(router)
