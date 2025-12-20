from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery, FSInputFile, BufferedInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from states import User, EditProfileStates, PhotoRecognitionStates, DeleteProfileStates, FoodCorrectionStates
from calculation import calc_water, calc_calorie, calc_calorie_with_goal
from db import (
    init_db, save_user_to_db, get_user_profile, update_user_field,
    delete_user_profile, add_food_entry, add_water_entry,
    get_daily_calories, get_daily_water
)
from ai_service import analyze_food_text, analyze_food_photo, download_photo_from_telegram
from visualization import generate_daily_chart, generate_monthly_chart
from datetime import date

router = Router()

user_dict: dict[int, dict[str, str | int | bool | float]] = {}

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    user_profile = get_user_profile(user_id)
    
    if user_profile:
        await message.reply("Добро пожаловать в HealthDietBot! 👋\n\nВаш профиль уже настроен. Используйте /help для списка команд.")
    else:
        await message.reply("Добро пожаловать в HealthDietBot! 👋\n\nЯ помогу вам отслеживать калории и воду.\nДля начала работы настройте профиль командой /set_profile")


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.reply(
        "Доступные команды:\n"
        "/start - Начало работы\n"
        "/help - Доступные команды\n"
        "/set_profile - настройка профиля\n"
        "/profile - просмотр профиля\n"
        "/edit_profile - редактирование профиля\n"
        "/delete_profile - удаление профиля\n"
        "/progress - прогресс за сегодня\n"
        "/вода <количество> - добавить воду\n"
        "/статистика день - график за день\n"
        "/статистика месяц - график за месяц\n"
        "Отправьте текст или фото блюда для анализа калорий"
    )


@router.message(Command("set_profile"))
async def cmd_set_profile(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    user_profile = get_user_profile(user_id)
    
    if user_profile:
        await message.answer("У вас уже есть профиль. Используйте /edit_profile для изменения данных.")
        return
    
    kb = [
        [KeyboardButton(text='Мужской'), KeyboardButton(text='Женский')]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Выберите ваш пол:", reply_markup=keyboard)
    await state.set_state(User.gender)


@router.message(User.gender)
async def process_gender(message: Message, state: FSMContext):
    gender_text = message.text.lower()
    if 'мужск' in gender_text:
        gender = 'male'
    elif 'женск' in gender_text:
        gender = 'female'
    else:
        await message.answer("Пожалуйста, выберите пол из предложенных вариантов.")
        return
    
    await state.update_data(gender=gender)
    await message.answer("Введите ваш вес (в кг):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(User.weight)


@router.message(User.weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text.replace(",", "."))
        if 0 < weight < 560:
            await state.update_data(weight=weight)
            await message.answer("Введите ваш рост (в см):")
            await state.set_state(User.height)
        else:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число (например: 70 или 70.5)")


@router.message(User.height)
async def process_height(message: Message, state: FSMContext):
    try:
        height = float(message.text.replace(",", "."))
        if 50 < height < 252:
            await state.update_data(height=height)
            await message.answer("Введите ваш возраст (в годах):")
            await state.set_state(User.age)
        else:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число (например: 175)")


@router.message(User.age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = float(message.text.replace(",", "."))
        if 0 < age < 120:
            await state.update_data(age=age)

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Минимальная (1.2)", callback_data="activity_1.2"),
                    InlineKeyboardButton(text="Низкая (1.375)", callback_data="activity_1.375")
                ],
                [
                    InlineKeyboardButton(text="Умеренная (1.55)", callback_data="activity_1.55"),
                    InlineKeyboardButton(text="Высокая (1.725)", callback_data="activity_1.725")
                ],
                [
                    InlineKeyboardButton(text="Очень высокая (1.9)", callback_data="activity_1.9")
                ]
            ])
            
            await message.answer(
                "Выберите уровень активности:\n\n"
                "Минимальная (1.2) - сидячий образ жизни\n"
                "Низкая (1.375) - легкие упражнения 1-3 раза в неделю\n"
                "Умеренная (1.55) - умеренные упражнения 3-5 раз в неделю\n"
                "Высокая (1.725) - интенсивные упражнения 6-7 раз в неделю\n"
                "Очень высокая (1.9) - очень интенсивные упражнения, физическая работа",
                reply_markup=keyboard
            )
            await state.set_state(User.activity_level)
        else:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число (например: 25)")


@router.callback_query(F.data.startswith("activity_"), StateFilter(User.activity_level))
async def process_activity_callback(callback: CallbackQuery, state: FSMContext):
    activity_level = float(callback.data.split("_")[1])
    await state.update_data(activity_level=activity_level)
    
    # Получаем данные и рассчитываем базовую норму
    data = await state.get_data()
    water_goal = calc_water(data.get("weight"), activity_level)
    base_calorie_goal = calc_calorie(
        data.get("weight"),
        data.get("height"),
        data.get("age"),
        data.get("gender"),
        activity_level
    )
    
    await state.update_data(water_goal=water_goal, base_calorie_goal=base_calorie_goal)
    
    await callback.message.edit_text("✅ Уровень активности выбран!")
    await callback.answer()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Поддержка веса", callback_data="goal_maintain")
        ],
        [
            InlineKeyboardButton(text="Похудение (-10%)", callback_data="goal_lose"),
            InlineKeyboardButton(text="Набор веса (+10%)", callback_data="goal_gain")
        ]
    ])
    
    await callback.message.answer(
        f"✅ Ваша базовая норма воды: {water_goal} мл\n"
        f"✅ Ваша базовая норма калорий: {base_calorie_goal} ккал\n\n"
        "Выберите вашу цель:",
        reply_markup=keyboard
    )
    await state.set_state(User.goal_type)


