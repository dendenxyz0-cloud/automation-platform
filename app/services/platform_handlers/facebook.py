from __future__ import annotations

from typing import Any

from playwright.async_api import Page

from app.services.platform_handlers.base import BasePlatformHandler, PlatformActionError


class FacebookHandler(BasePlatformHandler):
    """Structural handler for approved Facebook API or staging workflows."""

    async def run_platform_action(self, page: Page, target_url: str) -> dict[str, Any]:
        if not target_url.startswith(("http://", "https://")):
            raise PlatformActionError("Target URL must use HTTP or HTTPS")
        response = await page.goto(target_url, wait_until="domcontentloaded", timeout=30_000)
        return {"status_code": response.status if response else None, "title": await page.title()}

    async def execute_action(self, browser_context, target_url: str, action_type: str) -> dict[str, Any]:
        if action_type not in {"navigate", "status_check"}:
            raise PlatformActionError("Facebook handler only supports authorized status checks")
        page = await browser_context.new_page()
        try:
            result = await self.run_platform_action(page, target_url)
            return {"platform": "facebook", "action_type": action_type, **result}
        finally:
            await page.close()
