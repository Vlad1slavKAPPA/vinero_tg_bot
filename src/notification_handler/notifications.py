from datetime import datetime, date
from zoneinfo import ZoneInfo
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from create_bot import db_connector
from messaging_exception.messaging import send_long_message


async def safe_execute(query: str, params: dict | None = None):
    try:
        return await db_connector.execute_query(query, params or {})
    except Exception as e:
        await send_long_message(f"Ошибка SQL notifications.py ( line - 13 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return None

async def is_employee_working_today(emp_id: int, db_connector) -> bool:
    """Проверка, работает ли сотрудник сегодня по расписанию и исключениям"""
    try:
        print("Проверка, работает ли сотрудник сегодня по расписанию и исключениям")
        today = date.today()

        # 1. Получаем регулярные выходные (weekday: 0=Пн ... 6=Вс)
        try:
            result = await safe_execute(
                "SELECT weekday FROM employees_week_offday WHERE employee_id = :id",
                {"id": emp_id}
            )
            regular_days_off = {row.weekday for row in result.fetchall()}
        except Exception as e:
            await send_long_message(f"Exception notifications.py ( line - 30 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
            regular_days_off = set()

        # 2. Проверяем исключения
        try:
            result = await safe_execute(
                "SELECT exception_date, is_working FROM employees_exceptions WHERE employee_id = :id",
                {"id": emp_id}
            )
            rows = result.mappings().all()
            exception_map = {row["exception_date"]: row["is_working"] for row in rows}
        except Exception as e:
            await send_long_message(f"Exception notifications.py ( line - 42 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
            exception_map = {}

        # 3. Проверка
        if today in exception_map:
            return exception_map[today]  # True → работает в исключении, False → выходной в исключении
        elif today.weekday() in regular_days_off:
            return False  # обычный выходной
        return True  # обычный рабочий день
    except Exception as e:
        await send_long_message(f"Exception notifications.py ( line - 52 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
        return False


async def send_daily_notifications(bot: Bot, db_connector):
    try:
        today = date.today()

        # Получаем сотрудников
        try:
            employees = await db_connector.execute_query("SELECT id, user_id, name FROM employees")
            employees = employees.mappings().all()
        except Exception as e:
            await send_long_message(f"Exception notifications.py ( line - 65 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
            employees = []

        for emp in employees:
            try:
                works_today = await is_employee_working_today(emp["id"], db_connector)
                if not works_today:
                    continue  # сотрудник сегодня не работает → ничего не отправляем

                # Достаём клиентов на сегодня
                try:
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
                except Exception as e:
                    await send_long_message(f"Exception notifications.py ( line - 94 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
                    rows = []

                # --- группировка заказов ---
                orders_map = {}
                for row in rows:
                    oid = row["orders_id"]
                    if oid not in orders_map:
                        orders_map[oid] = {
                            "time": row["time"],
                            "client_name": row["client_name"],
                            "phone": row["phone"],
                            "user_id": row["id"],
                            "total_duration": row["total_duration"],
                            "total_price": row["total_price"],
                            "services": []
                        }
                    orders_map[oid]["services"].append(row["service_name"])

                orders = list(orders_map.values())

                if not orders:
                    msg = f"Сегодня ({today.strftime('%d.%m.%Y')}) клиентов нет."
                else:
                    lines = [f"Клиенты на {today.strftime('%d.%m.%Y')}:"]                    
                    count = 1
                    for o in orders:
                        services_text = o['services']
                        duration = f"{o['total_duration']} мин." if o['total_duration'] < 60 else f"{o['total_duration'] / 60} ч."
                        time_str = o['time'].strftime("%H:%M")
                        lines.append(
                            f"\n\n{count}. Время:⏰ {time_str}\n"
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

                try:
                    await bot.send_message(emp["user_id"], msg)
                except Exception as e:
                    await send_long_message(f"Exception notifications.py ( line - 139 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
            except Exception as e:
                await send_long_message(f"Exception notifications.py ( line - 141 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
    except Exception as e:
        await send_long_message(f"Exception notifications.py ( line - 143 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")


async def setup_scheduler(bot: Bot, db_connector):
    """Запускаем планировщик на каждый день в 09:00."""
    try:
        print("Запускаем планировщик на каждый день в 09:00.")
        try:
            scheduler = AsyncIOScheduler(timezone=ZoneInfo("Europe/Moscow"))
            scheduler.add_job(send_daily_notifications, "cron", hour=9, minute=0, args=[bot, db_connector])
            scheduler.start()
            return scheduler
        except Exception as e:
            await send_long_message(f"Exception notifications.py ( line - 156 ) {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n{e}")
    except Exception as e:
        print(f"Неудачный запуск планировщика!: \n\n {e}")