@router.callback_query(F.data.startswith("goal_"), StateFilter(User.goal_type))
async def process_goal_callback(callback: CallbackQuery, state: FSMContext):
    goal_type = callback.data.split("_")[1]  # maintain, lose, gain
    await state.update_data(goal_type=goal_type)

    data = await state.get_data()
    base_calorie_goal = data.get("base_calorie_goal")
    water_goal = data.get("water_goal")
    
    calorie_goal = calc_calorie_with_goal(base_calorie_goal, goal_type)
    await state.update_data(calorie_goal=calorie_goal)
    
    goal_text = {
        "maintain": "поддержка веса",
        "lose": "похудение (-10%)",
        "gain": "набор веса (+10%)"
    }
    
    await callback.message.edit_text(f"✅ Цель выбрана: {goal_text[goal_type]}")
    await callback.answer()
    
    await callback.message.answer(f"✅ Ваша суточная норма воды: {water_goal} мл")
    await callback.message.answer(f"✅ Ваша суточная норма калорий: {calorie_goal} ккал")

    user_data = await state.get_data()
    user_id = callback.from_user.id
    
    user_dict[user_id] = user_data
    save_user_to_db(user_id, user_data)
    
    await callback.message.answer("Профиль успешно сохранен!")
    await state.clear()

@router.message(Command(commands='profile'), StateFilter(default_state))
async def process_showdata_command(message: Message):
    user_id = message.from_user.id
    user_profile = get_user_profile(user_id)

    if user_profile:
        gender_text = "Мужской" if user_profile.get("gender") == "male" else "Женский"
        goal_type = user_profile.get("goal_type", "maintain")
        goal_text = {
            "maintain": "Поддержка веса",
            "lose": "Похудение (-10%)",
            "gain": "Набор веса (+10%)"
        }
        profile_text = ('Ваш профиль: \n\n'
            f'Пол: {gender_text}\n'
            f'Вес: {user_profile.get("weight")}\n'
            f'Рост: {user_profile.get("height")}\n'
            f'Возраст: {user_profile.get("age")}\n'
            f'Уровень активности: {user_profile.get("activity_level")}\n'
            f'Цель: {goal_text.get(goal_type, "Поддержка веса")}\n'
            f'Водная цель: {user_profile.get("water_goal")}\n'
            f'Цель по калориям: {user_profile.get("calorie_goal")}\n'
            'Чтобы изменить данные используйте /edit_profile\n'
            'Если хотите удалить профиль используйте /delete_profile'
        )
        await message.answer(profile_text)
    else:
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
        [KeyboardButton(text='Пол'), KeyboardButton(text='Вес')],
        [KeyboardButton(text='Рост'), KeyboardButton(text='Возраст')],
        [KeyboardButton(text='Уровень активности'), KeyboardButton(text='Цель')],
        [KeyboardButton(text='Отмена')]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb)
    await message.answer('Что вы хотите изменить?', reply_markup=keyboard)
    await state.set_state(EditProfileStates.choosing_field)


