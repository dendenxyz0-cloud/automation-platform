from __future__ import annotations

import json
import logging
from typing import Any, Dict, Mapping, Optional

from playwright.async_api import Browser, BrowserContext, async_playwright
from sqlalchemy.orm import Session

from app.db.models import BotAccount, BotAccountStatus

logger = logging.getLogger(__name__)


class SessionStateError(ValueError):
    """Stored session state is missing, malformed, or not usable."""


class AuthorizedSessionManager:
    """Load and validate session cookies for accounts owned by the organization.

    Credential decryption is deliberately not performed here. The encrypted
    credential blob remains opaque; a production secret-vault adapter can be
    added at the same boundary without exposing plaintext to logs or task
    payloads.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def load_session_state(self, account_id: int) -> Optional[dict[str, Any]]:
        account = (
            self.db.query(BotAccount)
            .filter(BotAccount.id == account_id)
            .one_or_none()
        )
        if account is None:
            raise SessionStateError("Authorized account was not found")
        if account.status == BotAccountStatus.DEAD.value:
            raise SessionStateError("Account session is marked dead")
        if not account.session_cookies:
            return None

        try:
            state = json.loads(account.session_cookies)
        except json.JSONDecodeError as exc:
            raise SessionStateError("Stored session cookies are not valid JSON") from exc

        if isinstance(state, list):
            state = {"cookies": state, "origins": []}
        if not isinstance(state, dict) or not isinstance(state.get("cookies"), list):
            raise SessionStateError("Session state must contain a cookies array")
        if not isinstance(state.get("origins", []), list):
            raise SessionStateError("Session state origins must be an array")
        return state

    def context_options(
        self,
        account_id: int,
        *,
        proxy: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        options: dict[str, Any] = {
            "ignore_https_errors": False,
            "java_script_enabled": True,
            "viewport": {"width": 1280, "height": 720},
            "locale": "en-US",
        }
        session_state = self.load_session_state(account_id)
        if session_state is not None:
            options["storage_state"] = session_state
        if proxy:
            options["proxy"] = {
                "server": f"http://{proxy['ip']}:{proxy['port']}",
                "username": proxy.get("username", ""),
                "password": proxy.get("password", ""),
            }
        return options


async def run_headless_visit(target_url: str, proxy: Optional[dict] = None) -> Dict[str, Any]:
    """Visit a URL without side effects and return a bounded response summary."""
    if not target_url.startswith(("http://", "https://")):
        raise ValueError("target_url must start with http:// or https://")

    proxy_config = None
    if proxy:
        ip = proxy.get("ip")
        port = proxy.get("port")
        if not ip or not port:
            raise ValueError("Proxy config requires 'ip' and 'port'")
        proxy_config = {
            "server": f"http://{ip}:{port}",
            "username": proxy.get("username", ""),
            "password": proxy.get("password", ""),
        }

    async with async_playwright() as playwright:
        browser: Browser = await playwright.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox", "--disable-gpu"],
            proxy=proxy_config,
        )
        context: Optional[BrowserContext] = None
        page = None
        try:
            context = await browser.new_context(
                ignore_https_errors=False,
                java_script_enabled=True,
                viewport={"width": 1280, "height": 720},
                locale="en-US",
            )
            page = await context.new_page()
            response = await page.goto(target_url, wait_until="domcontentloaded", timeout=30_000)
            await page.locator("body").wait_for(timeout=15_000)
            return {
                "success": True,
                "target_url": target_url,
                "status_code": response.status if response else None,
                "title": await page.title(),
                "body_preview": (await page.locator("body").inner_text() or "")[:250],
                "proxy_used": bool(proxy_config),
            }
        except Exception as exc:
            logger.warning("Non-destructive browser visit failed", extra={"target_url": target_url})
            return {
                "success": False,
                "target_url": target_url,
                "error": str(exc),
                "proxy_used": bool(proxy_config),
            }
        finally:
            if page is not None:
                await page.close()
            if context is not None:
                await context.close()
            await browser.close()
