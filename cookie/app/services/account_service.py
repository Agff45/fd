from app.infra.db import Database


class AccountService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def bind(self, user_id: int, bind_note: str) -> None:
        await self.db.bind_account(user_id, bind_note)

    async def is_bound(self, user_id: int) -> bool:
        return await self.db.is_account_bound(user_id)
