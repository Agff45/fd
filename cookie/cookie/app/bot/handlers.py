from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.services.account_service import AccountService
from app.services.task_service import TaskService


def build_router(account_service: AccountService, task_service: TaskService) -> Router:
    router = Router()

    @router.message(Command("start"))
    async def start_handler(message: Message) -> None:
        await message.answer(
            "已启动。\n"
            "命令：\n"
            "/bind <备注>\n"
            "/save <链接> [目录]\n"
            "/status <任务ID>\n"
            "/tasks [数量]"
        )

    @router.message(Command("bind"))
    async def bind_handler(message: Message) -> None:
        user_id = int(message.from_user.id)
        args = (message.text or "").split(maxsplit=1)
        bind_note = args[1].strip() if len(args) > 1 else "manual_bind"
        await account_service.bind(user_id=user_id, bind_note=bind_note)
        await message.answer("绑定成功（MVP 模式，已写入本地数据库）。")

    @router.message(Command("save"))
    async def save_handler(message: Message) -> None:
        user_id = int(message.from_user.id)
        if not await account_service.is_bound(user_id):
            await message.answer("请先执行 /bind 完成账号绑定。")
            return

        parts = (message.text or "").split()
        if len(parts) < 2:
            await message.answer("用法：/save <链接> [目录]")
            return

        link = parts[1]
        target_path = parts[2] if len(parts) >= 3 else "/"
        task_id = await task_service.create_and_enqueue(user_id=user_id, link=link, target_path=target_path)
        await message.answer(f"任务已创建：#{task_id}，正在排队执行。")

    @router.message(Command("status"))
    async def status_handler(message: Message) -> None:
        parts = (message.text or "").split()
        if len(parts) < 2 or not parts[1].isdigit():
            await message.answer("用法：/status <任务ID>")
            return

        task_id = int(parts[1])
        task = await task_service.get_task(task_id)
        if task is None:
            await message.answer("任务不存在。")
            return

        await message.answer(
            f"任务 #{task.id}\n"
            f"状态：{task.status}\n"
            f"重试次数：{task.retry_count}\n"
            f"链接：{task.link}\n"
            f"目录：{task.target_path}\n"
            f"结果：{task.result_message or '-'}"
        )

    @router.message(Command("tasks"))
    async def tasks_handler(message: Message) -> None:
        user_id = int(message.from_user.id)
        parts = (message.text or "").split()
        limit = 5
        if len(parts) >= 2 and parts[1].isdigit():
            limit = max(1, min(20, int(parts[1])))

        tasks = await task_service.list_tasks_by_user(user_id=user_id, limit=limit)
        if not tasks:
            await message.answer("暂无任务记录。")
            return

        lines: list[str] = ["最近任务："]
        for task in tasks:
            lines.append(
                f"#{task.id} {task.status} 重试{task.retry_count}次 目录:{task.target_path}"
            )
        await message.answer("\n".join(lines))

    return router
