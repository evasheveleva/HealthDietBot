import os
import sys
import dotenv

dotenv.load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Database
DB_NAME = os.getenv("DB_NAME", "healthdietbot.db")

if not TELEGRAM_TOKEN:
    print("ОШИБКА: TELEGRAM_TOKEN не установлен в .env файле!")
    sys.exit(1)

if not OPENROUTER_API_KEY:
    print("ОШИБКА: OPENROUTER_API_KEY не установлен в .env файле!")
    sys.exit(1)

