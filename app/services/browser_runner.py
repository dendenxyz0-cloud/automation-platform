import asyncio
from typing import Any, Dict, Optional

from playwright.async_api import async_playwright


async def run_headless_visit(target_url: str, proxy: Optional[dict] = None) -> Dict[str, Any]:
    """
    Launches a headless Chromium browser through an optional HTTP/HTTPS proxy,
    visits a target URL, does a minimal non-destructive interaction, and returns
    a structured result.
    """
    if not target_url.startswith(("http://", "https://")):
        raise ValueError("target_url must start with http:// or https://")

    proxy_config = None
    if proxy:
        ip = proxy.get("ip")
        port = proxy.get("port")
        username = proxy.get("username")
        password = proxy.get("password")

        if not ip or not port:
            raise ValueError("Proxy config requires 'ip' and 'port'")

        proxy_config = {
            "server": f"http://{ip}:{port}",
            "username": username or "",
            "password": password or "",
        }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-gpu",
            ],
        )
        context = None
        page = None

        try:
            context = await browser.new_context(
                ignore_https_errors=True,
                java_script_enabled=True,
                viewport={"width": 1280, "height": 720},
                proxy=proxy_config,
                locale="en-US",
            )

            page = await context.new_page()
            response = await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            await page.locator("body").wait_for(timeout=15000)

            title = await page.title()
            body_preview = await page.locator("body").inner_text()
            body_preview = (body_preview or "")[:250]

            return {
                "success": True,
                "target_url": target_url,
                "status_code": response.status if response else None,
                "title": title,
                "body_preview": body_preview,
                "proxy_used": bool(proxy_config),
            }

        except Exception as exc:
            return {
                "success": False,
                "target_url": target_url,
                "error": str(exc),
                "proxy_used": bool(proxy_config),
            }

        finally:
            try:
                if page is not None:
                    await page.close()
            finally:
                if context is not None:
                    await context.close()
                await browser.close()
