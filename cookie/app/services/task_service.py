from __future__ import annotations

import asyncio

from app.adapters.pan_adapter import MockPanAdapter, PanAdapterError
from app.domain.models import Task, TaskStatus
from app.infra.db import Database


class TaskService:
    def __init__(self, db: Database, adapter: MockPanAdapter) -> None:
        self.db = db
        self.adapter = adapter
        self.queue: asyncio.Queue[int] = asyncio.Queue()

    async def create_and_enqueue(self, user_id: int, link: str, target_path: str) -> int:
        task_id = await self.db.create_task(user_id=user_id, link=link, target_path=target_path)
        await self.queue.put(task_id)
        return task_id

    async def get_task(self, task_id: int) -> Task | None:
        return await self.db.get_task(task_id)

    async def worker(self) -> None:
        while True:
            task_id = await self.queue.get()
            try:
                await self.db.update_task_status(task_id, TaskStatus.RUNNING, "任务执行中")
                task = await self.db.get_task(task_id)
                if task is None:
                    continue

                result = await self.adapter.transfer(task.link, task.target_path)
                await self.db.update_task_status(task_id, TaskStatus.SUCCESS, result)
            except PanAdapterError as exc:
                await self.db.update_task_status(task_id, TaskStatus.FAILED, str(exc))
            except Exception as exc:  # pragma: no cover
                await self.db.update_task_status(task_id, TaskStatus.FAILED, f"未知错误: {exc}")
            finally:
                self.queue.task_done()
