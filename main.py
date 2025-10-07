import asyncio
from aiogram import Bot, Dispatcher
from config import TELEGRAM_TOKEN
from middlewares import LoggingMiddleware
from handlers import setup_handlers

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

dp.message.middleware(LoggingMiddleware())
setup_handlers(dp)

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен')