from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date, datetime, timedelta
from create_bot import db_connector, bot
from keyboards.all_kb import main_kb, employee_kb
from aiogram.exceptions import TelegramBadRequest
from messaging_exception.messaging import send_long_message

emp_router = Router()


@emp_router.message(F.text == "⚙️ Кабинет-сотрудника")
async def show_user_kb(message: Message):
    await message.answer("Здравствуйте!\n", reply_markup=employee_kb(message.from_user.id))

@emp_router.message(F.text == "Открыть меню пользователей")
async def go_users_menu(message: Message):
    await message.answer(
                f"Здравствуйте!\n"
                "Вас приветствует студия красоты Barbero!\n"
                "Что желаете сделать?",
                reply_markup=main_kb(message.from_user.id))
    

@emp_router.message(F.text == "Записи на сегодня")
async def startshow_orders_today(message: Message):
    msg = await show_orders_today(message.from_user.id, datetime.today())
    try:
        await bot.send_message(message.from_user.id, msg)
    except TelegramBadRequest as e:
        await send_long_message(f"Excpetion employee_panel.py 34 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        print(f"Ошибка при отправке сотруднику (user_id: {message.from_user.id}): {e}")

    


async def show_orders_today(user_id: int, dates = None):
    if date is None:
        msg = "❌ Ошибка при запросе данных из БД!"
        print("При вызове show_orders_today не передана дата!")
        return msg
    else:
        today = dates
    request = await db_connector.execute_query("SELECT id FROM employees WHERE user_id = :id",{"id": user_id})
    row_emp = request.fetchone()
    emp = {"id": row_emp.id if row_emp else None, "user_id": user_id}
    result = await db_connector.execute_query("""
            SELECT 
                o.orders_id,
                o.total_duration,
                o.total_price,
                u.name AS client_name,
                u.phone,
                u.id,
                o.time,
                s.name AS service_name
            FROM orders o
            JOIN users u ON u.id = o.user_id
            JOIN orders_has_services ohs ON o.orders_id = ohs.order_id
            JOIN services s ON s.id = ohs.services_id
            WHERE o.employee_id = :eid AND o.date = :today
            ORDER BY o.time;
        """, {"eid": emp["id"], "today": today})

    rows = result.mappings().all()
    if not rows:
        msg = f"Сегодня ({today.strftime('%d.%m.%Y')}) клиентов нет."
        return msg

    # --- группировка заказов ---
    orders_map = {}
    for row in rows:
        oid = row["orders_id"]
        if oid not in orders_map:
            orders_map[oid] = {
                "time": row["time"],
                "client_name": row["client_name"],
                "user_id": row["id"],
                "phone": row["phone"],
                "total_duration": row["total_duration"],
                "total_price": row["total_price"],
                "services": []
            }
        orders_map[oid]["services"].append(row["service_name"])

    # теперь сообщение собираем один раз
    orders = list(orders_map.values())
    lines = [f"Клиенты на {today.strftime('%d.%m.%Y')}:"]

    count = 1
    for o in orders:
        services_text = o['services']
        h, m = divmod(o['total_duration'], 60)
        duration = f"{f'{h} ч ' if h else ''}{m} мин" if m or h == 0 else f"{h} ч"
        time_str = o['time'].strftime("%H:%M")
        lines.append(
            f"\n\n{count}. ⏰ Время: {time_str}\n"
            f"    📋 Услуги:\n" + "\n".join(
            f"      • {name.replace('_', ', ').title()}" 
                    for name in services_text) + "\n\n"
            f"    ⏱ Общая длительность: {duration}\n"
            f"    💰 Стоимость усуг: {o['total_price']}₽\n\n"
            f"    💇‍♂️ Имя: {o['client_name'].capitalize()}\n"
            f"    📞 Телефон: +{o['phone']}\n"
            f"    🔗 <a href='tg://user?id={o['user_id']}'>Перейти к пользователю</a>\n\n" 
        )
        count += 1

    msg = "\n".join(lines)

    return msg

DAYS_OF_WEEK = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
DAY_EMOJI = {True: "❌", False: "✅"}  # выходной/рабочий

# ------------------------ Функция формирования текста и клавиатуры ------------------------
async def build_schedule_message(emp_id: int, editing: bool = False):
    # Получаем данные сотрудника
    res = await db_connector.execute_query(
        "SELECT name FROM employees WHERE id = :eid",
        {"eid": emp_id}
    )
    row = res.fetchone()
    if not row:
        return "❌ Сотрудник не найден.", None

    emp_name = row.name

    # Получаем дни отдыха
    res = await db_connector.execute_query(
        "SELECT weekday FROM employees_week_offday WHERE employee_id = :eid",
        {"eid": emp_id}
    )
    days_off = [r.weekday for r in res.fetchall()]

    # Формируем текст графика
    text = f"📅 График рабочих дней для <b>{emp_name}</b>:\n\n"
    for i, day in enumerate(DAYS_OF_WEEK):
        is_off = i in days_off
        text += f"{DAY_EMOJI[is_off]} {day}\n"

    # Формируем клавиатуру
    builder = InlineKeyboardBuilder()
    if editing:
        # Кнопки для переключения дней
        for i, day in enumerate(DAYS_OF_WEEK):
            is_off = i in days_off
            builder.button(
                text=f"{DAY_EMOJI[is_off]} {day}",
                callback_data=f"toggle_day_{emp_id}_{i}"
            )
        builder.adjust(4)
        builder.button(text="⬅️ Назад к просмотру", callback_data=f"back_schedule_{emp_id}", row=5)
    else:
        # Кнопка для редактирования
        builder.button(text="✏️ Редактировать график", callback_data=f"edit_schedule_{emp_id}")

    return text, builder


# ------------------------ Просмотр графика ------------------------
@emp_router.message(F.text == "График работы")
async def show_week_schedule(message: Message):
    # Получаем сотрудника
    res = await db_connector.execute_query(
        "SELECT id FROM employees WHERE user_id = :uid",
        {"uid": message.from_user.id}
    )
    row_emp = res.fetchone()
    if not row_emp:
        return await message.answer("❌ Сотрудник не найден.")

    emp_id = row_emp.id
    text, builder = await build_schedule_message(emp_id)
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


# ------------------------ Редактирование графика ------------------------
@emp_router.callback_query(F.data.startswith("edit_schedule_"))
async def edit_week_schedule(callback: CallbackQuery):
    await callback.answer()
    emp_id = int(callback.data.split("_")[-1])
    text, builder = await build_schedule_message(emp_id, editing=True)
    await callback.message.edit_text(
        "✏️ Редактирование графика. Нажмите на день, чтобы переключить рабочий/выходной:",
        reply_markup=builder.as_markup()
    )

# ------------------------ Переключение дня ------------------------
@emp_router.callback_query(F.data.startswith("toggle_day_"))
async def toggle_day(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    emp_id = int(parts[-2])
    weekday = int(parts[-1])

    # Переключаем день в базе
    res = await db_connector.execute_query(
        "SELECT employee_id FROM employees_week_offday WHERE employee_id = :eid AND weekday = :day",
        {"eid": emp_id, "day": weekday}
    )
    existing = res.fetchone()

    if existing:
        await db_connector.execute_query(
            "DELETE FROM employees_week_offday WHERE employee_id = :eid AND weekday = :day",
            {"eid": emp_id, "day": weekday}
        )
    else:
        await db_connector.execute_query(
            "INSERT INTO employees_week_offday (employee_id, weekday) VALUES (:eid, :day)",
            {"eid": emp_id, "day": weekday}
        )

    # Получаем свежие данные после изменения
    res = await db_connector.execute_query(
        "SELECT weekday FROM employees_week_offday WHERE employee_id = :eid",
        {"eid": emp_id}
    )
    days_off = [r.weekday for r in res.fetchall()]

    # Создаем клавиатуру с кнопками для всех дней недели
    builder = InlineKeyboardBuilder()
    for i, day in enumerate(DAYS_OF_WEEK):
        is_off = i in days_off
        builder.button(
            text=f"{DAY_EMOJI[is_off]} {day}",
            callback_data=f"toggle_day_{emp_id}_{i}"
        )
    builder.adjust(4)
    builder.button(text="⬅️ Назад к просмотру", callback_data=f"back_schedule_{emp_id}", row=5)

    await callback.message.edit_text(
        "✏️ Редактирование графика. Нажмите на день, чтобы переключить рабочий/выходной:",
        reply_markup=builder.as_markup()
    )

# ------------------------ Кнопка назад к просмотру ------------------------
@emp_router.callback_query(F.data.startswith("back_schedule_"))
async def back_to_schedule(callback: CallbackQuery):
    await callback.answer()
    emp_id = int(callback.data.split("_")[-1])
    text, builder = await build_schedule_message(emp_id)
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


    # FSM для добавления исключения
class ExceptionSchedule(StatesGroup):
    waiting_for_date = State()
    waiting_for_type = State()

# Дни для кнопок (даты)
def generate_date_buttons():
    builder = InlineKeyboardBuilder()
    today = datetime.today().date()
    start_date = today + timedelta(weeks=2)
    end_date = today + timedelta(weeks=4)

    current = start_date
    while current <= end_date:
        builder.button(
            text=current.strftime("%d.%m.%Y"),
            callback_data=f"exception_date_{current.strftime('%Y-%m-%d')}"
        )
        current += timedelta(days=1)

    builder.adjust(3)  # 3 кнопки в ряду
    return builder

# Хендлер для начала добавления исключения
@emp_router.message(F.text == "Добавить выходной/рабочий день")
async def start_add_exception(message: Message, state: FSMContext):
    await state.clear()
    # Получаем emp_id как обычно
    request = await db_connector.execute_query(
        "SELECT id FROM employees WHERE user_id = :uid",
        {"uid": message.from_user.id}
    )
    row_emp = request.fetchone()
    if not row_emp:
        return await message.answer("❌ Сотрудник не найден.")
    emp_id = row_emp.id

    # Сохраняем emp_id в состояние
    await state.update_data(emp_id=emp_id)
    builder = generate_date_buttons()
    await message.answer("Выберите дату:", reply_markup=builder.as_markup())
    await state.set_state(ExceptionSchedule.waiting_for_date)

# Выбор даты из кнопок
@emp_router.callback_query(F.data.startswith("exception_date_"))
async def select_exception_date(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    # Получаем выбранную дату
    date_str = callback.data.replace("exception_date_", "")
    exception_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    await state.update_data(exception_date=exception_date)

    # Получаем emp_id из состояния
    data = await state.get_data()
    emp_id = data.get("emp_id")
    if not emp_id:
        return await callback.message.answer("❌ Ошибка: не найден сотрудник в состоянии.")

    # Определяем день недели (0=Пн, 6=Вс)
    weekday = exception_date.weekday()

    # Получаем стандартные выходные дни сотрудника
    result = await db_connector.execute_query(
        "SELECT weekday FROM employees_week_offday WHERE employee_id = :eid",
        {"eid": emp_id}
    )
    days_off = [row.weekday for row in result.fetchall()]

    # Кнопки для типа дня
    builder = InlineKeyboardBuilder()
    if weekday in days_off:
        # день по графику выходной → можем сделать рабочим
        builder.button(text="💈 Сделать рабочим", callback_data="exception_working")
    else:
        # день по графику рабочий → можем сделать выходным
        builder.button(text="🏝️ Сделать выходным", callback_data="exception_day_off")

    # Кнопка назад к выбору даты
    builder.button(text="⬅️ Назад к датам", callback_data="back_to_dates")

    builder.adjust(1)  # 1 кнопка в ряду
    await state.set_state(ExceptionSchedule.waiting_for_type)
    await callback.message.edit_text(
        f"📅 Выбрана дата: {exception_date}\nВыберите действие:",
        reply_markup=builder.as_markup()
    )

# Выбор типа дня
@emp_router.callback_query(F.data.startswith("exception_"))
async def select_exception_type(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    if not data.get("exception_date"):
        return await callback.message.answer("Ошибка: дата не выбрана. Попробуйте снова.")

    exception_date = data["exception_date"]
    is_working = callback.data == "exception_working"

    # Получаем сотрудника
    request = await db_connector.execute_query(
        "SELECT id FROM employees WHERE user_id = :uid",
        {"uid": callback.from_user.id}
    )
    row_emp = request.fetchone()
    if not row_emp:
        return await callback.message.answer("❌ Сотрудник не найден.")
    emp_id = row_emp.id

    # Проверяем, есть ли уже запись
    existing = await db_connector.execute_query(
        "SELECT employee_id FROM employees_exceptions WHERE employee_id = :eid AND exception_date = :date",
        {"eid": emp_id, "date": exception_date}
    )
    if existing.fetchone():
        # Обновляем запись
        await db_connector.execute_query(
            "UPDATE employees_exceptions SET is_working = :work WHERE employee_id = :eid AND exception_date = :date",
            {"work": is_working, "eid": emp_id, "date": exception_date}
        )
    else:
        # Вставляем новую
        await db_connector.execute_query(
            "INSERT INTO employees_exceptions (employee_id, exception_date, is_working) VALUES (:eid, :date, :work)",
            {"eid": emp_id, "date": exception_date, "work": is_working}
        )

    await callback.message.edit_text(
        f"✅ Исключение добавлено: {exception_date.strftime('%d.%m.%Y')} — {'Рабочий день' if is_working else 'Выходной день'}"
    )
    await state.clear()

@emp_router.callback_query(F.data == "back_to_dates")
async def back_to_date_selection(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    builder = generate_date_buttons()  # функция, которая создает кнопки с датами через 2-4 недели
    await callback.message.edit_text(
        "Выберите дату:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(ExceptionSchedule.waiting_for_date)


@emp_router.message(F.text == "Просмотр записей")
async def select_record_date(message: Message):
    # Получаем сотрудника
    request = await db_connector.execute_query(
        "SELECT id FROM employees WHERE user_id = :uid",
        {"uid": message.from_user.id}
    )
    row_emp = request.fetchone()
    if not row_emp:
        return await message.answer("❌ Сотрудник не найден.")
    emp_id = row_emp.id

    # Получаем дни отдыха по постоянному графику
    result = await db_connector.execute_query(
        "SELECT weekday FROM employees_week_offday WHERE employee_id = :eid",
        {"eid": emp_id}
    )
    days_off = [row.weekday for row in result.fetchall()]

    # Получаем исключения (рабочие/выходные дни)
    result = await db_connector.execute_query(
        "SELECT exception_date, is_working FROM employees_exceptions WHERE employee_id = :eid",
        {"eid": emp_id}
    )
    exceptions = {row.exception_date: row.is_working for row in result.fetchall()}

    # Диапазон дат: сегодня + 1 неделя
    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=8)

    builder = InlineKeyboardBuilder()
    current_date = start_date
    while current_date <= end_date:
        weekday = current_date.weekday()  # Пн=0, Вс=6
        is_working = True

        if current_date in exceptions:
            is_working = exceptions[current_date]  # учитываем исключение
        else:
            is_working = weekday not in days_off  # обычный график

        if is_working:  # показываем только рабочие дни
            builder.button(
                text=current_date.strftime("%d.%m.%Y"),
                callback_data=f"view_records_{current_date}"
            )
        current_date += timedelta(days=1)

    builder.adjust(4)  # 4 кнопки в ряду
    await message.answer("Выберите дату для просмотра записей:", reply_markup=builder.as_markup())


@emp_router.callback_query(F.data.startswith("view_records_"))
async def view_records(callback: CallbackQuery):
    await callback.answer()
    date_str = callback.data.replace("view_records_", "")
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    msg = await show_orders_today(callback.from_user.id, selected_date)
    await bot.send_message(callback.from_user.id, msg)

    


        