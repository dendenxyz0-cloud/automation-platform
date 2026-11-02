from __future__ import annotations

import json
import random
from typing import Any, Mapping

from playwright.async_api import BrowserContext

from app.services.platform_handlers.base import BasePlatformHandler, PlatformActionError


class DiscordHandler(BasePlatformHandler):
    """Placeholder for Discord-specific, explicitly bounded browser actions."""

    async def execute_action(
        self,
        browser_context: BrowserContext,
        target_url: str,
        action_type: str,
    ) -> dict[str, Any]:
        if not action_type:
            raise PlatformActionError("action_type is required")

        self.logger.info("Executing Discord action", extra={"action_type": action_type})
        await self._apply_session_cookies(browser_context)
        navigation = await self._navigate(browser_context, target_url)
        return {"platform": "discord", "action_type": action_type, **navigation}

    async def _apply_session_cookies(self, browser_context: BrowserContext) -> None:
        cookies = self.account.session_cookies or []
        if cookies:
            await browser_context.add_cookies(cookies)

    async def _human_scroll(self, page: any) -> None:
        for _ in range(random.randint(1, 3)):
            await page.mouse.wheel(0, random.randint(100, 450))
