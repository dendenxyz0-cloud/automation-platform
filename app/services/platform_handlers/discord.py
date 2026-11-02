from typing import Any

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
        navigation = await self._navigate(browser_context, target_url)
        return {"platform": "discord", "action_type": action_type, **navigation}
