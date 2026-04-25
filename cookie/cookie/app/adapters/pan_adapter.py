from __future__ import annotations

import asyncio


class PanAdapterError(Exception):
    pass


class MockPanAdapter:
    async def transfer(self, link: str, target_path: str) -> str:
        # 这里只做可运行演示，真实实现请替换成官方授权接口调用。
        await asyncio.sleep(2)
        if "fail" in link.lower():
            raise PanAdapterError("模拟失败：链接触发了 fail 关键字。")
        return f"模拟转存成功，目标目录：{target_path}"
