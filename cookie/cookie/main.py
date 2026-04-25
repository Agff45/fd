import asyncio
import contextlib
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramNetworkError

from app.adapters.pan_adapter import MockPanAdapter
from app.bot.handlers import build_router
from app.core.config import load_settings
from app.domain.models import Task, TaskStatus
from app.infra.db import Database
from app.services.account_service import AccountService
from app.services.task_service import TaskService


async def send_with_retry(bot: Bot, chat_id: int, text: str, max_tries: int = 3) -> None:
    for attempt in range(1, max_tries + 1):
        try:
            await bot.send_message(chat_id=chat_id, text=text)
            return
        except TelegramNetworkError:
            if attempt >= max_tries:
                raise
            await asyncio.sleep(attempt)


async def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    settings = load_settings()
    db = Database(settings.db_path)
    await db.init()
    logging.info("数据库初始化完成：%s", settings.db_path)

    adapter = MockPanAdapter()
    account_service = AccountService(db)

    async def on_task_terminal(task: Task) -> None:
        status_text = "成功" if task.status == TaskStatus.SUCCESS else "失败"
        text = (
            f"任务 #{task.id} 已结束\n"
            f"状态：{status_text}\n"
            f"重试次数：{task.retry_count}\n"
            f"目录：{task.target_path}\n"
            f"结果：{task.result_message or '-'}"
        )
        await send_with_retry(bot, chat_id=task.user_id, text=text)

    task_service = TaskService(
        db,
        adapter,
        max_retries=settings.max_retries,
        retry_delay_seconds=settings.retry_delay_seconds,
        on_task_terminal=on_task_terminal,
    )

    session = AiohttpSession(proxy=settings.https_proxy) if settings.https_proxy else AiohttpSession()
    bot = Bot(token=settings.bot_token, session=session)
    dp = Dispatcher()
    dp.include_router(build_router(account_service, task_service))

    worker_task = asyncio.create_task(task_service.worker())
    try:
        me = await bot.get_me()
        logging.info("Bot 已登录：@%s (id=%s)", me.username, me.id)
        logging.info(
            "开始轮询，timeout=%s, max_retries=%s, retry_delay=%ss",
            settings.polling_timeout,
            settings.max_retries,
            settings.retry_delay_seconds,
        )
        await dp.start_polling(bot, polling_timeout=settings.polling_timeout)
    finally:
        worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker_task
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run())
