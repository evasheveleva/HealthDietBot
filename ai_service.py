import base64
import io
from typing import Optional, Dict, Any
from openai import OpenAI
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from aiogram.types import PhotoSize

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL
)


async def analyze_food_text(description: str) -> Optional[Dict[str, Any]]:
    prompt = f"""Ты помощник для подсчёта калорий. Проанализируй описание блюда и определи примерную калорийность.

Описание блюда: {description}

Верни ответ ТОЛЬКО в формате JSON:
{{
    "dish_name": "название блюда",
    "calories": число_калорий,
    "description": "краткое описание блюда"
}}

Важно:
- Укажи калорийность для стандартной порции (примерно 200-300г для основных блюд)
- Если указано несколько блюд, суммируй калории
- Будь точным, но если точно определить нельзя, укажи примерную оценку
- Отвечай на русском языке"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты помощник для подсчёта калорий. Отвечай только в формате JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        content = response.choices[0].message.content.strip()
        
        # Парсим JSON ответ
        import json
        # Убираем markdown код блоки если есть
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        result = json.loads(content)
        return result
        
    except Exception as e:
        print(f"Ошибка при анализе текста: {e}")
        return None


async def analyze_food_photo(photo_file: bytes) -> Optional[Dict[str, Any]]:
    # Конвертируем изображение в base64
    base64_image = base64.b64encode(photo_file).decode('utf-8')
    
    prompt = """Ты помощник для подсчёта калорий. Проанализируй фотографию блюда и определи:
1. Что это за блюдо
2. Примерную калорийность для порции на фото

Верни ответ ТОЛЬКО в формате JSON:
{
    "dish_name": "название блюда",
    "calories": число_калорий,
    "description": "краткое описание блюда и порции"
}

Важно:
- Оцени калорийность для порции, которая видна на фото
- Будь максимально точным, но если точно определить нельзя, укажи примерную оценку
- Учитывай размер порции на фото
- Отвечай на русском языке"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.3,
            max_tokens=300
        )
        
        content = response.choices[0].message.content.strip()
        
        # Парсим JSON ответ
        import json
        # Убираем markdown код блоки если есть
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        result = json.loads(content)
        return result
        
    except Exception as e:
        print(f"Ошибка при анализе фото: {e}")
        return None


async def download_photo_from_telegram(bot, photo: PhotoSize) -> Optional[bytes]:
    try:
        file = await bot.get_file(photo.file_id)
        photo_bytes = await bot.download_file(file.file_path)
        return photo_bytes.read()
    except Exception as e:
        print(f"Ошибка при скачивании фото: {e}")
        return None