@router.message(EditProfileStates.choosing_field)
async def process_field_choice(message: Message, state: FSMContext):
    field_choice = message.text
    field_mapping = {
        "Пол": ("gender", EditProfileStates.editing_gender),
        "Вес": ("weight", EditProfileStates.editing_weight),
        "Рост": ("height", EditProfileStates.editing_height),
        "Возраст": ("age", EditProfileStates.editing_age),
        "Уровень активности": ("activity_level", EditProfileStates.editing_activity),
        "Цель": ("goal_type", EditProfileStates.editing_goal)
    }
    if field_choice == 'Отмена':
        await message.answer('Изменение отменено', reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    if field_choice in field_mapping:
        field_name, next_state = field_mapping[field_choice]
        await state.update_data(editing_field=field_name)
        await state.set_state(next_state)
        if field_choice == "Пол":
            kb = [
                [KeyboardButton(text='Мужской'), KeyboardButton(text='Женский')]
            ]
            keyboard = ReplyKeyboardMarkup(keyboard=kb)
            await message.answer('Выберите пол:', reply_markup=keyboard)
        elif field_choice == "Уровень активности":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Минимальная (1.2)", callback_data="edit_activity_1.2"),
                    InlineKeyboardButton(text="Низкая (1.375)", callback_data="edit_activity_1.375")
                ],
                [
                    InlineKeyboardButton(text="Умеренная (1.55)", callback_data="edit_activity_1.55"),
                    InlineKeyboardButton(text="Высокая (1.725)", callback_data="edit_activity_1.725")
                ],
                [
                    InlineKeyboardButton(text="Очень высокая (1.9)", callback_data="edit_activity_1.9")
                ]
            ])
            await message.answer(
                'Выберите уровень активности:\n\n'
                'Минимальная (1.2) - сидячий образ жизни\n'
                'Низкая (1.375) - легкие упражнения 1-3 раза в неделю\n'
                'Умеренная (1.55) - умеренные упражнения 3-5 раз в неделю\n'
                'Высокая (1.725) - интенсивные упражнения 6-7 раз в неделю\n'
                'Очень высокая (1.9) - очень интенсивные упражнения, физическая работа',
                reply_markup=keyboard
            )
        elif field_choice == "Цель":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Поддержка веса", callback_data="edit_goal_maintain")
                ],
                [
                    InlineKeyboardButton(text="Похудение (-10%)", callback_data="edit_goal_lose"),
                    InlineKeyboardButton(text="Набор веса (+10%)", callback_data="edit_goal_gain")
                ]
            ])
            await message.answer(
                'Выберите вашу цель:\n\n'
                'Поддержка веса - базовая норма калорий\n'
                'Похудение - базовая норма - 10%\n'
                'Набор веса - базовая норма + 10%',
                reply_markup=keyboard
            )
        else:
            await message.answer('Введите данные, на которые вы хотите изменить: ')
    else:
        await message.answer('Пожалуйста, выберите поле из списка')


@router.message(EditProfileStates.editing_gender)
async def process_edit_gender(message: Message, state: FSMContext):
    gender_text = message.text.lower()
    if 'мужск' in gender_text:
        new_value = 'male'
    elif 'женск' in gender_text:
        new_value = 'female'
    else:
        await message.answer("Пожалуйста, выберите пол из предложенных вариантов.")
        return
    
    user_data = await state.get_data()
    field_name = user_data['editing_field']

    success = update_user_field(message.from_user.id, field_name, new_value)
    if success:
        user_profile = get_user_profile(message.from_user.id)
        if user_profile:
            new_calorie_goal = calc_calorie(
                user_profile.get("weight"),
                user_profile.get("height"),
                user_profile.get("age"),
                new_value,
                user_profile.get("activity_level")
            )
            update_user_field(message.from_user.id, "calorie_goal", new_calorie_goal)
        if message.from_user.id in user_dict:
            user_dict[message.from_user.id]['gender'] = new_value
        await message.answer('Пол успешно изменён', reply_markup=ReplyKeyboardRemove())
        await process_showdata_command(message)
    await state.clear()


@router.message(EditProfileStates.editing_weight)
async def process_edit_weight(message: Message, state: FSMContext):
    try:
        new_weight = float(message.text.replace(",", "."))
        if 0 < new_weight < 560:
            user_data = await state.get_data()
            field_name = user_data['editing_field']

            success = update_user_field(message.from_user.id, field_name, new_weight)
            if success:
                # Пересчитываем нормы
                user_profile = get_user_profile(message.from_user.id)
                if user_profile:
                    new_water_goal = calc_water(new_weight, user_profile.get("activity_level"))
                    new_calorie_goal = calc_calorie(
                        new_weight,
                        user_profile.get("height"),
                        user_profile.get("age"),
                        user_profile.get("gender"),
                        user_profile.get("activity_level")
                    )
                    update_user_field(message.from_user.id, "water_goal", new_water_goal)
                    update_user_field(message.from_user.id, "calorie_goal", new_calorie_goal)
                if message.from_user.id in user_dict:
                    user_dict[message.from_user.id]['weight'] = new_weight
                await message.answer(f'Вес успешно изменён на {new_weight} кг', reply_markup=ReplyKeyboardRemove())
                await process_showdata_command(message)
        else:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число")
    await state.clear()


