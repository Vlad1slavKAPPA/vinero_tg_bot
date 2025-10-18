from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from keyboards.all_kb import main_kb
from create_bot import db_connector,bot
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from messaging_exception.messaging import send_long_message

# Состояния: имя и телефон
class Form(StatesGroup):
    name = State()
    phone = State()
    gender = State()
    url_tg = State()

start_router = Router()

user_name = None


@start_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    query = "SELECT id, name FROM users WHERE id = :id"
    params = {"id": message.from_user.id}

    try:
        result = await db_connector.execute_query(query, params)
        rows = result.fetchall()

        if not rows:
            # Очистить старое состояние, если пользователь не найден в БД
            await state.clear()
            await message.answer("Вы у нас впервые! Как к вам можно обращаться?")
            await state.set_state(Form.name)
        else:
            user_name = rows[0].name
            await message.answer(
                f"Здравствуйте, {user_name.capitalize()}!\n"
                "Вас приветствует студия красоты Barbero!\n"
                "Что желаете сделать?",
                reply_markup=main_kb(message.from_user.id),
                parse_mode=ParseMode.HTML
            )

    except Exception as e:
        await message.answer("❌ Произошла ошибка на сервере. Попробуйте позже.")
        await send_long_message(f"Excpetion start.py 51 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        print(f"Ошибка при работе с БД: {e}")


@start_router.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.update_data(url_tg=message.from_user.full_name)
    await state.set_state(Form.gender)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👨 Мужской", callback_data="gender_male"),
            InlineKeyboardButton(text="👩 Женский", callback_data="gender_female"),
        ]
    ])

    await message.answer("Пожалуйста, укажите ваш пол:", reply_markup=keyboard)

    
@start_router.callback_query(F.data.startswith("gender_"))
async def process_gender_callback(callback: types.CallbackQuery, state: FSMContext):
    gender = 2 if callback.data == "gender_male" else 3  # 2 — мужской, 3 — женский
    await state.update_data(gender=gender)
    await state.set_state(Form.phone)

    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📱 Отправить номер", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await callback.message.answer("Пожалуйста, отправьте свой номер телефона нажав на кнопку снизу:", reply_markup=keyboard)
    await callback.answer()


@start_router.message(Form.phone, lambda msg: msg.contact is not None)
async def process_phone_button(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await save_user_and_finish(message, state)


@start_router.message(Form.phone)
async def process_phone_manual(message: Message, state: FSMContext):
    phone = message.text.strip()
    if phone.startswith("+") and phone[1:].isdigit() and 10 <= len(phone) <= 15:
        await state.update_data(phone=phone)
        await save_user_and_finish(message, state)
    else:
        await message.answer("❗ Введите корректный номер телефона. Пример: +79528125252")


async def save_user_and_finish(message: Message, state: FSMContext):
    user_data = await state.get_data()
    await state.clear()

    # Ответ пользователю
    await message.answer(
        f"✅ Спасибо, {user_data['name'].capitalize()}!\n"
        f"📞 Ваш номер телефона: {user_data['phone']}\n"
        "Ваши данные сохранены.",
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML
    )
    phone_clean = user_data['phone'].lstrip('+')  # убираем плюс в начале
    # Запрос в БД
    query = "INSERT INTO users (id, name, phone, gender) VALUES (:id, :name, :phone, :gender)"
    params = {
        "id": message.from_user.id,
        "name": user_data['name'],
        "phone": phone_clean,
        "gender": user_data['gender'],
    }

    await message.answer(
                f"Здравствуйте, {user_data['name']}!\n"
                "Вас приветствует студия красоты Barbero!\n"
                "Что желаете сделать?",
                reply_markup=main_kb(message.from_user.id),
                parse_mode=ParseMode.HTML
            )
    try:
        await db_connector.execute_query(query, params)
    except Exception as e:
        print(f"❌ Ошибка при сохранении в БД: {e}")
        await message.answer("⚠️ Ошибка при сохранении данных. Попробуйте позже.")
        await send_long_message(f"Excpetion start.py 139 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 