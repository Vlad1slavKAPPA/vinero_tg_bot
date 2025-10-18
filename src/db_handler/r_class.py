import asyncio
from aiogram.fsm.storage.redis import RedisStorage
from redis.exceptions import ConnectionError
from decouple import config


class RedisConnector:
    def __init__(self):
        self.storage = None
        self.tunnel = None

    def start_tunnel(self):
        """Подключение через SSH (локальная разработка)"""
        from sshtunnel import SSHTunnelForwarder

        self.tunnel = SSHTunnelForwarder(
            (config("SSH_HOST"), int(config("SSH_PORT"))),
            ssh_username=config("SSH_USER"),
            ssh_password=config("SSH_PASSWORD"),
            remote_bind_address=(config("R_HOST"), int(config("R_PORT")))
        )
        self.tunnel.start()

    def stop_tunnel(self):
        if self.tunnel:
            self.tunnel.stop()

    async def check_redis(self, storage: RedisStorage):
        try:
            pong = await storage.redis.ping()
            return pong
        except ConnectionError:
            return False

    async def connect_with_retry(self):

        if config("USE_SSH").lower() == "true":
            # 🔹 локальная разработка
            self.start_tunnel()
            host = "localhost"
            port = self.tunnel.local_bind_port
        else:
            # 🔹 Docker / продакшн
            host = config("REDIS_HOST", default="redis")
            port = config("REDIS_PORT", default="6379")

        password = config("REDIS_PASSWORD")

        redis_url = f"redis://:{password}@{host}:{port}/0"
        self.storage = RedisStorage.from_url(redis_url)

        retry_delay = 5
        max_retries = 5
        retries = 0
        while retries < max_retries:
            if await self.check_redis(self.storage):
                print("✅ Redis connected")
                return self.storage
            print(f"Redis not available, retrying in {retry_delay} seconds...")
            retries += 1
            await asyncio.sleep(retry_delay)
        raise ConnectionError("Cannot connect to Redis after retries")

    def close(self):
        self.stop_tunnel()