@router.message(EditProfileStates.editing_height)
async def process_edit_height(message: Message, state: FSMContext):
    try:
        new_height = float(message.text.replace(",", "."))
        if 50 < new_height < 252:
            user_data = await state.get_data()
            field_name = user_data['editing_field']

            success = update_user_field(message.from_user.id, field_name, new_height)
            if success:
                # Пересчитываем калории
                user_profile = get_user_profile(message.from_user.id)
                if user_profile:
                    new_calorie_goal = calc_calorie(
                        user_profile.get("weight"),
                        new_height,
                        user_profile.get("age"),
                        user_profile.get("gender"),
                        user_profile.get("activity_level")
                    )
                    update_user_field(message.from_user.id, "calorie_goal", new_calorie_goal)
                if message.from_user.id in user_dict:
                    user_dict[message.from_user.id]['height'] = new_height
                await message.answer(f'Рост был изменен на {new_height}', reply_markup=ReplyKeyboardRemove())
                await process_showdata_command(message)
        else:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число")
    await state.clear()


@router.message(EditProfileStates.editing_age)
async def process_edit_age(message: Message, state: FSMContext):
    try:
        new_age = float(message.text.replace(",", "."))
        if 0 < new_age < 120:
            user_data = await state.get_data()
            field_name = user_data['editing_field']

            success = update_user_field(message.from_user.id, field_name, new_age)

            if success:
                # Пересчитываем калории
                user_profile = get_user_profile(message.from_user.id)
                if user_profile:
                    new_calorie_goal = calc_calorie(
                        user_profile.get("weight"),
                        user_profile.get("height"),
                        new_age,
                        user_profile.get("gender"),
                        user_profile.get("activity_level")
                    )
                    update_user_field(message.from_user.id, "calorie_goal", new_calorie_goal)
                if message.from_user.id in user_dict:
                    user_dict[message.from_user.id]['age'] = new_age

                await message.answer(f'Возраст успешно изменен на {new_age}', reply_markup=ReplyKeyboardRemove())
                await process_showdata_command(message)
        else:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число")
    await state.clear()


@router.callback_query(F.data.startswith("edit_activity_"), StateFilter(EditProfileStates.editing_activity))
async def process_edit_activity_callback(callback: CallbackQuery, state: FSMContext):
    new_activity = float(callback.data.split("_")[2])
    user_data = await state.get_data()
    field_name = user_data['editing_field']

    success = update_user_field(callback.from_user.id, field_name, new_activity)
    if success:
        user_profile = get_user_profile(callback.from_user.id)
        if user_profile:
            new_water_goal = calc_water(user_profile.get("weight"), new_activity)
            new_calorie_goal = calc_calorie(
                user_profile.get("weight"),
                user_profile.get("height"),
                user_profile.get("age"),
                user_profile.get("gender"),
                new_activity
            )
            update_user_field(callback.from_user.id, "water_goal", new_water_goal)
            update_user_field(callback.from_user.id, "calorie_goal", new_calorie_goal)
        if callback.from_user.id in user_dict:
            user_dict[callback.from_user.id]['activity_level'] = new_activity
        
        await callback.message.edit_text(f'✅ Уровень активности изменён на {new_activity}')
        await callback.answer()
        await callback.message.answer('Профиль обновлён', reply_markup=ReplyKeyboardRemove())

        user_profile = get_user_profile(callback.from_user.id)
        if user_profile:
            gender_text = "Мужской" if user_profile.get("gender") == "male" else "Женский"
            goal_type = user_profile.get("goal_type", "maintain")
            goal_text_display = {
                "maintain": "Поддержка веса",
                "lose": "Похудение (-10%)",
                "gain": "Набор веса (+10%)"
            }
            profile_text = ('Ваш профиль: \n\n'
                f'Пол: {gender_text}\n'
                f'Вес: {user_profile.get("weight")}\n'
                f'Рост: {user_profile.get("height")}\n'
                f'Возраст: {user_profile.get("age")}\n'
                f'Уровень активности: {user_profile.get("activity_level")}\n'
                f'Цель: {goal_text_display.get(goal_type, "Поддержка веса")}\n'
                f'Водная цель: {user_profile.get("water_goal")}\n'
                f'Цель по калориям: {user_profile.get("calorie_goal")}\n'
                'Чтобы изменить данные используйте /edit_profile\n'
                'Если хотите удалить профиль используйте /delete_profile'
            )
            await callback.message.answer(profile_text)
    await state.clear()


