from aiogram.types import Message
from aiogram import F
from aiogram import Bot
from create_bot import bot
MAX_LEN = 4096

async def send_long_message(text: str):
    """
    Отправка длинного текста частями (если превышает лимит Telegram).
    """
    # делим текст на куски по MAX_LEN символов
    for i in range(0, len(text), MAX_LEN):
        await bot.send_message(-1003074142093, text[i:i+MAX_LEN], parse_mode=None)