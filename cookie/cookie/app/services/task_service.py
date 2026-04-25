from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.adapters.pan_adapter import MockPanAdapter, PanAdapterError
from app.domain.models import Task, TaskStatus
from app.infra.db import Database


class TaskService:
    def __init__(
        self,
        db: Database,
        adapter: MockPanAdapter,
        max_retries: int = 3,
        retry_delay_seconds: float = 2,
        on_task_terminal: Callable[[Task], Awaitable[None]] | None = None,
    ) -> None:
        self.db = db
        self.adapter = adapter
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.on_task_terminal = on_task_terminal
        self.queue: asyncio.Queue[int] = asyncio.Queue()

    async def create_and_enqueue(self, user_id: int, link: str, target_path: str) -> int:
        task_id = await self.db.create_task(user_id=user_id, link=link, target_path=target_path)
        await self.queue.put(task_id)
        return task_id

    async def get_task(self, task_id: int) -> Task | None:
        return await self.db.get_task(task_id)

    async def list_tasks_by_user(self, user_id: int, limit: int = 10) -> list[Task]:
        return await self.db.list_tasks_by_user(user_id=user_id, limit=limit)

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
                await self._notify_terminal(task_id)
            except PanAdapterError as exc:
                await self._handle_failure(task_id=task_id, reason=str(exc))
            except Exception as exc:  # pragma: no cover
                await self._handle_failure(task_id=task_id, reason=f"未知错误: {exc}")
            finally:
                self.queue.task_done()

    async def _handle_failure(self, task_id: int, reason: str) -> None:
        retry_count = await self.db.increment_retry_count(task_id)
        if retry_count <= self.max_retries:
            await self.db.update_task_status(
                task_id,
                TaskStatus.PENDING,
                f"执行失败，准备第 {retry_count} 次重试：{reason}",
            )
            await asyncio.sleep(self.retry_delay_seconds)
            await self.queue.put(task_id)
            return

        await self.db.update_task_status(
            task_id,
            TaskStatus.FAILED,
            f"失败且超过重试上限({self.max_retries})：{reason}",
        )
        await self._notify_terminal(task_id)

    async def _notify_terminal(self, task_id: int) -> None:
        if self.on_task_terminal is None:
            return
        task = await self.db.get_task(task_id)
        if task is None:
            return
        try:
            await self.on_task_terminal(task)
        except Exception as exc:  # pragma: no cover
            logging.exception("任务结果通知发送失败 task_id=%s: %s", task_id, exc)