@router.callback_query(F.data.startswith("edit_goal_"), StateFilter(EditProfileStates.editing_goal))
async def process_edit_goal_callback(callback: CallbackQuery, state: FSMContext):
    new_goal = callback.data.split("_")[2]
    user_data = await state.get_data()
    field_name = user_data['editing_field']

    success = update_user_field(callback.from_user.id, field_name, new_goal)
    if success:
        user_profile = get_user_profile(callback.from_user.id)
        if user_profile:
            base_calorie = calc_calorie(
                user_profile.get("weight"),
                user_profile.get("height"),
                user_profile.get("age"),
                user_profile.get("gender"),
                user_profile.get("activity_level")
            )
            new_calorie_goal = calc_calorie_with_goal(base_calorie, new_goal)
            update_user_field(callback.from_user.id, "calorie_goal", new_calorie_goal)
        
        if callback.from_user.id in user_dict:
            user_dict[callback.from_user.id]['goal_type'] = new_goal
        
        goal_text = {
            "maintain": "поддержка веса",
            "lose": "похудение (-10%)",
            "gain": "набор веса (+10%)"
        }
        
        await callback.message.edit_text(f'✅ Цель изменена на: {goal_text[new_goal]}')
        await callback.answer()
        await callback.message.answer('Профиль обновлён', reply_markup=ReplyKeyboardRemove())

        user_profile = get_user_profile(callback.from_user.id)
        if user_profile:
            gender_text = "Мужской" if user_profile.get("gender") == "male" else "Женский"
            goal_type = user_profile.get("goal_type", "maintain")
            goal_text_display = {
                "maintain": "Поддержка веса",
                "lose": "Похудение (-10%)",
                "gain": "Набор веса (+10%)"
            }
            profile_text = ('Ваш профиль: \n\n'
                f'Пол: {gender_text}\n'
                f'Вес: {user_profile.get("weight")}\n'
                f'Рост: {user_profile.get("height")}\n'
                f'Возраст: {user_profile.get("age")}\n'
                f'Уровень активности: {user_profile.get("activity_level")}\n'
                f'Цель: {goal_text_display.get(goal_type, "Поддержка веса")}\n'
                f'Водная цель: {user_profile.get("water_goal")}\n'
                f'Цель по калориям: {user_profile.get("calorie_goal")}\n'
                'Чтобы изменить данные используйте /edit_profile\n'
                'Если хотите удалить профиль используйте /delete_profile'
            )
            await callback.message.answer(profile_text)
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


@router.message(StateFilter(default_state), F.text, ~F.text.startswith("/"))
async def process_food_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_profile = get_user_profile(user_id)
    
    if not user_profile:
        await message.answer("Сначала настройте профиль командой /set_profile")
        return

    processing_msg = await message.answer("🔍 Анализирую блюдо...")

    description = message.text
    result = await analyze_food_text(description)
    
    if result and "total_calories" in result:
        dish_name = result.get("dish_name", description)
        grams = float(result.get("grams", 0))
        calories_per_100g = float(result.get("calories_per_100g", 0))
        total_calories = float(result.get("total_calories", 0))

        await state.update_data(
            dish_name=dish_name,
            description=description,
            grams=grams,
            calories_per_100g=calories_per_100g,
            total_calories=total_calories
        )

        await processing_msg.delete()
        result_text = (
            f"🍽 <b>{dish_name}</b>\n\n"
            f"📊 Количество: {int(grams)} г\n"
            f"🔥 Калории на 100г: {int(calories_per_100g)} ккал\n"
            f"⚡ Общее количество калорий: {int(total_calories)} ккал"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Записать", callback_data="food_record"),
                InlineKeyboardButton(text="✏️ Исправить", callback_data="food_correct")
            ]
        ])
        
        await message.answer(result_text, reply_markup=keyboard, parse_mode="HTML")
        await state.set_state(FoodCorrectionStates.choosing_correction_type)
    elif result and "calories" in result:
        dish_name = result.get("dish_name", description)
        calories = float(result.get("calories", 0))

        add_food_entry(user_id, description, calories)

        daily_calories = get_daily_calories(user_id)
        calorie_goal = user_profile.get("calorie_goal", 0)
        remaining = max(0, calorie_goal - daily_calories)
        percentage = (daily_calories / calorie_goal * 100) if calorie_goal > 0 else 0
        
        await processing_msg.delete()
        await message.answer(
            f"✅ Блюдо записано!\n\n"
            f"🍽 {dish_name}\n"
            f"🔥 Калории: {calories:.0f} ккал\n\n"
            f"📊 Прогресс за сегодня:\n"
            f"Съедено: {daily_calories:.0f} / {calorie_goal:.0f} ккал ({percentage:.1f}%)\n"
            f"Осталось: {remaining:.0f} ккал"
        )
    else:
        await processing_msg.delete()
        await message.answer(
            "❌ Не удалось определить калорийность блюда.\n"
            "Попробуйте описать блюдо более подробно или отправьте фото."
        )


