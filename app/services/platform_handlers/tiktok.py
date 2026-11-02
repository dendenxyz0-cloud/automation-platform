import asyncio
import random
from typing import Any

from playwright.async_api import BrowserContext, Page

from app.services.platform_handlers.base import BasePlatformHandler, PlatformActionError


class TikTokHandler(BasePlatformHandler):
    platform_name = "tiktok"

    async def execute_action(
        self,
        browser_context: BrowserContext,
        target_url: str,
        action_type: str,
    ) -> dict[str, Any]:
        if not action_type:
            raise PlatformActionError("action_type is required")

        try:
            page = await browser_context.new_page()
            await self._apply_saved_session(page)
            await self._human_scroll(page)
            response = await page.goto(target_url, wait_until="domcontentloaded", timeout=30_000)
            if response is None:
                raise PlatformActionError("No response from target URL")
            if response.status >= 400:
                raise PlatformActionError(f"Target URL returned status {response.status}")
            await self._human_delay()
            title = await page.title()
            return {
                "platform": self.platform_name,
                "action_type": action_type,
                "status": "completed",
                "target_url": target_url,
                "title": title,
                "status_code": response.status,
            }
        except Exception as exc:
            self.logger.exception("TikTok action failed")
            raise PlatformActionError(str(exc)) from exc

    async def _apply_saved_session(self, page: Page) -> None:
        cookies = self.account.session_cookies or []
        if cookies:
            await page.context.add_cookies(cookies)

    async def _human_scroll(self, page: Page) -> None:
        for _ in range(random.randint(1, 3)):
            await page.mouse.wheel(0, random.randint(120, 600))
            await asyncio.sleep(random.uniform(0.4, 1.0))

    async def _human_delay(self) -> None:
        await asyncio.sleep(random.uniform(0.6, 1.9))
