from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from playwright.async_api import BrowserContext

logger = logging.getLogger(__name__)


class PlatformActionError(RuntimeError):
    """Expected failure while executing a platform action."""


class AccountLockedError(PlatformActionError):
    """The platform indicates that the managed account cannot be used."""


class SessionExpiredError(PlatformActionError):
    """The saved session is no longer valid."""


class ProxyExpiredError(PlatformActionError):
    """The configured proxy rejected or could not complete navigation."""


@dataclass(frozen=True)
class AccountCredentials:
    """Opaque credentials supplied by the account-secret layer.

    The dispatcher passes these values to a handler but handlers must not log them.
    A production implementation should decrypt credentials only in memory.
    """

    credentials: Mapping[str, Any]
    session_cookies: Optional[Any] = None
    proxy: Optional[Mapping[str, Any]] = None


class BasePlatformHandler(ABC):
    """Strategy interface for platform-specific browser flows."""

    def __init__(self, account: AccountCredentials) -> None:
        self.account = account
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def execute_action(
        self,
        browser_context: BrowserContext,
        target_url: str,
        action_type: str,
    ) -> dict[str, Any]:
        """Execute one bounded action using an already-configured context."""
        raise NotImplementedError

    async def _navigate(self, browser_context: BrowserContext, target_url: str) -> dict[str, Any]:
        page = await browser_context.new_page()
        try:
            response = await page.goto(target_url, wait_until="domcontentloaded", timeout=30_000)
            if response is None:
                raise PlatformActionError("Target navigation returned no response")
            if response.status == 407:
                raise ProxyExpiredError("Proxy authentication was rejected")
            return {
                "status_code": response.status,
                "title": await page.title(),
                "target_url": target_url,
            }
        except PlatformActionError:
            raise
        except Exception as exc:
            self.logger.exception("Platform navigation failed", extra={"target_url": target_url})
            raise PlatformActionError(str(exc)) from exc
        finally:
            await page.close()