@router.callback_query(F.data == "food_record", StateFilter(FoodCorrectionStates.choosing_correction_type))
async def process_food_record(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id
    user_profile = get_user_profile(user_id)
    
    description = data.get("description", "")
    total_calories = data.get("total_calories", 0)

    add_food_entry(user_id, description, total_calories)

    daily_calories = get_daily_calories(user_id)
    calorie_goal = user_profile.get("calorie_goal", 0) if user_profile else 0
    remaining = max(0, calorie_goal - daily_calories)
    percentage = (daily_calories / calorie_goal * 100) if calorie_goal > 0 else 0
    
    await callback.message.edit_text("✅ Блюдо записано!")
    await callback.answer()
    
    await callback.message.answer(
        f"📊 Прогресс за сегодня:\n"
        f"Съедено: {daily_calories:.0f} / {calorie_goal:.0f} ккал ({percentage:.1f}%)\n"
        f"Осталось: {remaining:.0f} ккал"
    )
    await state.clear()


@router.callback_query(F.data == "food_correct", StateFilter(FoodCorrectionStates.choosing_correction_type))
async def process_food_correct(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Исправить граммы", callback_data="correct_grams")
        ],
        [
            InlineKeyboardButton(text="Исправить калории", callback_data="correct_calories")
        ]
    ])
    
    await callback.message.edit_text(
        "Что вы хотите исправить?",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "correct_grams", StateFilter(FoodCorrectionStates.choosing_correction_type))
async def process_correct_grams_choice(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите новое количество грамм:")
    await callback.answer()
    await state.set_state(FoodCorrectionStates.correcting_grams)


@router.message(FoodCorrectionStates.correcting_grams)
async def process_correct_grams_input(message: Message, state: FSMContext):
    try:
        new_grams = float(message.text.replace(",", "."))
        if new_grams <= 0:
            raise ValueError
        
        data = await state.get_data()
        calories_per_100g = data.get("calories_per_100g", 0)

        new_total_calories = (calories_per_100g * new_grams) / 100

        await state.update_data(grams=new_grams, total_calories=new_total_calories)
        
        dish_name = data.get("dish_name", "Блюдо")
        result_text = (
            f"🍽 <b>{dish_name}</b>\n\n"
            f"📊 Количество: {int(new_grams)} г\n"
            f"🔥 Калории на 100г: {int(calories_per_100g)} ккал\n"
            f"⚡ Общее количество калорий: {int(new_total_calories)} ккал"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Записать", callback_data="food_record"),
                InlineKeyboardButton(text="✏️ Исправить", callback_data="food_correct")
            ]
        ])
        
        await message.answer(result_text, reply_markup=keyboard, parse_mode="HTML")
        await state.set_state(FoodCorrectionStates.choosing_correction_type)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число грамм (например: 200)")


@router.callback_query(F.data == "correct_calories", StateFilter(FoodCorrectionStates.choosing_correction_type))
async def process_correct_calories_choice(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите новое количество калорий:")
    await callback.answer()
    await state.set_state(FoodCorrectionStates.correcting_calories)


@router.message(FoodCorrectionStates.correcting_calories)
async def process_correct_calories_input(message: Message, state: FSMContext):
    try:
        new_calories = float(message.text.replace(",", "."))
        if new_calories < 0:
            raise ValueError

        await state.update_data(total_calories=new_calories)
        
        data = await state.get_data()
        dish_name = data.get("dish_name", "Блюдо")
        grams = data.get("grams", 0)
        
        result_text = (
            f"🍽 <b>{dish_name}</b>\n\n"
            f"📊 Количество: {int(grams)} г\n"
            f"⚡ Общее количество калорий: {int(new_calories)} ккал"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Записать", callback_data="food_record"),
                InlineKeyboardButton(text="✏️ Исправить", callback_data="food_correct")
            ]
        ])
        
        await message.answer(result_text, reply_markup=keyboard, parse_mode="HTML")
        await state.set_state(FoodCorrectionStates.choosing_correction_type)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число калорий (например: 350)")

