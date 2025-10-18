from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
from create_bot import db_connector
from handlers.client_record import calculate_free_slots
from messaging_exception.messaging import send_long_message
import re

edit_router = Router()

class EditBookingFSM(StatesGroup):
    choosing_date = State()
    choosing_time = State()
    choosing_services = State()
    confirming = State()


async def safe_execute(query: str, params: dict | None = None):
    try:
        return await db_connector.execute_query(query, params or {})
    except Exception as e:
        await send_long_message(f"Ошибка SQL edit_record.py {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return None

@edit_router.callback_query(F.data.startswith("edit_order_"))
async def start_edit(callback: CallbackQuery, state: FSMContext):
    await show_edit_summary(callback, state, show_conf_button = False)

@edit_router.callback_query(F.data.startswith("start_edit_order_"))
async def date_edit(callback: CallbackQuery, state: FSMContext):
    try:
        order_id = int(callback.data.split("_")[-1])
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 36 )  {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        order_data = await state.get_data()
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 42 )  {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    today = datetime.today().date()
    days_range = [today + timedelta(days=i) for i in range(14)]

    try:
        result = await safe_execute(
            "SELECT weekday FROM employees_week_offday WHERE employee_id = :id",
            {"id": order_data['master_id']}
        )
        regular_days_off = {row.weekday for row in result.fetchall()}
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 55 )  {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        regular_days_off = set()

    try:
        result = await safe_execute(
            "SELECT exception_date, is_working FROM employees_exceptions WHERE employee_id = :id",
            {"id": order_data['master_id']}
        )
        rows = result.mappings().all()
        exception_map = {row["exception_date"]: row["is_working"] for row in rows}
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 66 )  {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        exception_map = {}

    available_dates = []
    for date in days_range:
        weekday = date.weekday()
        if date in exception_map:
            if exception_map[date]:
                available_dates.append(date)
        elif weekday not in regular_days_off:
            available_dates.append(date)

    builder = InlineKeyboardBuilder()
    for date in available_dates[:7]:
        builder.button(text=date.strftime("%d.%m.%Y"), callback_data=f"edit_date_{date}")
    builder.adjust(2)

    try:
        await callback.message.edit_text("Выберите новую дату записи:", reply_markup=builder.as_markup())
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 86 )  {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")

    try:
        await state.set_state(EditBookingFSM.choosing_date)
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 91 )  {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")

@edit_router.callback_query(EditBookingFSM.choosing_date, lambda c: c.data.startswith("edit_date_"))
async def choose_new_date(callback: CallbackQuery, state: FSMContext):
    try:
        date_str = callback.data.split("_")[2]
        chosen_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 99 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        data = await state.get_data()
        master_id = data["master_id"]
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 106 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        query = "SELECT start_time, end_time FROM employees WHERE id = :id"
        result = await safe_execute(query, {"id": master_id})
        times = result.fetchone()
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 114 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        query = "SELECT time, total_duration FROM orders WHERE employee_id = :mid AND date = :date AND orders_id != :oid"
        params = {"mid": master_id, "date": chosen_date, "oid": data["order_id"]}
        result = await safe_execute(query, params)
        bookings = [{"start_time": row.time, "duration": row.total_duration} for row in result.fetchall()]
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 123 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        bookings = []

    try:
        required_duration = data["total_duration"]
        slots = calculate_free_slots(chosen_date, times.start_time, times.end_time, bookings, required_duration)
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 130 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        slots = []

    if not slots:
        try:
            await callback.message.edit_text("Нет доступного времени на выбранную дату.")
        except Exception as e:
            await send_long_message(f"Exception edit_record.py ( line - 137 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    builder = InlineKeyboardBuilder()
    for slot in slots:
        builder.button(text=slot.strftime("%H:%M"), callback_data=f"edit_time_{slot.strftime('%H:%M')}")
    builder.adjust(3)

    try:
        await state.update_data(chosen_date=str(chosen_date))
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 148 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")

    try:
        await callback.message.edit_text("Выберите новое время:", reply_markup=builder.as_markup())
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 153 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")

    try:
        await state.set_state(EditBookingFSM.choosing_time)
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 158 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")

@edit_router.callback_query(EditBookingFSM.choosing_time, lambda c: c.data.startswith("edit_time_"))
async def choose_new_time(callback: CallbackQuery, state: FSMContext):
    try:
        time_str = callback.data.split("_")[2]
        await state.update_data(chosen_time=time_str)
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 166 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        data = await state.get_data()
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 172 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        gender_result = await safe_execute(
            "SELECT gender FROM users WHERE id = :id", {"id": callback.from_user.id}
        )
        gender = gender_result.fetchone().gender
        await state.update_data(user_gender=gender)
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 182 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")

    try:
        # 👉 Вместо show_services вызываем сводку + кнопки
        await show_edit_summary(callback, state, show_conf_button=True)
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 188 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")

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
        await send_long_message(f"Exception edit_record.py ( line - 393 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        data = await state.get_data()
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 399 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        gender = data.get("user_gender")
        selected_services = data.get("selected_services", [])
        path = data.get("service_path", [])
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 407 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    # 1) Получаем все услуги по полу
    try:
        query = "SELECT id, name, price, duration, sex FROM services WHERE sex IN (:gender, 1)"
        result = await safe_execute(query, {"gender": gender})
        services = result.fetchall()
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 416 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    # 2) Если есть выбранные услуги, получим их названия
    selected_info = []
    if selected_services:
        try:
            placeholders = ",".join(map(str, selected_services))
            q = f"SELECT id, name FROM services WHERE id IN ({placeholders})"
            res = await safe_execute(q)
            selected_info = res.fetchall()
        except Exception as e:
            await send_long_message(f"Exception edit_record.py ( line - 428 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
            return

    # 3) Функция классификации
    def classify_service(name: str):
        nl = name.lower()
        is_haircut = bool(HAIRCUT_RE.search(nl))
        is_model = bool(MODEL_RE.search(nl))
        is_male = bool(MALE_RE.search(nl))
        is_female = bool(FEMALE_RE.search(nl))
        return {"is_haircut": is_haircut, "is_model": is_model, "is_male": is_male, "is_female": is_female}

    # 4) Проверяем, есть ли уже стрижка в выбранных
    selected_haircut = False
    try:
        for row in selected_info:
            cls = classify_service(row.name)
            if cls["is_haircut"]:
                selected_haircut = True
                break
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 449 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    # 5) Фильтруем услуги
    filtered_services = []
    try:
        for s in services:
            sid = s.id
            sname = s.name

            if sid in selected_services:
                continue

            cls = classify_service(sname)
            if selected_haircut and cls["is_haircut"]:
                continue

            filtered_services.append(s)
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 468 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        # --- Динамическое меню ---
        builder = InlineKeyboardBuilder()
        builder.adjust(1)
        tree = build_service_tree(filtered_services)

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

        for cat in sorted(categories, key=lambda x: x.lower()): 
            builder.button(text=cat.capitalize(), callback_data=f"ecat_{cat}")
        builder.adjust(1)
        for s in sorted(services_list, key=lambda x: x.price): 
            parts = [p for p in s.name.split("_") if p.strip()]
            last_part = parts[-1] if parts else s.name

            # флаг, выбрана ли услуга
            is_selected = s.id in selected_services  

            # добавляем галочку в начало текста, если выбрана
            mark = "✅ " if is_selected else ""

            # форматируем длительность
            duration = f"{s.duration} мин." if s.duration < 60 else f"{s.duration / 60:.1f} ч." 

            builder.button(
                text=f"{mark}{last_part.capitalize()} ({s.price}₽ ~ {duration})",
                callback_data=f"eservice_{s.id}"
            ) 
            
        if path: builder.button(text="⬅ Назад", callback_data="eback_cat") 
        if selected_services: builder.button(text="✅ Готово", callback_data="eservices_done") 
        builder.adjust(1)
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 507 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        await callback.message.edit_text("Выберите услугу:", reply_markup=builder.as_markup())
    except Exception as e:
        try:
            await callback.message.answer("Выберите услугу:", reply_markup=builder.as_markup())
        except Exception as e:
            await send_long_message(f"Exception edit_record.py ( line - 516 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")

    try:
        await state.set_state(EditBookingFSM.choosing_services)
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 521 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")

@edit_router.callback_query(EditBookingFSM.confirming, F.data == "edit_services_start")
async def start_edit_services(callback: CallbackQuery, state: FSMContext):
    await show_services(callback, state)

@edit_router.callback_query(EditBookingFSM.choosing_services)
async def choose_services(callback: CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split("_")
        data = await state.get_data()
        selected_services = data.get("selected_services", [])
        total_duration = data.get("total_duration", 0)
        total_price = data.get("total_price", 0)
        path = data.get("service_path", [])
        order_id = data.get("order_id")
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 534 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        if callback.data == "eback_cat":
            if path:
                path.pop()
            await state.update_data(service_path=path)
            return await show_services(callback, state)

        if callback.data.startswith("ecat_"):
            category = callback.data.split("_", 1)[1]
            path.append(category)
            await state.update_data(service_path=path)
            return await show_services(callback, state)

        if callback.data.startswith("eservice_"):
            service_id = int(callback.data.split("_")[1])

        if callback.data == "eservices_done":
            return await show_edit_summary(callback, state)
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 556 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    # Получаем параметры услуги
    try:
        query = "SELECT name, duration, price FROM services WHERE id = :id"
        result = await safe_execute(query, {"id": service_id})
        service = result.fetchone()
        if not service:
            await callback.answer("Услуга не найдена.", show_alert=True)
            return
    except Exception as e:
        await callback.answer()
        await callback.answer("Выберите хотя-бы одну услугу!", show_alert=True)
        await send_long_message(f"Exception edit_record.py ( line - 570 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        extra_minutes = 0
        ok, reason = await _can_fit_selected_time(state, extra_minutes)
        if not ok:
            await callback.answer(f"❌ {reason}", show_alert=True)
            return
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 580 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    try:
        # Фиксируем выбор
        selected_services.append(service_id)
        total_duration += service.duration
        total_price += service.price

        await state.update_data(
            selected_services=selected_services,
            total_duration=total_duration,
            total_price=total_price,
            order_id=order_id
        )
        await show_edit_summary(callback, state, True)
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 595 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return
    
    

async def show_edit_summary(callback: CallbackQuery, state: FSMContext, show_conf_button=False):
    try:
        data = await state.get_data()
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 301 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    master_id = data.get("master_id")
    try:
        result = await safe_execute("SELECT name FROM employees WHERE id = :id", {"id": master_id})
        master_name = result.fetchone().name
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 309 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        master_name = "(неизвестно)"

    selected_services = data.get("selected_services", [])
    if selected_services:
        query = f"SELECT name FROM services WHERE id IN ({','.join(map(str, selected_services))})"
        try:
            result = await safe_execute(query)
            service_names = [row.name for row in result.fetchall()]
        except Exception as e:
            await send_long_message(f"Exception edit_record.py ( line - 319 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
            service_names = ["(ошибка при получении услуг)"]
    else:
        service_names = ["(услуги не выбраны)"]

    total_duration = data.get("total_duration", 0)
    h, m = divmod(total_duration, 60)
    duration_str = f"{f'{h} ч ' if h else ''}{m} мин" if m or h == 0 else f"{h} ч"
    total_price = data.get("total_price", 0)

    builder = InlineKeyboardBuilder()
    builder.button(text="🛠 Изменить услуги", callback_data="edit_services_start")
    builder.button(text="🛠 Изменить дату и время", callback_data=f"start_edit_order_{data['order_id']}")

    if show_conf_button:
        builder.button(text="✅ Подтвердить изменения", callback_data="confirm_edit")
        builder.button(text="❌ Отменить", callback_data="cancel_edit")
        builder.adjust(2)
    else:
        builder.button(text="⬅️ Назад к записи", callback_data=f"order_detail_{data['order_id']}_{0}_active")
    builder.adjust(1)

    try:
        await callback.message.edit_text(
            f"Информация о записи:\n\n"
            f"📅 Дата: {datetime.fromisoformat(data['chosen_date']).strftime('%d.%m.%Y')}\n"
            f"🕒 Время: {data['chosen_time']}\n\n"
            f"💇‍♂️ Мастер: {master_name}\n\n"
            f"📋 Услуги:\n" + 
            "\n".join(f"• {name.replace('_', ', ').title()}" for name in service_names) + "\n\n"
            f"⏱ Длительность: {duration_str}\n"
            f"💰 Стоимость: {total_price}₽",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 351 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")

    try:
        await state.set_state(EditBookingFSM.confirming)
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 356 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")

@edit_router.callback_query(EditBookingFSM.confirming)
async def confirm_or_cancel(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 363 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    if callback.data == "econfirm_edit":
        try:
            await safe_execute("""
                UPDATE orders SET date = :date, time = :time, total_duration = :duration, total_price = :price
                WHERE orders_id = :oid
            """, {
                "date": datetime.strptime(data['chosen_date'], "%Y-%m-%d").date(),
                "time": datetime.strptime(data['chosen_time'], "%H:%M").time(),
                "duration": data['total_duration'],
                "price": data['total_price'],
                "oid": data['order_id']
            })
        except Exception as e:
            await send_long_message(f"Exception edit_record.py ( line - 379 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
            return

        try:
            await safe_execute(
                "DELETE FROM orders_has_services WHERE order_id = :oid",
                {"oid": data['order_id']}
            )
        except Exception as e:
            await send_long_message(f"Exception edit_record.py ( line - 388 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
            return

        for sid in data['selected_services']:
            try:
                await safe_execute(
                    "INSERT INTO orders_has_services (order_id, services_id) VALUES (:oid, :sid)",
                    {"oid": data['order_id'], "sid": sid}
                )
            except Exception as e:
                await send_long_message(f"Exception edit_record.py ( line - 398 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
                return

        try:
            await callback.message.edit_text("✅ Запись успешно обновлена!")
        except Exception as e:
            await send_long_message(f"Exception edit_record.py ( line - 404 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
    else:
        try:
            await callback.message.edit_text("❌ Изменения отменены.")
        except Exception as e:
            await send_long_message(f"Exception edit_record.py ( line - 409 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")

    try:
        await state.clear()
    except Exception as e:
        await send_long_message(f"Exception edit_record.py ( line - 414 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")


async def _can_fit_selected_time(state: FSMContext, extra_minutes: int) -> tuple[bool, str]:
    """
    Проверяет, влезает ли текущая запись (с уже выбранным временем)
    при увеличении общей длительности на extra_minutes.

    Возвращает (ok, reason). Если ok=False — reason содержит текст причины.
    """
    data = await state.get_data()

    if not data.get("chosen_date") or not data.get("chosen_time"):
        return True, ""

    master_id = data["master_id"]
    chosen_date = datetime.strptime(data["chosen_date"], "%Y-%m-%d").date()
    chosen_time = datetime.strptime(data["chosen_time"], "%H:%M").time()
    order_id = data.get("order_id")  # <-- берём id текущего заказа

    total_duration = data.get("total_duration", 0) + extra_minutes

    res = await safe_execute(
        "SELECT start_time, end_time FROM employees WHERE id = :id",
        {"id": master_id}
    )
    times = res.fetchone()
    if not times:
        return False, "Не удалось получить рабочее время мастера."

    work_end_dt = datetime.combine(chosen_date, times.end_time)
    start_dt = datetime.combine(chosen_date, chosen_time)
    end_dt = start_dt + timedelta(minutes=total_duration)
    buffer = timedelta(minutes=10)

    if end_dt > work_end_dt:
        return False, "❌ Длительность выходит за пределы рабочего дня мастера. \n\nВыберите более раннее время для этих услуг."

    # получаем все заказы, кроме текущего
    query = """
        SELECT orders_id, time as start_time, total_duration 
        FROM orders 
        WHERE employee_id = :mid AND date = :date
    """
    params = {"mid": master_id, "date": chosen_date}
    if order_id:
        query += " AND orders_id != :oid"
        params["oid"] = order_id

    res = await safe_execute(query, params)
    rows = res.fetchall()

    for row in rows:
        b_start = datetime.combine(chosen_date, row.start_time)
        b_end = b_start + timedelta(minutes=row.total_duration) + buffer
        if b_start < end_dt and start_dt < b_end:
            return False, f"❌ Пересечение с записью на {row.start_time.strftime('%H:%M')}."

    return True, ""

