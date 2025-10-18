from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta, time
from create_bot import db_connector, bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from messaging_exception.messaging import send_long_message
from aiogram.exceptions import DetailedAiogramError
import random
import re

client_record_router = Router()


class BookingFSM(StatesGroup):
    collecting_name = State()
    collecting_phone = State()
    collecting_gender = State()
    client_id = State()
    user_gender = State()

    collecting_gender_emp = State()


    choosing_master = State()
    choosing_date = State()
    choosing_time = State()
    choosing_gender = State()
    choosing_services = State()
    confirming = State()

    count_add_services = State()

async def safe_execute(query: str, params: dict | None = None):
    try:
        return await db_connector.execute_query(query, params or {})
    except Exception as e:
        await send_long_message(f"Ошибка SQL client_record.py {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return None


@client_record_router.message(F.text == 'Записать клиента к мастеру')
async def ask_client_name(message: Message, state: FSMContext):
    await message.answer("Введите номер телефона клиента. Пример: +79001234567.")
    await state.set_state(BookingFSM.collecting_phone)
    
@client_record_router.message(BookingFSM.collecting_phone)
async def get_client_phone(message: Message, state: FSMContext):
    try:
        phone = message.text.strip()
        if len(phone) > 12 and len(phone) < 10:
            await message.answer("❌ Произошла ошибка! Номер телефона некорректный. Попробуйте еще раз. Пример: +79002009090.")
        elif phone.startswith("+"):
            phone = phone[1:]
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 58 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    # Проверяем, существует ли пользователь
    try:
        query = "SELECT id, gender FROM users WHERE phone = :phone"
        result = await safe_execute(query, {"phone": phone})
        existing_user = result.mappings().fetchone()
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 67 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    if existing_user:
        try:
            user_id = existing_user["id"]
            gender = existing_user["gender"]
            await state.update_data(client_id=user_id)
            await state.update_data(user_gender=gender)
            await message.answer("✅ Пользователь найден!")
            await start_booking(message, state)
        except Exception as e:
            await send_long_message(f"Exception client_record.py ( line - 79 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
    else:
        try:
            await state.update_data(collecting_phone=phone)
            await message.answer("Введите имя клиента:")
            await state.set_state(BookingFSM.collecting_name)
        except Exception as e:
            await send_long_message(f"Exception client_record.py ( line - 86 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
    
@client_record_router.message(BookingFSM.collecting_name)
async def get_client_name(message: Message, state: FSMContext):
    await state.update_data(collecting_name=message.text.strip())
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♂ Мужской", callback_data=f"reg_gender_{2}")],
        [InlineKeyboardButton(text="♀ Женский", callback_data=f"reg_gender_{3}")],
    ])
    await message.answer("Выберите пол клиента:", reply_markup=keyboard)


@client_record_router.message(BookingFSM.collecting_gender_emp)
async def get_client_gender(message: Message, state: FSMContext):
    try:
        query = "SELECT name FROM employees WHERE user_id = :id"
        response = await safe_execute(query, {"id": message.from_user.id})
        name = response.fetchone()
    except DetailedAiogramError as e:
        await message.answer(text="❌ Произошла ошибка при запросе данных из БД!")
        await send_long_message(f"Excpetion client_record.py ( line - 107 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♂ Мужской", callback_data=f"fast_reg_gender_{2}")],
        [InlineKeyboardButton(text="♀ Женский", callback_data=f"fast_reg_gender_{3}")],
    ])
    await message.answer("Выберите пол клиента:", reply_markup=keyboard)

