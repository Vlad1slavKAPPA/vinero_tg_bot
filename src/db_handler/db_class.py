from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import asyncio
from decouple import config


class DatabaseConnector:
    def __init__(self):
        self.admins_cache = []
        self.employee_cache = []
        self.engine = None
        self.async_session = None

    def create_engine_and_session(self):
        if config("USE_SSH").lower() == "true":
            # 🔹 Локальная разработка (с туннелем)
            from sshtunnel import SSHTunnelForwarder

            self.tunnel = SSHTunnelForwarder(
                (config("SSH_HOST"), int(config("SSH_PORT"))),
                ssh_username=config("SSH_USER"),
                ssh_password=config("SSH_PASSWORD"),
                remote_bind_address=(config("DB_HOST"), int(config("DB_PORT")))
            )
            self.tunnel.start()
            host = "localhost"
            port = self.tunnel.local_bind_port
        else:
            # 🔹 Docker / продакшн
            host = config("POSTGRES_HOST", default="postgres")
            port = config("POSTGRES_PORT", default="5432")

        DATABASE_URL = (
            f"postgresql+asyncpg://{config('POSTGRES_USER')}:"
            f"{config('POSTGRES_PASSWORD')}@{host}:{port}/{config('POSTGRES_DB')}"
        )

        self.engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def test_connection(self):
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar()

    async def execute_query(self, query, *args):
        try:
            async with self.async_session() as session:
                result = await session.execute(text(query), *args)

                # Определяем тип SQL-запроса по первому слову
                qtype = query.strip().split()[0].upper()
                if qtype in {"INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"}:
                    await session.commit()

                return result
        except Exception as e:
            print(f"Ошибка запроса: {e}")
            await self.connect_with_retry()
            async with self.async_session() as session:
                result = await session.execute(text(query), *args)

                qtype = query.strip().split()[0].upper()
                if qtype in {"INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"}:
                    await session.commit()

                return result

    async def load_admins(self):
        query = "SELECT id FROM users WHERE admin_status = true"
        result = await self.execute_query(query)
        self.admins_cache = [row.id for row in result.fetchall()]
        print(f"Загружено админов: {self.admins_cache}")

    async def load_employees(self):
        query = "SELECT user_id, id FROM employees"
        result = await self.execute_query(query)
        self.employee_cache = [row.user_id for row in result.fetchall()]
        print(f"Загружено сотрудников: {self.employee_cache}")

    async def connect_with_retry(self):
        self.create_engine_and_session()

        start_time = asyncio.get_event_loop().time()
        first_phase_duration = 60
        first_phase_attempts = 5
        first_phase_interval = first_phase_duration / first_phase_attempts

        attempt = 0

        while True:
            try:
                attempt += 1
                print(f"Попытка подключения к БД #{attempt}...")
                await self.test_connection()
                print("Подключение к базе данных успешно!")
                break
            except Exception as e:
                print(e)
                now = asyncio.get_event_loop().time()
                elapsed = now - start_time

                if elapsed < first_phase_duration:
                    wait_time = first_phase_interval
                else:
                    wait_time = 30

                print(f"Ошибка подключения: {e}. Повтор через {wait_time} секунд.")
                await asyncio.sleep(wait_time)

        return self.engine, self.async_session

    def close(self):
        if hasattr(self, "tunnel") and self.tunnel:
            self.tunnel.stop()