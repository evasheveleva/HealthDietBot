from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery, FSInputFile, BufferedInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from states import User, EditProfileStates, PhotoRecognitionStates, DeleteProfileStates
from calculation import calc_water, calc_calorie
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


# ==================== РЕГИСТРАЦИЯ ====================

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
            await message.answer(
                "Выберите уровень активности:\n\n"
                "1.2 - Минимальная активность (сидячий образ жизни)\n"
                "1.375 - Низкая активность (легкие упражнения 1-3 раза в неделю)\n"
                "1.55 - Умеренная активность (умеренные упражнения 3-5 раз в неделю)\n"
                "1.725 - Высокая активность (интенсивные упражнения 6-7 раз в неделю)\n"
                "1.9 - Очень высокая активность (очень интенсивные упражнения, физическая работа)\n\n"
                "Введите коэффициент активности (например: 1.55):"
            )
            await state.set_state(User.activity_level)
        else:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число (например: 25)")


@router.message(User.activity_level)
async def process_activity_level(message: Message, state: FSMContext):
    try:
        activity_level = float(message.text.replace(",", "."))
        if 1.2 <= activity_level <= 1.9:
            await state.update_data(activity_level=activity_level)
            
            # Получаем данные и рассчитываем нормы
            data = await state.get_data()
            water_goal = calc_water(data.get("weight"), activity_level)
            calorie_goal = calc_calorie(
                data.get("weight"),
                data.get("height"),
                data.get("age"),
                data.get("gender"),
                activity_level
            )
            
            await state.update_data(water_goal=water_goal, calorie_goal=calorie_goal)
            
            await message.answer(f"✅ Ваша суточная норма воды: {water_goal} мл")
            await message.answer(f"✅ Ваша суточная норма калорий: {calorie_goal} ккал")
            
            # Сохраняем в БД
            user_data = await state.get_data()
            user_id = message.from_user.id
            
            user_dict[user_id] = user_data
            save_user_to_db(user_id, user_data)
            
            await message.answer("Профиль успешно сохранен!")
            await state.clear()
        else:
            await message.answer("Пожалуйста, введите коэффициент от 1.2 до 1.9")
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число (например: 1.55)")


# ==================== УПРАВЛЕНИЕ ПРОФИЛЕМ ====================

@router.message(Command(commands='profile'), StateFilter(default_state))
async def process_showdata_command(message: Message):
    user_id = message.from_user.id
    user_profile = get_user_profile(user_id)

    if user_profile:
        gender_text = "Мужской" if user_profile.get("gender") == "male" else "Женский"
        profile_text = ('Ваш профиль: \n\n'
            f'Пол: {gender_text}\n'
            f'Вес: {user_profile.get("weight")}\n'
            f'Рост: {user_profile.get("height")}\n'
            f'Возраст: {user_profile.get("age")}\n'
            f'Уровень активности: {user_profile.get("activity_level")}\n'
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
        [KeyboardButton(text='Уровень активности'), KeyboardButton(text='Отмена')]
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
        "Уровень активности": ("activity_level", EditProfileStates.editing_activity)
    }
    if field_choice == 'Отмена':
        await message.answer('Изменение отменено')
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
        # Пересчитываем калории при изменении пола
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
        await message.answer('Пол успешно изменён')
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
                await message.answer(f'Вес успешно изменён на {new_weight} кг')
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
                await message.answer(f'Рост был изменен на {new_height}')
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

                await message.answer(f'Возраст успешно изменен на {new_age}')
                await process_showdata_command(message)
        else:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число")
    await state.clear()


@router.message(EditProfileStates.editing_activity)
async def process_edit_activity(message: Message, state: FSMContext):
    try:
        new_activity = float(message.text.replace(",", "."))
        if 1.2 <= new_activity <= 1.9:
            user_data = await state.get_data()
            field_name = user_data['editing_field']

            success = update_user_field(message.from_user.id, field_name, new_activity)
            if success:
                # Пересчитываем нормы
                user_profile = get_user_profile(message.from_user.id)
                if user_profile:
                    new_water_goal = calc_water(user_profile.get("weight"), new_activity)
                    new_calorie_goal = calc_calorie(
                        user_profile.get("weight"),
                        user_profile.get("height"),
                        user_profile.get("age"),
                        user_profile.get("gender"),
                        new_activity
                    )
                    update_user_field(message.from_user.id, "water_goal", new_water_goal)
                    update_user_field(message.from_user.id, "calorie_goal", new_calorie_goal)
                if message.from_user.id in user_dict:
                    user_dict[message.from_user.id]['activity_level'] = new_activity
                await message.answer(f'Уровень активности изменено на {new_activity}')
                await process_showdata_command(message)
        else:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите коэффициент от 1.2 до 1.9")
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


# ==================== УЧЁТ ЕДЫ ТЕКСТОМ ====================

