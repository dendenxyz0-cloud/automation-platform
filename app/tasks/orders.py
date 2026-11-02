from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator, Mapping, Optional

from playwright.async_api import Browser, BrowserContext, async_playwright
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import AutomationAuditLog, BotAccount, BotAccountStatus, BotPlatform, Order
from app.db.session import SessionLocal
from app.queue.celery_app import celery_app
from app.services.audit import record_audit_event
from app.services.browser_runner import AuthorizedSessionManager
from app.services.platform_handlers import (
    AccountCredentials,
    AccountLockedError,
    BasePlatformHandler,
    DiscordHandler,
    InstagramHandler,
    PlatformActionError,
    ProxyExpiredError,
    SessionExpiredError,
    TestFixtureHandler,
)
from app.services.proxy_health import ProxyHealthError, check_proxy_health

logger = logging.getLogger(__name__)

_HANDLER_TYPES: dict[str, type[BasePlatformHandler]] = {
    BotPlatform.INSTAGRAM.value: InstagramHandler,
    BotPlatform.DISCORD.value: DiscordHandler,
    "test": TestFixtureHandler,
}


class NoAvailableAccountError(RuntimeError):
    pass


class NoAvailableProxyError(RuntimeError):
    pass


class RateLimitExceededError(RuntimeError):
    pass


class ComplianceKillSwitchError(RuntimeError):
    pass


def _set_order_status(order_id: int, status: str) -> None:
    with SessionLocal() as db:
        order = db.query(Order).filter(Order.id == order_id).one_or_none()
        if order is None:
            raise RuntimeError(f"Order {order_id} not found")
        order.status = status
        db.commit()


def _parse_proxy_pool() -> list[dict[str, Any]]:
    try:
        raw = json.loads(settings.PROXY_CONFIGS_JSON)
    except json.JSONDecodeError as exc:
        raise NoAvailableProxyError("PROXY_CONFIGS_JSON is not valid JSON") from exc

    if not isinstance(raw, list):
        raise NoAvailableProxyError("PROXY_CONFIGS_JSON must be a JSON array")

    proxies = [item for item in raw if isinstance(item, dict) and item.get("ip") and item.get("port")]
    if not proxies:
        raise NoAvailableProxyError("No active proxy configuration is available")
    return proxies


