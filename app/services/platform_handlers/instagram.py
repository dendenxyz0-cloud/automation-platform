from typing import Any

from playwright.async_api import BrowserContext

from app.services.platform_handlers.base import BasePlatformHandler, PlatformActionError


class InstagramHandler(BasePlatformHandler):
    """Placeholder for Instagram-specific, explicitly bounded browser actions."""

    async def run_platform_action(self, page, target_url: str) -> dict[str, Any]:
        response = await page.goto(target_url, wait_until="domcontentloaded", timeout=30_000)
        return {"status_code": response.status if response else None, "title": await page.title()}

    async def execute_action(
        self,
        browser_context: BrowserContext,
        target_url: str,
        action_type: str,
    ) -> dict[str, Any]:
        if not action_type:
            raise PlatformActionError("action_type is required")

        self.logger.info("Executing Instagram action", extra={"action_type": action_type})
        page = await browser_context.new_page()
        try:
            navigation = await self.run_platform_action(page, target_url)
            return {"platform": "instagram", "action_type": action_type, **navigation}
        finally:
            await page.close()
