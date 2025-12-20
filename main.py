import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from config import TELEGRAM_TOKEN
from middlewares import LoggingMiddleware
from handlers import setup_handlers
from db import init_db

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Начало работы"),
        BotCommand(command="set_profile", description="Настройка профиля"),
        BotCommand(command="profile", description="Просмотр профиля"),
        BotCommand(command="edit_profile", description="Редактирование профиля"),
        BotCommand(command="progress", description="Прогресс за сегодня"),
        BotCommand(command="stats_day", description="Статистика за день"),
        BotCommand(command="stats_month", description="Статистика за месяц"),
        BotCommand(command="water", description="Добавить воду"),
        BotCommand(command="help", description="Помощь")
    ]
    await bot.set_my_commands(commands)

async def main():
    init_db()
    
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher()
    
    dp.message.middleware(LoggingMiddleware())
    setup_handlers(dp)
    
    await set_bot_commands(bot)

    bot_info = await bot.get_me()
    bot_username = bot_info.username if bot_info.username else "N/A"
    print(f"Бот запущен! @{bot_username}")
    
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен')
    except Exception as e:
        print(f'Ошибка при запуске бота: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

