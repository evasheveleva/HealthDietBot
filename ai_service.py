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
    prompt = f"""Ты помощник для подсчёта калорий. Проанализируй описание блюда и определи:
1. Название блюда
2. Количество грамм (извлеки из текста, если указано, иначе оцени примерное количество)
3. Калории на 100 грамм
4. Общее количество калорий

Описание блюда: {description}

Верни ответ ТОЛЬКО в формате JSON:
{{
    "dish_name": "название блюда",
    "grams": число_грамм,
    "calories_per_100g": калории_на_100г,
    "total_calories": общее_количество_калорий,
    "description": "краткое описание блюда"
}}

Важно:
- ВНИМАТЕЛЬНО извлекай количество грамм из текста (например: "лазанья 200 грамм" = 200г)
- Если граммы не указаны, оцени примерное количество на основе описания
- Рассчитывай калории на 100г для данного блюда
- Общее количество калорий = (calories_per_100g * grams) / 100
- Если указано несколько блюд, суммируй граммы и калории
- Будь точным, учитывай все указанные количества
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

        import json
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
    base64_image = base64.b64encode(photo_file).decode('utf-8')
    
    prompt = """Ты помощник для подсчёта калорий. Проанализируй фотографию блюда и определи:
1. Название блюда
2. Примерное количество грамм на фото (оцени визуально размер порции)
3. Калории на 100 грамм для данного блюда
4. Общее количество калорий для порции на фото

Верни ответ ТОЛЬКО в формате JSON:
{
    "dish_name": "название блюда",
    "grams": примерное_количество_грамм,
    "calories_per_100g": калории_на_100г,
    "total_calories": общее_количество_калорий,
    "description": "краткое описание блюда и порции"
}

Важно:
- ВНИМАТЕЛЬНО оцени количество грамм на основе размера порции на фото
- Рассчитывай калории на 100г для данного блюда
- Общее количество калорий = (calories_per_100g * grams) / 100
- Будь максимально точным, учитывай размер порции на фото
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

        import json
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
