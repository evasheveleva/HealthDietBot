import asyncio
import sys
from aiogram import Bot, Dispatcher
from config import TELEGRAM_TOKEN
from middlewares import LoggingMiddleware
from handlers import setup_handlers
from db import init_db

async def main():
    init_db()
    
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher()
    
    dp.message.middleware(LoggingMiddleware())
    setup_handlers(dp)
    
    print("Бот запущен!")
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
