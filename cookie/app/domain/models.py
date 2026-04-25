from dataclasses import dataclass
from enum import StrEnum


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass
class Task:
    id: int
    user_id: int
    link: str
    target_path: str
    status: TaskStatus
    result_message: str
    created_at: str
    updated_at: str
