from __future__ import annotations

from typing import Any

from playwright.async_api import BrowserContext

from app.services.platform_handlers.base import BasePlatformHandler, PlatformActionError


class InstagramHandler(BasePlatformHandler):
    """Placeholder for Instagram-specific, explicitly bounded browser actions."""

    async def execute_action(
        self,
        browser_context: BrowserContext,
        target_url: str,
        action_type: str,
    ) -> dict[str, Any]:
        if not action_type:
            raise PlatformActionError("action_type is required")

        self.logger.info("Executing Instagram action", extra={"action_type": action_type})
        navigation = await self._navigate(browser_context, target_url)
        await self._apply_session_cookies(browser_context)
        return {"platform": "instagram", "action_type": action_type, **navigation}

    async def _apply_session_cookies(self, browser_context: BrowserContext) -> None:
        cookies = self.account.session_cookies or []
        if cookies:
            await browser_context.add_cookies(cookies)