@router.message(Command("вода", "water"))
async def cmd_water(message: Message):
    user_id = message.from_user.id
    user_profile = get_user_profile(user_id)
    
    if not user_profile:
        await message.answer("Сначала настройте профиль командой /set_profile")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /вода <количество> или /water <количество>\nНапример: /вода 250")
        return
    
    try:
        amount = float(parts[1].replace(",", "."))
        if amount <= 0:
            raise ValueError

        add_water_entry(user_id, amount)

        daily_water = get_daily_water(user_id)
        water_goal = user_profile.get("water_goal", 0)
        remaining = max(0, water_goal - daily_water)
        percentage = (daily_water / water_goal * 100) if water_goal > 0 else 0
        
        await message.answer(
            f"✅ Добавлено {amount:.0f} мл воды\n\n"
            f"💧 Прогресс за сегодня:\n"
            f"Выпито: {daily_water:.0f} / {water_goal:.0f} мл ({percentage:.1f}%)\n"
            f"Осталось: {remaining:.0f} мл"
        )
    except ValueError:
        await message.answer("Пожалуйста, введите корректное количество (например: /вода 250)")


@router.message(Command("progress"))
async def cmd_progress(message: Message):
    user_id = message.from_user.id
    user_profile = get_user_profile(user_id)
    
    if not user_profile:
        await message.answer("Сначала настройте профиль командой /set_profile")
        return
    
    daily_calories = get_daily_calories(user_id)
    daily_water = get_daily_water(user_id)
    calorie_goal = user_profile.get("calorie_goal", 0)
    water_goal = user_profile.get("water_goal", 0)
    
    calories_percentage = (daily_calories / calorie_goal * 100) if calorie_goal > 0 else 0
    water_percentage = (daily_water / water_goal * 100) if water_goal > 0 else 0
    
    progress_text = (
        f"📊 Прогресс за {date.today().strftime('%d.%m.%Y')}:\n\n"
        f"🔥 Калории:\n"
        f"Съедено: {daily_calories:.0f} / {calorie_goal:.0f} ккал ({calories_percentage:.1f}%)\n"
        f"Осталось: {max(0, calorie_goal - daily_calories):.0f} ккал\n\n"
        f"💧 Вода:\n"
        f"Выпито: {daily_water:.0f} / {water_goal:.0f} мл ({water_percentage:.1f}%)\n"
        f"Осталось: {max(0, water_goal - daily_water):.0f} мл"
    )
    await message.answer(progress_text)

@router.message(F.photo, StateFilter(default_state))
async def process_food_photo(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_profile = get_user_profile(user_id)
    
    if not user_profile:
        await message.answer("Сначала настройте профиль командой /set_profile")
        return

    processing_msg = await message.answer("🔍 Анализирую фото...")

    photo = message.photo[-1]  # Берем фото наибольшего размера
    photo_bytes = await download_photo_from_telegram(message.bot, photo)
    
    if not photo_bytes:
        await processing_msg.delete()
        await message.answer("❌ Не удалось загрузить фото. Попробуйте еще раз.")
        return

    result = await analyze_food_photo(photo_bytes)
    
    if result and "total_calories" in result:
        dish_name = result.get("dish_name", "Блюдо")
        grams = float(result.get("grams", 0))
        calories_per_100g = float(result.get("calories_per_100g", 0))
        total_calories = float(result.get("total_calories", 0))
        description = result.get("description", "")

        await state.update_data(
            dish_name=dish_name,
            description=description,
            grams=grams,
            calories_per_100g=calories_per_100g,
            total_calories=total_calories
        )

        await processing_msg.delete()
        result_text = (
            f"🍽 <b>{dish_name}</b>\n\n"
            f"📊 Количество: {int(grams)} г\n"
            f"🔥 Калории на 100г: {int(calories_per_100g)} ккал\n"
            f"⚡ Общее количество калорий: {int(total_calories)} ккал"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Записать", callback_data="photo_record"),
                InlineKeyboardButton(text="✏️ Исправить", callback_data="photo_correct")
            ]
        ])
        
        await message.answer(result_text, reply_markup=keyboard, parse_mode="HTML")
        await state.set_state(FoodCorrectionStates.choosing_correction_type)
    else:
        await processing_msg.delete()
        await message.answer(
            "❌ Не удалось определить блюдо на фото.\n"
            "Попробуйте отправить более четкое фото или опишите блюдо текстом."
        )


@router.callback_query(F.data == "photo_record", StateFilter(FoodCorrectionStates.choosing_correction_type))
async def process_photo_record(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id
    user_profile = get_user_profile(user_id)
    
    description = data.get("description", "")
    total_calories = data.get("total_calories", 0)

    add_food_entry(user_id, description, total_calories)

    daily_calories = get_daily_calories(user_id)
    calorie_goal = user_profile.get("calorie_goal", 0) if user_profile else 0
    remaining = max(0, calorie_goal - daily_calories)
    percentage = (daily_calories / calorie_goal * 100) if calorie_goal > 0 else 0
    
    await callback.message.edit_text("✅ Блюдо записано!")
    await callback.answer()
    
    await callback.message.answer(
        f"📊 Прогресс за сегодня:\n"
        f"Съедено: {daily_calories:.0f} / {calorie_goal:.0f} ккал ({percentage:.1f}%)\n"
        f"Осталось: {remaining:.0f} ккал"
    )
    await state.clear()


@router.callback_query(F.data == "photo_correct", StateFilter(FoodCorrectionStates.choosing_correction_type))
async def process_photo_correct(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Исправить граммы", callback_data="correct_grams")
        ],
        [
            InlineKeyboardButton(text="Исправить калории", callback_data="correct_calories")
        ]
    ])
    
    await callback.message.edit_text(
        "Что вы хотите исправить?",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("photo_save_"))
