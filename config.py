import telebot
import os
import dotenv

dotenv.load_dotenv('D:/k/1.env')

TELEGRAM_TOKEN=os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TELEGRAM_TOKEN)
