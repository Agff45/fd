import asyncio
import contextlib

from aiogram import Bot, Dispatcher

from app.adapters.pan_adapter import MockPanAdapter
from app.bot.handlers import build_router
from app.core.config import load_settings
from app.infra.db import Database
from app.services.account_service import AccountService
from app.services.task_service import TaskService


async def run() -> None:
    settings = load_settings()
    db = Database(settings.db_path)
    await db.init()

    adapter = MockPanAdapter()
    account_service = AccountService(db)
    task_service = TaskService(db, adapter)

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.include_router(build_router(account_service, task_service))

    worker_task = asyncio.create_task(task_service.worker())
    try:
        await dp.start_polling(bot)
    finally:
        worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker_task
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run())
