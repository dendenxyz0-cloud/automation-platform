from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from playwright.async_api import BrowserContext

from app.services.platform_handlers.base import BasePlatformHandler, PlatformActionError


_ALLOWED_ACTIONS = {"navigate", "click_mock_button", "scrape_text"}


def _is_allowed_fixture_url(target_url: str) -> bool:
    parsed = urlparse(target_url)
    if parsed.scheme == "file":
        return True
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    hostname = parsed.hostname.lower()
    return (
        hostname in {"localhost", "127.0.0.1", "::1"}
        or hostname.endswith(".test")
        or hostname.endswith(".staging")
        or hostname.startswith("staging.")
        or ".staging." in hostname
    )


class TestFixtureHandler(BasePlatformHandler):
    """Execute deterministic actions only against local/staging HTML fixtures."""

    async def execute_action(
        self,
        browser_context: BrowserContext,
        target_url: str,
        action_type: str,
    ) -> dict[str, Any]:
        if not _is_allowed_fixture_url(target_url):
            raise PlatformActionError("TestFixtureHandler only accepts local or staging fixture URLs")
        if action_type not in _ALLOWED_ACTIONS:
            raise PlatformActionError(f"Unsupported test fixture action: {action_type}")

        page = await browser_context.new_page()
        try:
            response = await page.goto(target_url, wait_until="domcontentloaded", timeout=15_000)
            result: dict[str, Any] = {
                "platform": "test",
                "action_type": action_type,
                "target_url": target_url,
                "status_code": response.status if response else None,
            }
            if action_type == "click_mock_button":
                button = page.locator("[data-testid='mock-action'], #mock-action").first
                await button.click(timeout=5_000)
                result["clicked"] = True
                result["result_text"] = await page.locator(
                    "[data-testid='mock-result'], #mock-result"
                ).first.inner_text(timeout=5_000)
            elif action_type == "scrape_text":
                text = await page.locator("[data-testid='mock-text'], #mock-text").first.inner_text(
                    timeout=5_000
                )
                result["text"] = text[:500]
            else:
                result["title"] = await page.title()
            return result
        except PlatformActionError:
            raise
        except Exception as exc:
            self.logger.exception("Test fixture action failed", extra={"action_type": action_type})
            raise PlatformActionError("Test fixture action failed") from exc
        finally:
            await page.close()
