from __future__ import annotations

import logging
from dataclasses import dataclass
from time import monotonic
from typing import Any, Mapping

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class ProxyHealthError(RuntimeError):
    """The assigned proxy cannot safely service an automation task."""


@dataclass(frozen=True)
class ProxyHealthResult:
    available: bool
    latency_ms: int
    status_code: int | None


async def check_proxy_health(
    proxy: Mapping[str, Any],
    *,
    healthcheck_url: str,
    timeout_ms: int = 5_000,
) -> ProxyHealthResult:
    """Perform a bounded response check through the assigned proxy node."""
    if not proxy.get("ip") or not proxy.get("port"):
        raise ProxyHealthError("Proxy requires ip and port")
    if not healthcheck_url.startswith(("http://", "https://")):
        raise ProxyHealthError("Proxy healthcheck URL must use HTTP or HTTPS")

    proxy_config = {
        "server": f"http://{proxy['ip']}:{proxy['port']}",
        "username": proxy.get("username", ""),
        "password": proxy.get("password", ""),
    }
    started = monotonic()
    async with async_playwright() as playwright:
        browser = None
        try:
            browser = await playwright.chromium.launch(
                headless=True,
                args=["--disable-dev-shm-usage", "--no-sandbox", "--disable-gpu"],
                proxy=proxy_config,
            )
            context = await browser.new_context(ignore_https_errors=False)
            try:
                page = await context.new_page()
                try:
                    response = await page.goto(
                        healthcheck_url,
                        wait_until="domcontentloaded",
                        timeout=timeout_ms,
                    )
                    latency_ms = int((monotonic() - started) * 1000)
                    status_code = response.status if response else None
                    if response is None or status_code >= 500:
                        raise ProxyHealthError(f"Healthcheck returned status {status_code}")
                    return ProxyHealthResult(True, latency_ms, status_code)
                finally:
                    await page.close()
            finally:
                await context.close()
        except ProxyHealthError:
            raise
        except Exception as exc:
            logger.warning("Proxy healthcheck failed", extra={"healthcheck_url": healthcheck_url})
            raise ProxyHealthError("Proxy healthcheck failed") from exc
        finally:
            if browser is not None:
                await browser.close()
