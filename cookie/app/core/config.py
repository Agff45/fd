from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass
class Settings:
    bot_token: str
    owner_tg_id: int
    db_path: str
    https_proxy: str | None
    polling_timeout: int
    max_retries: int
    retry_delay_seconds: float


def load_settings() -> Settings:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    owner_raw = os.getenv("OWNER_TG_ID", "0").strip()
    db_path = os.getenv("DB_PATH", "bot.db").strip()
    https_proxy = os.getenv("HTTPS_PROXY", "").strip() or None
    polling_timeout_raw = os.getenv("POLLING_TIMEOUT", "30").strip()
    max_retries_raw = os.getenv("MAX_RETRIES", "3").strip()
    retry_delay_raw = os.getenv("RETRY_DELAY_SECONDS", "2").strip()

    if not token:
        raise ValueError("BOT_TOKEN 未配置，请先复制 .env.example 为 .env 并填写。")

    try:
        owner_tg_id = int(owner_raw)
    except ValueError as exc:
        raise ValueError("OWNER_TG_ID 必须是整数。") from exc

    try:
        polling_timeout = int(polling_timeout_raw)
        max_retries = int(max_retries_raw)
        retry_delay_seconds = float(retry_delay_raw)
    except ValueError as exc:
        raise ValueError("POLLING_TIMEOUT、MAX_RETRIES、RETRY_DELAY_SECONDS 配置格式错误。") from exc

    return Settings(
        bot_token=token,
        owner_tg_id=owner_tg_id,
        db_path=db_path,
        https_proxy=https_proxy,
        polling_timeout=polling_timeout,
        max_retries=max_retries,
        retry_delay_seconds=retry_delay_seconds,
    )
