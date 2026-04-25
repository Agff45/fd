from __future__ import annotations

import aiosqlite

from app.domain.models import Task, TaskStatus


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    user_id INTEGER PRIMARY KEY,
                    bind_note TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    link TEXT NOT NULL,
                    target_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    result_message TEXT NOT NULL DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await self._ensure_tasks_columns(db)
            await db.commit()

    async def _ensure_tasks_columns(self, db: aiosqlite.Connection) -> None:
        cursor = await db.execute("PRAGMA table_info(tasks)")
        rows = await cursor.fetchall()
        columns = {row[1] for row in rows}
        if "retry_count" not in columns:
            await db.execute(
                "ALTER TABLE tasks ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0"
            )

    async def bind_account(self, user_id: int, bind_note: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO accounts(user_id, bind_note, updated_at)
                VALUES(?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    bind_note=excluded.bind_note,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (user_id, bind_note),
            )
            await db.commit()

    async def is_account_bound(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM accounts WHERE user_id=? LIMIT 1", (user_id,)
            )
            row = await cursor.fetchone()
            return row is not None

    async def create_task(self, user_id: int, link: str, target_path: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO tasks(user_id, link, target_path, status, retry_count, result_message)
                VALUES(?, ?, ?, ?, 0, '')
                """,
                (user_id, link, target_path, TaskStatus.PENDING.value),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def update_task_status(
        self, task_id: int, status: TaskStatus, result_message: str = ""
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE tasks
                SET status=?, result_message=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (status.value, result_message, task_id),
            )
            await db.commit()

    async def increment_retry_count(self, task_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE tasks
                SET retry_count=retry_count+1, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (task_id,),
            )
            cursor = await db.execute("SELECT retry_count FROM tasks WHERE id=?", (task_id,))
            row = await cursor.fetchone()
            await db.commit()
            if row is None:
                return 0
            return int(row[0])

    async def get_task(self, task_id: int) -> Task | None:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, user_id, link, target_path, status, retry_count, result_message, created_at, updated_at
                FROM tasks WHERE id=?
                """,
                (task_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None

            return Task(
                id=row[0],
                user_id=row[1],
                link=row[2],
                target_path=row[3],
                status=TaskStatus(row[4]),
                retry_count=row[5],
                result_message=row[6],
                created_at=row[7],
                updated_at=row[8],
            )
