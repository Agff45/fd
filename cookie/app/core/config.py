from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass
class Settings:
    bot_token: str
    owner_tg_id: int
    db_path: str


def load_settings() -> Settings:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    owner_raw = os.getenv("OWNER_TG_ID", "0").strip()
    db_path = os.getenv("DB_PATH", "bot.db").strip()

    if not token:
        raise ValueError("BOT_TOKEN 未配置，请先复制 .env.example 为 .env 并填写。")

    try:
        owner_tg_id = int(owner_raw)
    except ValueError as exc:
        raise ValueError("OWNER_TG_ID 必须是整数。") from exc

    return Settings(bot_token=token, owner_tg_id=owner_tg_id, db_path=db_path)