async def process_photo_save_old(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    
    dish_name = data.get("photo_dish_name", "Блюдо")
    calories = data.get("photo_calories", 0)
    description = data.get("photo_description", dish_name)

    add_food_entry(user_id, description, calories)

    user_profile = get_user_profile(user_id)
    daily_calories = get_daily_calories(user_id)
    calorie_goal = user_profile.get("calorie_goal", 0) if user_profile else 0
    remaining = max(0, calorie_goal - daily_calories)
    percentage = (daily_calories / calorie_goal * 100) if calorie_goal > 0 else 0
    
    await callback.message.edit_text(
        f"✅ Блюдо записано!\n\n"
        f"🍽 {dish_name}\n"
        f"🔥 Калории: {calories:.0f} ккал\n\n"
        f"📊 Прогресс за сегодня:\n"
        f"Съедено: {daily_calories:.0f} / {calorie_goal:.0f} ккал ({percentage:.1f}%)\n"
        f"Осталось: {remaining:.0f} ккал"
    )
    await callback.answer()
    await state.clear()


@router.callback_query(F.data.startswith("photo_edit_"))
async def process_photo_edit_old(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите правильное количество калорий для этого блюда:"
    )
    await state.set_state(PhotoRecognitionStates.waiting_for_correction)
    await callback.answer()


@router.message(PhotoRecognitionStates.waiting_for_correction)
async def process_calorie_correction_old(message: Message, state: FSMContext):
    try:
        calories = float(message.text.replace(",", "."))
        if calories < 0:
            raise ValueError
        
        user_id = message.from_user.id
        data = await state.get_data()
        dish_name = data.get("photo_dish_name", "Блюдо")
        description = data.get("photo_description", dish_name)

        add_food_entry(user_id, description, calories)

        user_profile = get_user_profile(user_id)
        daily_calories = get_daily_calories(user_id)
        calorie_goal = user_profile.get("calorie_goal", 0) if user_profile else 0
        remaining = max(0, calorie_goal - daily_calories)
        percentage = (daily_calories / calorie_goal * 100) if calorie_goal > 0 else 0
        
        await message.answer(
            f"✅ Блюдо записано с исправленными данными!\n\n"
            f"🍽 {dish_name}\n"
            f"🔥 Калории: {calories:.0f} ккал\n\n"
            f"📊 Прогресс за сегодня:\n"
            f"Съедено: {daily_calories:.0f} / {calorie_goal:.0f} ккал ({percentage:.1f}%)\n"
            f"Осталось: {remaining:.0f} ккал"
        )
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число калорий")

@router.message(Command("статистика", "stats", "stats_day", "stats_month"))
async def cmd_statistics(message: Message):
    user_id = message.from_user.id
    user_profile = get_user_profile(user_id)
    
    if not user_profile:
        await message.answer("Сначала настройте профиль командой /set_profile")
        return
    
    command = message.text.split()[0].lower()

    if command in ["/stats_day", "/stats_day@healthdietbot"]:
        period = "day"
    elif command in ["/stats_month", "/stats_month@healthdietbot"]:
        period = "month"
    else:
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Использование:\n/статистика день или /stats_day - график за сегодня\n/статистика месяц или /stats_month - график за текущий месяц")
            return
        period = parts[1].lower()

    if period in ["день", "day"]:
        chart = generate_daily_chart(user_id)
        if chart:
            photo = BufferedInputFile(chart.read(), filename="daily_stats.png")
            await message.answer_photo(photo)
        else:
            await message.answer("Нет данных за сегодня")
    
    elif period in ["месяц", "month"]:
        chart = generate_monthly_chart(user_id)
        if chart:
            photo = BufferedInputFile(chart.read(), filename="monthly_stats.png")
            await message.answer_photo(photo)
        else:
            await message.answer("Нет данных за текущий месяц")
    
    else:
        await message.answer("Используйте: /статистика день или /stats_day - график за сегодня\n/статистика месяц или /stats_month - график за месяц")


def setup_handlers(dp):
    dp.include_router(router)