@client_record_router.callback_query(F.data.startswith("fast_reg_gender_"))
async def gender_selected(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split("_")
    gender = int(parts[3])
    await state.update_data(user_gender=gender)
    await start_booking(callback.message, state)
    print("Старт записи после выбранного пола у сотрудника")
    

@client_record_router.callback_query(F.data.startswith("reg_gender_"))
async def gender_selected(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 129 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        parts = callback.data.split("_")
        gender = int(parts[2])
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 136 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        await state.update_data(user_gender=gender)
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 142 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")

    try:
        # Генерируем случайный ID
        user_id = random.randint(10**7, 10**9)
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 148 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    insert_query = """
    INSERT INTO users (id, name, phone, gender)
    VALUES (:id, :name, :phone, :gender)
    """
    try:
        data = await state.get_data()
        await safe_execute(insert_query, {
            "id": user_id,
            "name": data.get("collecting_name"),
            "phone": data.get("collecting_phone"),
            "gender": gender
        })
        await state.update_data(client_id=user_id)
        await start_booking(callback.message, state)
    except Exception as e:
        try:
            await callback.message.answer("❌ Произошла ошибка при сохранении данных в БД!")
        except Exception:
            await send_long_message(f"Exception client_record.py ( line - 169 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
            pass
            

# Начало записи

@client_record_router.message(F.text == '💇‍♀️ Записаться к мастеру')
async def handler_booking(message: Message | CallbackQuery, state: FSMContext):
    if message.from_user.id in db_connector.employee_cache:
        return await get_client_gender(message, state)
    else:
        await start_booking(message, state)


async def start_booking(message: Message | CallbackQuery, state: FSMContext):
    try:
        if isinstance(message, CallbackQuery):
            send_fn = message.message.edit_text
        else:
            send_fn = message.answer
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 188 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        query = "SELECT e.id, e.name, r.name FROM employees e JOIN roles r ON r.id = e.role_id"
        result = await safe_execute(query)
        masters = result.fetchall()
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 196 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        builder = InlineKeyboardBuilder()
        for master in masters:
            builder.button(text=f"{master[2]} {master[1]}", callback_data=f"master_{master[0]}")
        builder.adjust(1)
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 205 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        await send_fn("Выберите мастера:", reply_markup=builder.as_markup())
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 211 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        await state.set_state(BookingFSM.choosing_master)
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 217 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
    


@client_record_router.callback_query(BookingFSM.choosing_master, lambda c: c.data.startswith("master_"))
async def master_chosen(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 226 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        master_id = int(callback.data.split("_")[1])
        await state.update_data(master_id=master_id)
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 233 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        data = await state.get_data() 
        user_id = data.get("client_id", callback.from_user.id)
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 240 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        if not callback.from_user.id in db_connector.employee_cache:
            result = await safe_execute(
                "SELECT gender FROM users WHERE id = :id",
                {"id": user_id}
            )
            row = result.fetchone()
            gender = data.get("user_gender", row.gender if row else 1)  # по умолчанию 1 (универсально)
            await state.update_data(user_gender=gender)
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 253 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        await state.update_data(selected_services=[], total_duration=0, total_price=0)
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 259 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        await show_services(callback, state)
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 265 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")


@client_record_router.callback_query(BookingFSM.choosing_date, lambda c: c.data.startswith("date_"))
async def date_chosen(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 273 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        date_str = callback.data.split("_")[1]
        chosen_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 280 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        data = await state.get_data()
        master_id = data.get("master_id")
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 287 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        query = "SELECT start_time, end_time FROM employees WHERE id = :id"
        result = await safe_execute(query, {"id": master_id})
        times = result.fetchone()
        start_time, end_time = times.start_time, times.end_time
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 296 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        query = "SELECT time as start_time, total_duration FROM orders WHERE employee_id = :mid AND date = :date"
        params = {"mid": master_id, "date": chosen_date}
        result = await safe_execute(query, params)
        rows = result.fetchall()
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 305 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        bookings = [{"start_time": row.start_time, "duration": row.total_duration} for row in rows]
        required_duration = data.get("total_duration")
        slots = calculate_free_slots(chosen_date, start_time, end_time, bookings, required_duration)
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 313 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        if not slots:
            await callback.answer("Нет свободного времени на выбранную дату. Попробуйте другую.")
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 320 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        builder = InlineKeyboardBuilder()
        for slot in slots:
            builder.button(text=slot.strftime("%H:%M"), callback_data=f"time_{slot.strftime('%H:%M')}")
        builder.adjust(3)
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 329 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        await state.update_data(chosen_date=str(chosen_date))
        await callback.message.edit_text("Выберите удобное время:", reply_markup=builder.as_markup())
        await state.set_state(BookingFSM.choosing_time)
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 337 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")


@client_record_router.callback_query(BookingFSM.choosing_time, lambda c: c.data.startswith("time_"))
async def time_chosen(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 345 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        await callback.answer()
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 351 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        time_str = callback.data.split("_")[1]
        await state.update_data(chosen_time=time_str)
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 358 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        await show_summary(callback, state)
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 364 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")


HAIRCUT_RE = re.compile(r'стриж', re.I)      # поймает "стрижка", "стрижки" и т.д.
MODEL_RE   = re.compile(r'модел', re.I)      # "модель", "модельная" и т.п.
MALE_RE    = re.compile(r'муж', re.I)       # для определения пола по названию (опционально)
FEMALE_RE  = re.compile(r'жен', re.I)

def build_service_tree(services):
    """
    Строим дерево категорий на основе имени услуги (разделитель "_").
    """
    tree = {}
    for s in services:
        parts = s.name.split("_")
        node = tree
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                # последний уровень = сама услуга
                node[part] = s
            else:
                node = node.setdefault(part, {})
    return tree


async def show_services(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 393 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        data = await state.get_data()
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 399 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        gender = data.get("user_gender")
        selected_services = data.get("selected_services", [])
        path = data.get("service_path", [])
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 407 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    # 1) Получаем все услуги по полу
    try:
        query = "SELECT id, name, price, duration, sex FROM services WHERE sex IN (:gender, 1)"
        result = await safe_execute(query, {"gender": gender})
        services = result.fetchall()
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 416 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    # 2) Фильтруем услуги
    filtered_services = []
    for s in services:
        if s.id not in selected_services:
            filtered_services.append(s)

    # --- Динамическое меню ---
    try:
        builder = InlineKeyboardBuilder()
        builder.adjust(1)
        tree = build_service_tree(filtered_services + [s for s in services if s.id in selected_services])

        node = tree
        for p in path:
            node = node.get(p, {})

        categories = []
        services_list = []

        for key, val in node.items():
            if isinstance(val, dict):
                categories.append(key)
            else:
                services_list.append(val)

        # Категории
        for cat in sorted(categories, key=lambda x: x.lower()): 
            builder.button(text=cat.capitalize(), callback_data=f"cat_{cat}")
        builder.adjust(1)

        # Услуги
        for s in sorted(services_list, key=lambda x: x.price):
            clean_name = s.name.split("_")[-1].capitalize()
            h, m = divmod(s.duration, 60)
            duration = f"{f'{h} ч ' if h else ''}{m} мин" if m or h == 0 else f"{h} ч"
            checkmark = "✅ " if s.id in selected_services else ""
            builder.button(
                text=f"{checkmark}{clean_name} ({s.price}₽ ~ {duration})",
                callback_data=f"service_{s.id}"
            )

        if path: 
            builder.button(text="⬅ Назад", callback_data="back_cat") 
        if selected_services: 
            builder.button(text="✅ Готово", callback_data="services_done") 
        builder.adjust(1)
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 507 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        await callback.message.edit_text("Выберите услугу:", reply_markup=builder.as_markup())
    except DetailedAiogramError:
        try:
            await callback.message.answer("Выберите услугу:", reply_markup=builder.as_markup())
        except Exception as e:
            await send_long_message(f"Exception client_record.py ( line - 516 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")

    try:
        await state.set_state(BookingFSM.choosing_services)
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 521 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
    



@client_record_router.callback_query(BookingFSM.choosing_services)
async def choose_services(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        selected_services = data.get("selected_services", [])
        total_duration = data.get("total_duration", 0)
        total_price = data.get("total_price", 0)
        path = data.get("service_path", [])
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 534 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        if callback.data == "back_cat":
            if path:
                path.pop()
            await state.update_data(service_path=path)
            return await show_services(callback, state)

        if callback.data.startswith("cat_"):
            category = callback.data.split("_", 1)[1]
            path.append(category)
            await state.update_data(service_path=path)
            return await show_services(callback, state)

        if callback.data.startswith("service_"):
            service_id = int(callback.data.split("_")[1])

            # Получаем параметры услуги
            query = "SELECT name, duration, price FROM services WHERE id = :id"
            result = await safe_execute(query, {"id": service_id})
            service = result.fetchone()
            if not service:
                await callback.answer("Услуга не найдена.", show_alert=True)
                return

            # Toggle выбора услуги
            if service_id in selected_services:
                selected_services.remove(service_id)
                total_duration -= service.duration
                total_price -= service.price
            else:
                selected_services.append(service_id)
                total_duration += service.duration
                total_price += service.price

            await state.update_data(
                selected_services=selected_services,
                total_duration=total_duration,
                total_price=total_price
            )

            # Обновляем меню, чтобы показать галочки
            return await show_services(callback, state)

        if callback.data == "services_done":
            # Пользователь закончил выбор услуг → показываем свободные даты
            # Используем старую логику показа доступных дат и времени
            data = await state.get_data()
            master_id = data.get("master_id")
            today = datetime.today().date()
            days_range = [today + timedelta(days=i) for i in range(8)]

            # Выходные по расписанию
            result = await safe_execute(
                "SELECT weekday FROM employees_week_offday WHERE employee_id = :id",
                {"id": master_id}
            )
            regular_days_off = {row.weekday for row in result.fetchall()}

            # Исключения
            result = await safe_execute(
                "SELECT exception_date, is_working FROM employees_exceptions WHERE employee_id = :id",
                {"id": master_id}
            )
            rows = result.mappings().all()
            exception_map = {row["exception_date"]: row["is_working"] for row in rows}

            # Время работы мастера
            result = await safe_execute(
                "SELECT start_time, end_time FROM employees WHERE id = :id",
                {"id": master_id}
            )
            work_times = result.fetchone()
            start_time, end_time = work_times.start_time, work_times.end_time

            required_duration = data.get("total_duration")

            available_dates = []
            for date in days_range:
                weekday = date.weekday()
                is_available = False
                if date in exception_map:
                    is_available = exception_map[date]
                elif weekday not in regular_days_off:
                    is_available = True

                if not is_available:
                    continue

                query = "SELECT time as start_time, total_duration FROM orders WHERE employee_id = :mid AND date = :date"
                params = {"mid": master_id, "date": date}
                result = await safe_execute(query, params)
                rows = result.fetchall()
                bookings = [{"start_time": row.start_time, "duration": row.total_duration} for row in rows]

                slots = calculate_free_slots(date, start_time, end_time, bookings, required_duration)
                if slots:
                    available_dates.append(date)

            if not available_dates:
                await callback.message.edit_text("❌ Нет свободных дат для записи.")
                await callback.answer()
                return

            builder = InlineKeyboardBuilder()
            for date in available_dates:
                builder.button(text=date.strftime("%d.%m.%Y"), callback_data=f"date_{date}")
            builder.adjust(1)

            await callback.message.edit_text("Выберите удобную дату:", reply_markup=builder.as_markup())
            await callback.answer()
            await state.set_state(BookingFSM.choosing_date)
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 667 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")



async def show_summary(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()

    service_ids = data.get("selected_services", [])
    master_id = data["master_id"]
    chosen_date = data["chosen_date"]
    chosen_time = data["chosen_time"]
    duration = data["total_duration"]
    h, m = divmod(duration, 60)
    duration_str = f"{f'{h} ч ' if h else ''}{m} мин" if m or h == 0 else f"{h} ч"
    total_price = data["total_price"]

    # Получаем имя мастера
    result = await safe_execute("SELECT name FROM employees WHERE id = :id", {"id": master_id})
    master_name = result.fetchone().name

    # Получаем названия услуг
    placeholders = ','.join([str(sid) for sid in service_ids])
    query = f"SELECT name FROM services WHERE id IN ({placeholders})"
    result = await safe_execute(query)
    service_names = [row.name for row in result.fetchall()]

    # Кнопки
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить услугу", callback_data="add_service")
    builder.button(text="✅ Подтвердить", callback_data="confirm_booking")
    builder.button(text="❌ Отменить", callback_data="cancel_booking")
    builder.adjust(1)

    # Формируем текст сообщения
    text = (
        f"Проверьте данные записи:\n\n"
        f"📅 Дата: {datetime.fromisoformat(chosen_date).strftime('%d.%m.%Y')}\n"
        f"🕒 Время: {chosen_time}\n\n"
        f"💇‍♂️ Мастер: {master_name}\n\n"
        f"📋 Услуги:\n" +
        "\n".join(f"• {name.replace('_', ', ').title()}" for name in service_names) + "\n\n"
        f"⏱ Общая длительность: {duration_str}\n"
        f"💰 Общая стоимость: {total_price}₽\n\n"
        f"Что вы хотите сделать?"
    )

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await state.set_state(BookingFSM.confirming)


@client_record_router.callback_query(BookingFSM.confirming)
async def finalize_booking(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
    except Exception as e:
        await send_long_message(f"Exception client_record.py ( line - 722 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    if callback.data == "add_service":
        try:
            await state.update_data(service_path=[])
            await state.update_data(count_add_services=1)
            await show_services(callback, state)
        except Exception as e:
            await send_long_message(f"Exception client_record.py ( line - 731 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    if callback.data == "confirm_booking":
        try:
            master_id = data["master_id"]
            chosen_date_str = data["chosen_date"]
            chosen_time_str = data["chosen_time"]
            service_ids = data["selected_services"]
            total_duration = data["total_duration"]
            total_price = data["total_price"]

            # Преобразуем время и дату
            chosen_time = datetime.strptime(chosen_time_str, "%H:%M").time()
            chosen_date = datetime.strptime(chosen_date_str, "%Y-%m-%d").date()

            client_id = data.get("client_id", callback.from_user.id)

            # Вставка записи в orders
            insert_order_query = """
            INSERT INTO orders (employee_id, user_id, date, time, total_duration, total_price)
            VALUES (:employee_id, :user_id, :date, :time, :total_duration, :total_price)
            RETURNING orders_id
            """
            result = await safe_execute(insert_order_query, {
                "employee_id": master_id,
                "user_id": client_id,
                "date": chosen_date,
                "time": chosen_time,
                "total_duration": total_duration,
                "total_price": total_price
            })
            order_id = result.fetchone().orders_id

            # Вставка в orders_has_services
            insert_services_query = """
            INSERT INTO orders_has_services (order_id, services_id)
            VALUES (:order_id, :services_id)
            """
            for sid in service_ids:
                await safe_execute(insert_services_query, {"order_id": order_id, "services_id": sid})

            await callback.message.edit_text("✅ Вы успешно записаны!")
            await state.clear()
        except Exception as e:
            await send_long_message(f"Exception client_record.py ( line - 776 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return
    else:
        try:
            await callback.message.edit_text("❌ Запись отменена.")
            await state.clear()
        except Exception as e:
            await send_long_message(f"Exception client_record.py ( line - 782 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        

from zoneinfo import ZoneInfo

MSK = ZoneInfo("Europe/Moscow")

def calculate_free_slots(date, work_start: time, work_end: time, bookings, required_duration: int):
    """
    Возвращает список свободных слотов на выбранную дату.
    
    date: datetime.date — выбранная дата
    work_start, work_end: datetime.time — рабочий день мастера
    bookings: list[dict] — [{"start_time": time, "duration": int}]
    required_duration: int — длительность услуги в минутах
    """
    slot_interval = timedelta(minutes=15)
    slots = []

    # Текущее время в MSK
    now = datetime.now(MSK)

    # Начало и конец рабочего дня в MSK
    current = datetime.combine(date, work_start, tzinfo=MSK)
    work_end_dt = datetime.combine(date, work_end, tzinfo=MSK)

    # Конвертируем бронирования в интервалы datetime с MSK
    intervals = []
    for booking in bookings:
        start = datetime.combine(date, booking['start_time'], tzinfo=MSK)
        end = start + timedelta(minutes=booking['duration'])
        intervals.append((start, end))

    intervals.sort()

    # Проверка, свободен ли слот
    def is_free(start_time: datetime):
        end_time = start_time + timedelta(minutes=required_duration)
        if end_time > work_end_dt:
            return False
        for booked_start, booked_end in intervals:
            if booked_start < end_time and start_time < booked_end:
                return False
        return True

    # Если дата сегодня, округляем now вверх до ближайшего 15-минутного интервала
    if date == now.date():
        minutes = (now.minute // 15 + 1) * 15
        now = now.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=minutes)
        if now > work_end_dt:
            now = work_end_dt

    # Генерация слотов
    while current <= work_end_dt - timedelta(minutes=required_duration):
        # Пропускаем все слоты в прошлом
        if date == now.date() and current < now:
            current += slot_interval
            continue

        if is_free(current):
            slots.append(current.time())

        current += slot_interval

    return slots