@router.message(StateFilter(default_state), F.text, ~F.text.startswith("/"))
async def process_food_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_profile = get_user_profile(user_id)
    
    if not user_profile:
        await message.answer("Сначала настройте профиль командой /set_profile")
        return
    
    # Показываем, что обрабатываем
    processing_msg = await message.answer("🔍 Анализирую блюдо...")
    
    # Анализируем через AI
    description = message.text
    result = await analyze_food_text(description)
    
    if result and "calories" in result:
        dish_name = result.get("dish_name", description)
        calories = float(result.get("calories", 0))
        
        # Сохраняем в БД
        add_food_entry(user_id, description, calories)
        
        # Получаем прогресс
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


# ==================== УЧЁТ ВОДЫ ====================

@router.message(Command("вода"))
async def cmd_water(message: Message):
    user_id = message.from_user.id
    user_profile = get_user_profile(user_id)
    
    if not user_profile:
        await message.answer("Сначала настройте профиль командой /set_profile")
        return
    
    # Парсим количество из команды
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /вода <количество>\nНапример: /вода 250")
        return
    
    try:
        amount = float(parts[1].replace(",", "."))
        if amount <= 0:
            raise ValueError
        
        # Сохраняем в БД
        add_water_entry(user_id, amount)
        
        # Получаем прогресс
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


# ==================== ОПРЕДЕЛЕНИЕ БЛЮДА ПО ФОТО ====================

@router.message(F.photo, StateFilter(default_state))
async def process_food_photo(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_profile = get_user_profile(user_id)
    
    if not user_profile:
        await message.answer("Сначала настройте профиль командой /set_profile")
        return
    
    # Показываем, что обрабатываем
    processing_msg = await message.answer("🔍 Анализирую фото...")
    
    # Скачиваем фото
    photo = message.photo[-1]  # Берем фото наибольшего размера
    photo_bytes = await download_photo_from_telegram(message.bot, photo)
    
    if not photo_bytes:
        await processing_msg.delete()
        await message.answer("❌ Не удалось загрузить фото. Попробуйте еще раз.")
        return
    
    # Анализируем через AI
    result = await analyze_food_photo(photo_bytes)
    
    if result and "calories" in result:
        dish_name = result.get("dish_name", "Блюдо")
        calories = float(result.get("calories", 0))
        description = result.get("description", "")
        
        # Сохраняем во временное состояние
        await state.update_data(
            photo_dish_name=dish_name,
            photo_calories=calories,
            photo_description=description
        )
        
        # Создаем кнопки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Записать", callback_data=f"photo_save_{user_id}"),
                InlineKeyboardButton(text="✏️ Исправить", callback_data=f"photo_edit_{user_id}")
            ]
        ])
        
        await processing_msg.delete()
        await message.answer(
            f"🍽 Определено блюдо:\n\n"
            f"Название: {dish_name}\n"
            f"Калории: {calories:.0f} ккал\n"
            f"Описание: {description}\n\n"
            f"Что делать дальше?",
            reply_markup=keyboard
        )
    else:
        await processing_msg.delete()
        await message.answer(
            "❌ Не удалось определить блюдо на фото.\n"
            "Попробуйте отправить более четкое фото или опишите блюдо текстом."
        )


@router.callback_query(F.data.startswith("photo_save_"))
async def process_photo_save(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    
    dish_name = data.get("photo_dish_name", "Блюдо")
    calories = data.get("photo_calories", 0)
    description = data.get("photo_description", dish_name)
    
    # Сохраняем в БД
    add_food_entry(user_id, description, calories)
    
    # Получаем прогресс
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
async def process_photo_edit(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите правильное количество калорий для этого блюда:"
    )
    await state.set_state(PhotoRecognitionStates.waiting_for_correction)
    await callback.answer()


@router.message(PhotoRecognitionStates.waiting_for_correction)
async def process_calorie_correction(message: Message, state: FSMContext):
    try:
        calories = float(message.text.replace(",", "."))
        if calories < 0:
            raise ValueError
        
        user_id = message.from_user.id
        data = await state.get_data()
        dish_name = data.get("photo_dish_name", "Блюдо")
        description = data.get("photo_description", dish_name)
        
        # Сохраняем в БД с исправленными калориями
        add_food_entry(user_id, description, calories)
        
        # Получаем прогресс
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


@router.message(Command("статистика"))
async def cmd_statistics(message: Message):
    user_id = message.from_user.id
    user_profile = get_user_profile(user_id)
    
    if not user_profile:
        await message.answer("Сначала настройте профиль командой /set_profile")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование:\n/статистика день - график за сегодня\n/статистика месяц - график за текущий месяц")
        return
    
    period = parts[1].lower()
    
    if period == "день":
        chart = generate_daily_chart(user_id)
        if chart:
            photo = BufferedInputFile(chart.read(), filename="daily_stats.png")
            await message.answer_photo(photo)
        else:
            await message.answer("Нет данных за сегодня")
    
    elif period == "месяц":
        chart = generate_monthly_chart(user_id)
        if chart:
            photo = BufferedInputFile(chart.read(), filename="monthly_stats.png")
            await message.answer_photo(photo)
        else:
            await message.answer("Нет данных за текущий месяц")
    
    else:
        await message.answer("Используйте: /статистика день или /статистика месяц")

def setup_handlers(dp):
    dp.include_router(router)

