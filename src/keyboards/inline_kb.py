from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

def ease_link_kb():
    inline_kb_list = [
        [InlineKeyboardButton(text='Для связи в телеграм', url='tg://resolve?domain=Warislav')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)

def contacs_link():
    inline_kb_list = [
        [InlineKeyboardButton(text='Контакты для связи', callback_data='contacts')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)

def geo_link():
    inline_kb_list = [
        [InlineKeyboardButton(text='Мы на карте 📍', web_app=WebAppInfo(url="https://yandex.ru/maps/-/CHF3QR8s"))]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)

def ease_link_kb():
    inline_kb_list = [
        [InlineKeyboardButton(text='Для связи в телеграм', url='tg://resolve?domain=Warislav')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)



