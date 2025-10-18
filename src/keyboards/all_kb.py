from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from create_bot import db_connector


def main_kb(user_telegram_id: int):
    kb_list = [
        [KeyboardButton(text="📖 О нас"), KeyboardButton(text="💸 Прайс-лист")],
        [KeyboardButton(text="📝 Отзывы клиентов")],
        [KeyboardButton(text="💇‍♀️ Записаться к мастеру")],
        [KeyboardButton(text='📋 Мои записи')],
        [KeyboardButton(text='🛠 Выдать права администратора')],
    ]
    if user_telegram_id in db_connector.admins_cache:
        kb_list.append([KeyboardButton(text="⚙️ Админ-панель")])
    if user_telegram_id in db_connector.employee_cache:
        kb_list.append([KeyboardButton(text="⚙️ Кабинет-сотрудника")])
    else:
        kb_list.append([KeyboardButton(text='👨‍🔧 Выдать права сотрудника')])
    keyboard = ReplyKeyboardMarkup(
        keyboard=kb_list,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Воспользуйтесь меню:"
    )
    return keyboard

def admin_kb(user_telegram_id: int):
    kb_list = [
        [KeyboardButton(text="📖 О нас"), KeyboardButton(text="💸 Прайс-лист")],
        [KeyboardButton(text="📝 Отзывы клиентов")],
        [KeyboardButton(text="💇‍♀️ Записаться к мастеру")],
        [KeyboardButton(text='📋 Мои записи')]
    ]
    if user_telegram_id in db_connector.admins_cache:
        kb_list = [
            [KeyboardButton(text="Записать клиента к мастеру")],
            [KeyboardButton(text="Сотрудники"), KeyboardButton(text="Услуги")],
            [KeyboardButton(text="Публикация отзывов")],
            [KeyboardButton(text="Открыть меню пользователей")]
        ]
    keyboard = ReplyKeyboardMarkup(
        keyboard=kb_list,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Воспользуйтесь меню:"
    )
    return keyboard

def employee_kb(user_telegram_id: int):
    kb_list = [
        [KeyboardButton(text="📖 О нас"), KeyboardButton(text="💸 Прайс-лист")],
        [KeyboardButton(text="📝 Отзывы клиентов")],
        [KeyboardButton(text="💇‍♀️ Записаться к мастеру")],
        [KeyboardButton(text='📋 Мои записи')]
    ]
    if user_telegram_id in db_connector.employee_cache:
        kb_list = [
            [KeyboardButton(text="Записи на сегодня")],
            [KeyboardButton(text="График работы")],
            [KeyboardButton(text="Добавить выходной/рабочий день")],
            [KeyboardButton(text="Просмотр записей")],
            [KeyboardButton(text="Открыть меню пользователей")]
        ]
    keyboard = ReplyKeyboardMarkup(
        keyboard=kb_list,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Воспользуйтесь меню:"
    )
    return keyboard


def review_kb():
    kb_list = [
        [KeyboardButton(text="📝 Оставить отзыв")],
        [KeyboardButton(text="💬 Отзывы наших клиентов")],
        [KeyboardButton(text="📁 Мои отзывы")],
        [KeyboardButton(text="📖 Назад в главное меню")]
    ]
    keyboard = ReplyKeyboardMarkup(
        keyboard=kb_list,
        resize_keyboard=True,
        one_time_keyboard=False    
    )
    return keyboard

def back_kb():
    kb_list = [[KeyboardButton(text="⬅️ Назад")]]
    keyboard = ReplyKeyboardMarkup(
        keyboard=kb_list,
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    return keyboard


