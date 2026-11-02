from __future__ import annotations

import json
import logging
from typing import Any, Optional

from playwright.async_api import BrowserContext

logger = logging.getLogger(__name__)


class BasePlatformHandler:
    """Abstract strategy interface for platform-specific, bounded browser actions."""

    platform_name: str = "generic"

    def __init__(self, account: Optional[dict[str, Any]] = None) -> None:
        self.account = account or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def _apply_session_cookies(self, browser_context: BrowserContext) -> None:
        session_cookies = self.account.get("session_cookies")
        if not session_cookies:
            return
        if isinstance(session_cookies, str):
            try:
                session_cookies = json.loads(session_cookies)
            except json.JSONDecodeError:
                return
        if isinstance(session_cookies, list):
            await browser_context.add_cookies(session_cookies)

    async def execute_action(
        self,
        browser_context: BrowserContext,
        target_url: str,
        action_type: str,
    ) -> dict[str, Any]:
        raise NotImplementedError
