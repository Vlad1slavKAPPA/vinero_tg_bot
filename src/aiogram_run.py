import asyncio
from create_bot import bot, dp
from handlers.start import start_router
from handlers.info import info_router
from handlers.record_info import recinf_router
from handlers.client_record import client_record_router
from handlers.edit_record import edit_router
from handlers.reviews import reviews_router
from handlers.admin_panel import apanel_router
from handlers.employee_panel import emp_router
from create_bot import db_connector, r_connector
from notification_handler import notifications

async def connection_monitor(db_connector):
    while True:
        try:
            await db_connector.test_connection()
            print("Test connection Postgre прошло успешно!")
        except Exception as e:
            print(f"Проблемы с БД! | {e} | Переподключаемся...")
            await db_connector.connect_with_retry()
        await asyncio.sleep(300)  # 5 минут

async def connection_monitor_redis(r_connector):
    while True:
        try:
            await r_connector.check_redis(r_connector.storage)
            print("Test connection Redis прошло успешно!")
        except Exception as e:
            print(f"Проблемы с Redis! | {e} | Переподключаемся...")
            await r_connector.connect_with_retry()
        await asyncio.sleep(360)  # 6 минут


async def main():
    # scheduler.add_lob(send_time_msg, 'interval', seconds=10)
    # scheduler.start()
    await db_connector.connect_with_retry() 
    await db_connector.load_admins()
    await db_connector.load_employees()
    await r_connector.connect_with_retry()
    dp.include_router(start_router)
    dp.include_router(info_router)
    dp.include_router(client_record_router)
    dp.include_router(recinf_router)
    dp.include_router(edit_router)
    dp.include_router(reviews_router)
    dp.include_router(apanel_router)
    dp.include_router(emp_router)
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(connection_monitor(db_connector))
    asyncio.create_task(connection_monitor_redis(r_connector))
    try:
        await notifications.setup_scheduler(bot, db_connector)
    except Exception as e:
        print(f"Неудачный запуск уведомлений при запуске бота!:\n\n{e}")

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())