def _select_proxy(request_proxy: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    """Use an explicitly supplied proxy or the configured worker pool.

    Proxy secrets are never written to logs. Pool rotation can be replaced with a
    health-aware selector without changing the worker's lease contract.
    """
    if request_proxy:
        return dict(request_proxy)
    return _parse_proxy_pool()[0]


def _decode_session_state(raw: Optional[str]) -> Optional[dict[str, Any]]:
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SessionExpiredError("Stored session cookies are not valid JSON") from exc

    if isinstance(value, dict) and "cookies" in value:
        return value
    if isinstance(value, list):
        return {"cookies": value, "origins": []}
    raise SessionExpiredError("Stored session cookies have an unsupported format")


def _load_opaque_credentials(value: str) -> dict[str, Any]:
    """Return credentials without logging or interpreting secret material.

    Replace this boundary with the application's KMS/secret-vault decryptor. Until
    then, handlers receive an opaque value and cannot accidentally print plaintext.
    """
    return {"encrypted": value}


def _lease_account(db: Session, platform: str) -> BotAccount:
    try:
        BotPlatform(platform)
    except ValueError as exc:
        raise PlatformActionError(f"Unsupported platform: {platform}") from exc

    candidates = (
        db.query(BotAccount)
        .filter(
            BotAccount.platform == platform,
            BotAccount.status == BotAccountStatus.ACTIVE.value,
        )
        .order_by(BotAccount.last_used_at.asc().nullsfirst(), BotAccount.id.asc())
        .with_for_update(skip_locked=True)
        .all()
    )
    if not candidates:
        raise NoAvailableAccountError(f"No active account available for platform {platform}")
    if settings.AUTOMATION_RATE_LIMIT_PER_HOUR <= 0:
        db.commit()
        raise RateLimitExceededError("Automation rate limiting is configured to allow no actions")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    account = None
    for candidate in candidates:
        action_count = (
            db.query(AutomationAuditLog)
            .filter(
                AutomationAuditLog.account_id == candidate.id,
                AutomationAuditLog.event_type == "action_executed",
                AutomationAuditLog.status == "success",
                AutomationAuditLog.created_at >= cutoff,
            )
            .count()
        )
        if action_count < settings.AUTOMATION_RATE_LIMIT_PER_HOUR:
            account = candidate
            break

    if account is None:
        db.commit()
        raise RateLimitExceededError("All active accounts are at their hourly action limit")

    account.status = BotAccountStatus.IN_USE.value
    db.commit()
    db.refresh(account)
    return account


def _update_account_status(account_id: int, status: BotAccountStatus) -> None:
    with SessionLocal() as db:
        account = db.query(BotAccount).filter(BotAccount.id == account_id).one_or_none()
        if account is None:
            logger.error("Leased account disappeared", extra={"account_id": account_id})
            return
        account.status = status.value
        if status == BotAccountStatus.ACTIVE:
            account.last_used_at = datetime.now(timezone.utc)
        db.commit()


def _handler_for(platform: str, account: AccountCredentials) -> BasePlatformHandler:
    handler_type = _HANDLER_TYPES.get(platform)
    if handler_type is None:
        raise PlatformActionError(
            f"No handler is registered for {platform}; add a strategy before dispatching it"
        )
    return handler_type(account)


@asynccontextmanager
async def _browser_context(
    account: AccountCredentials,
    account_id: Optional[int],
    db: Optional[Session],
) -> AsyncIterator[BrowserContext]:
    proxy = account.proxy
    proxy_config = None
    if proxy:
        proxy_config = {
            "server": f"http://{proxy['ip']}:{proxy['port']}",
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
        try:
            if account_id is not None and db is not None:
                context_options = AuthorizedSessionManager(db).context_options(
                    account_id,
                    proxy=None,
                )
            else:
                context_options = {
                    "ignore_https_errors": False,
                    "java_script_enabled": True,
                    "viewport": {"width": 1280, "height": 720},
                    "locale": "en-US",
                }
            context = await browser.new_context(**context_options)
            yield context
        finally:
            if context is not None:
                await context.close()
            await browser.close()


async def _execute_action(
    platform: str,
    target_url: str,
    action_type: str,
    account: AccountCredentials,
    account_id: Optional[int],
) -> dict[str, Any]:
    handler = _handler_for(platform, account)
    with SessionLocal() as db:
        async with _browser_context(account, account_id, db) as browser_context:
            return await handler.execute_action(browser_context, target_url, action_type)


def _account_failure_status(exc: Exception) -> BotAccountStatus:
    if isinstance(exc, SessionExpiredError):
        return BotAccountStatus.DEAD
    if isinstance(exc, AccountLockedError):
        return BotAccountStatus.FLAGGED
    if isinstance(exc, ProxyExpiredError):
        return BotAccountStatus.FLAGGED
    return BotAccountStatus.FLAGGED


def _record_task_event(
    *,
    event_type: str,
    status: str,
    platform: str,
    order_id: int,
    account_id: Optional[int] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    with SessionLocal() as db:
        record_audit_event(
            db,
            event_type=event_type,
            status=status,
            platform=platform,
            order_id=order_id,
            account_id=account_id,
            details=details,
        )


def _check_compliance_kill_switch(order_id: int, platform: str) -> None:
    if not settings.COMPLIANCE_KILL_SWITCH:
        return
    _record_task_event(
        event_type="compliance_kill_switch",
        status="blocked",
        platform=platform,
        order_id=order_id,
    )
    raise ComplianceKillSwitchError("Automation is disabled by the compliance kill switch")


@celery_app.task(
    bind=True,
    name="process_order_task",
    autoretry_for=(NoAvailableAccountError, NoAvailableProxyError, RateLimitExceededError, ProxyHealthError),
    retry_backoff=5,
    max_retries=3,
)
def process_order_task(
    self,
    order_id: int,
    target_url: str,
    platform: str,
    action_type: str = "navigate",
    proxy: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Lease one managed account, execute one bounded action, and release it."""
    account_id: Optional[int] = None
    try:
        _check_compliance_kill_switch(order_id, platform)
        _set_order_status(order_id, "Processing")
        selected_proxy = proxy if platform == "test" else _select_proxy(proxy)

        if selected_proxy:
            try:
                health = asyncio.run(
                    check_proxy_health(
                        selected_proxy,
                        healthcheck_url=settings.PROXY_HEALTHCHECK_URL,
                        timeout_ms=settings.PROXY_HEALTHCHECK_TIMEOUT_MS,
                    )
                )
                _record_task_event(
                    event_type="proxy_healthcheck",
                    status="success",
                    platform=platform,
                    order_id=order_id,
                    details={"latency_ms": health.latency_ms, "status_code": health.status_code},
                )
            except ProxyHealthError:
                _record_task_event(
                    event_type="proxy_healthcheck",
                    status="error",
                    platform=platform,
                    order_id=order_id,
                )
                raise

        if platform == "test":
            account_context = AccountCredentials(credentials={}, proxy=selected_proxy)
        else:
            with SessionLocal() as db:
                account = _lease_account(db, platform)
                account_id = account.id
                account_context = AccountCredentials(
                    credentials=_load_opaque_credentials(account.credentials_encrypted),
                    session_cookies=account.session_cookies,
                    proxy=selected_proxy,
                )

        result = asyncio.run(
            _execute_action(platform, target_url, action_type, account_context, account_id)
        )
        if account_id is not None:
            _record_task_event(
                event_type="action_executed",
                status="success",
                platform=platform,
                order_id=order_id,
                account_id=account_id,
            )
            _update_account_status(account_id, BotAccountStatus.ACTIVE)
        _set_order_status(order_id, "Completed")
        return {"order_id": order_id, "status": "Completed", "details": result}

    except Exception as exc:
        if account_id is not None:
            try:
                _update_account_status(account_id, _account_failure_status(exc))
            except Exception:
                logger.exception("Failed to update leased account status", extra={"account_id": account_id})
        try:
            _record_task_event(
                event_type="task_failure",
                status="error",
                platform=platform,
                order_id=order_id,
                account_id=account_id,
                details={"error_type": type(exc).__name__},
            )
        except Exception:
            logger.exception("Failed to write automation audit event", extra={"order_id": order_id})
        try:
            _set_order_status(
                order_id,
                "Pending"
                if isinstance(
                    exc,
                    (
                        NoAvailableAccountError,
                        NoAvailableProxyError,
                        RateLimitExceededError,
                        ProxyHealthError,
                    ),
                )
                else "Cancelled",
            )
        except Exception:
            logger.exception("Failed to update order status", extra={"order_id": order_id})
        raise
