from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
from create_bot import db_connector
from handlers.edit_record import EditBookingFSM
from messaging_exception.messaging import send_long_message
from aiogram.exceptions import DetailedAiogramError
from keyboards.all_kb import main_kb

recinf_router = Router()


async def safe_execute(query: str, params: dict | None = None):
    try:
        return await db_connector.execute_query(query, params or {})
    except Exception as e:
        await send_long_message(f"Ошибка SQL record_info.py ( line - 20 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return None

@recinf_router.message(F.text == '📋 Мои записи')
async def show_my_orders(message: Message, state: FSMContext):
    try:
        await send_orders_list(message=message, user_id=message.from_user.id, page=0, archived=False)
    except Exception as e:
        await send_long_message(f"Exception record_info.py ( line - 28 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

async def send_orders_list(message: Message | CallbackQuery, user_id: int, page: int, archived: bool):
    if isinstance(message, CallbackQuery):
        send_fn = message.message.edit_text
    else:
        send_fn = message.answer

    now = datetime.now().date()

    if archived:
        date_filter = "date < :today"
        params = {"uid": user_id, "today": now}
    else:
        date_filter = "date >= :today"
        params = {"uid": user_id, "today": now}

    query = f"""
    SELECT orders_id, date, time, total_price 
    FROM orders 
    WHERE user_id = :uid AND {date_filter} 
    ORDER BY date, time
    LIMIT 6 OFFSET :offset
    """
    params["offset"] = page * 5

    try:
        result = await safe_execute(query, params)
        rows = result.fetchall()
        orders = rows[:5]
        has_next_page = len(rows) > 5
    except Exception as e:
        await send_long_message(f"Exception record_info.py ( line - 61 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    if not orders:
        try:
            await send_fn("Записи в архиве не найдены." if archived else "Записи не найдены.")
        except Exception as e:
            await send_long_message(f"Exception record_info.py ( line - 68 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    builder = InlineKeyboardBuilder()
    for order in orders:
        try:
            label = f"{order.date.strftime('%d.%m')} {order.time.strftime('%H:%M')} - {order.total_price}₽"
            builder.button(text=label, callback_data=f"order_detail_{order.orders_id}_{page}_{'archive' if archived else 'active'}")
        except Exception as e:
            await send_long_message(f"Exception record_info.py ( line - 77 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")

    try:
        if page > 0:
            builder.button(text="⬅️ Назад", callback_data=f"order_page_{page-1}_{'archive' if archived else 'active'}")
        if has_next_page:
            builder.button(text="➡️ Далее", callback_data=f"order_page_{page+1}_{'archive' if archived else 'active'}")

        if not archived:
            builder.button(
                text="📂 Архив записей",
                callback_data="order_toggle_archive"
            )
        else:
            builder.button(
                text="📋 Текущие записи",
                callback_data="order_toggle_active"
            )
        builder.adjust(1)
    except Exception as e:
        await send_long_message(f"Exception record_info.py ( line - 97 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")

    try:
        await send_fn("Ваши записи:" if not archived else "Архив записей:", reply_markup=builder.as_markup())
    except Exception as e:
        await send_long_message(f"Exception record_info.py ( line - 102 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")

@recinf_router.callback_query(F.data.startswith("order_page_"))
async def paginate_orders(callback: CallbackQuery):
    parts = callback.data.split("_")
    page = int(parts[2])
    section = parts[3]
    await send_orders_list(callback, callback.from_user.id, page, section == 'archive')

@recinf_router.callback_query(F.data.startswith("order_toggle_"))
async def toggle_orders_section(callback: CallbackQuery):
    parts = callback.data.split("_")
    section = parts[-1]
    await send_orders_list(callback, callback.from_user.id, 0, section == 'archive')

@recinf_router.callback_query(F.data.startswith("order_detail_"))
async def show_order_detail(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    # "order", "detail", "{order_id}", "{page}", "{section}"
    if len(parts) < 5:
        try:
            await callback.answer("Некорректные данные кнопки.", show_alert=True)
        except Exception as e:
            await send_long_message(f"Exception record_info.py ( line - 125 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    order_id = parts[2]
    page = parts[3]
    section = parts[4]

    query_recinf = """
    SELECT 
        o.date,
        o.time,
        o.total_price,
        o.total_duration,
        o.employee_id,
        e.name AS master_name,
        s.name AS service_name,
        s.price AS service_price,
        ohs.services_id as service_id
    FROM orders o
    JOIN employees e ON o.employee_id = e.id
    JOIN orders_has_services ohs ON o.orders_id = ohs.order_id
    JOIN services s ON ohs.services_id = s.id
    WHERE o.orders_id = :id
    ORDER BY s.name
    """
    try:
        result = await safe_execute(query_recinf, {"id": int(order_id)})
        records = result.mappings().all()
    except Exception as e:
        await send_long_message(f"Exception record_info.py ( line - 154 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    if not records:
        try:
            await callback.answer("❌ Запись не найдена.", show_alert=True)
        except Exception as e:
            await send_long_message(f"Exception record_info.py ( line - 161 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    # Берём общую информацию из первой строки
    first = records[0]

    try:
        await state.set_state(EditBookingFSM.choosing_date)
        await state.set_data({
            "order_id": int(order_id),
            "chosen_date": first["date"].isoformat(),
            "chosen_time": first["time"].strftime('%H:%M'),
            "master_id": first["employee_id"],
            "total_duration": first["total_duration"],
            "total_price": first["total_price"],
            "selected_services": [r["service_id"] for r in records]
        })
    except Exception as e:
        await send_long_message(f"Exception record_info.py ( line - 179 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return

    # Формируем список услуг
    try:
        h, m = divmod(first['total_duration'], 60)
        duration = f"{f'{h} ч ' if h else ''}{m} мин" if m or h == 0 else f"{h} ч"
        detail_text = (
            f"📅 Дата: {first['date'].strftime('%d.%m.%Y')}\n"
            f"🕒 Время: {first['time'].strftime('%H:%M')}\n\n"
            f"💇‍♂️ Мастер: {first['master_name']}\n\n"
            f"📋 Услуги:\n" +
            "\n".join(f"• {row['service_name'].replace('_', ', ').title()}" for row in records) + "\n\n" 
            f"⏱ Общая длительность услуг: {duration}\n"
            f"💰 Общая стоимость: {first['total_price']}₽\n"
        )

        builder = InlineKeyboardBuilder()
        if first['date'] >= datetime.now().date():
            builder.button(
                text="✏ Изменить запись",
                callback_data=f"edit_order_{order_id}"
            )
        datetimes = f"{first['date'].strftime('%d.%m.%Y')} в {first['time'].strftime('%H:%M')}"
        builder.button(
            text="❌ Отменить запись",
            callback_data=f"o_d_{order_id}_{datetimes}_{page}_{section}"
        )
        builder.button(
            text="⬅️ Назад к записям",
            callback_data=f"order_page_{page}_{section}"
        )
        builder.adjust(2)
        await callback.message.edit_text(detail_text, reply_markup=builder.as_markup())
    except Exception as e:
        await send_long_message(f"Exception record_info.py ( line - 213 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")


@recinf_router.callback_query(F.data.startswith("o_d_"))
async def show_order_detail(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    order_id = parts[2]
    datetimes = parts[3]
    page = parts[4]
    section = parts[5]
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Подтвердить удаление",
        callback_data=f"complete_deletes_{order_id}"
    )
    builder.button(
        text="❌ Отменить удаление",
        callback_data=f"order_detail_{order_id}_{page}_{section}"
    )
    # "order", "detail", "{order_id}", "{page}", "{section}"

    await callback.message.edit_text(f"Вы уверены что хотите отменить запись на {datetimes}?", reply_markup=builder.as_markup())

@recinf_router.callback_query(F.data.startswith("complete_deletes_"))
async def comfirm_delete_employee(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    order_id = int(parts[2])
    try:
        query = "DELETE FROM orders WHERE orders_id = :id"
        await safe_execute(query, {"id": order_id})
        await callback.message.edit_text("✅ Запись успешно отменена!")
    except DetailedAiogramError as e:
        print(f"Ошибка при удалении записи: {e}")
        await callback.message.edit_text("❌ При удалении данных произошла ошибка в БД!")
        await send_long_message(f"Excpetion record_info.py 247 line {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}") 
        return