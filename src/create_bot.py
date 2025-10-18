import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from decouple import config
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db_handler.db_class import DatabaseConnector
from db_handler.r_class import RedisConnector


# --- Настройка логирования ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Отдельно настраиваем уровень логирования для SQLAlchemy
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

# Главный логгер бота
logger = logging.getLogger(__name__)

# --- Инициализация бота и диспетчера ---
db_connector = DatabaseConnector()
r_connector = RedisConnector()
scheduler = AsyncIOScheduler(timezone='Europe/Moscow')

bot = Bot(token=config('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=r_connector.storage)